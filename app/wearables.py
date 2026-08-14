"""Wearable OAuth connect flows for Oura, Whoop, and Garmin.

The authorize redirect, the callback, and the code-for-token exchange are
real, against each vendor's actual OAuth2 endpoints. What happens *after* a
successful connection is deliberately fixture data, not a live pull of the
client's metrics — see specs/v2/06-client-portal.md's "Wearable
integration" section. This phase proves the OAuth mechanics and the data
model shape; three real vendor data-normalization integrations are
separable future work.

Garmin note: Garmin's older Health API used three-legged OAuth 1.0a, which
does not fit an authorize_url/token_url shape at all. Garmin's newer
"Connect Developer Program" API moved to OAuth 2.0 with PKCE, which *does*
fit this module's shape (with an extra code_verifier/code_challenge leg —
see PROVIDERS and connect_url() below). This module targets that newer
flow. Confidence in Oura's and Whoop's endpoint URLs is high; confidence in
Garmin's exact current URLs is lower — verify against Garmin's developer
portal before pointing this at real credentials.

A client's session cookie (app/auth.py) carries practitioner_id alongside
role and id, since vault.py shards clients into one SQLite file per
practitioner and every client-scoped route needs to know which vault to
open. The connect route below reads it from the verified session rather
than trusting a caller-supplied value.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import urllib.error
import urllib.request
from base64 import urlsafe_b64encode
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeSerializer

from . import auth, vault
from .config import get_config

cfg = get_config()

# Signs the OAuth state param — independent of auth.py's session cookie
# signing, though it reuses the same secret (fine: different salt, and
# neither is a session credential on its own).
_STATE_SALT = "clinic-wearable-state"
_state_serializer = URLSafeSerializer(cfg.session_secret, salt=_STATE_SALT)

PROVIDERS = {
    # Oura API v2 (https://cloud.ouraring.com/v2/docs). Standard OAuth2
    # authorization-code flow.
    "oura": {
        "client_id": cfg.oura_client_id,
        "client_secret": cfg.oura_client_secret,
        "authorize_url": "https://cloud.ouraring.com/oauth/authorize",
        "token_url": "https://api.ouraring.com/oauth/token",
        "scope": "email personal daily heartrate workout",
        "pkce": False,
    },
    # Whoop API (https://developer.whoop.com). Standard OAuth2
    # authorization-code flow; "offline" scope requests a refresh token.
    "whoop": {
        "client_id": cfg.whoop_client_id,
        "client_secret": cfg.whoop_client_secret,
        "authorize_url": "https://api.prod.whoop.com/oauth/oauth2/auth",
        "token_url": "https://api.prod.whoop.com/oauth/oauth2/token",
        "scope": "read:profile read:recovery read:cycles read:sleep "
                 "read:workout offline",
        "pkce": False,
    },
    # Garmin Connect Developer Program. Garmin's *older* Health API used
    # OAuth 1.0a three-legged auth (request token -> user auth -> access
    # token, HMAC-SHA1 signed) — that flow does not fit this module's
    # authorize_url/token_url shape at all. This targets Garmin's newer
    # OAuth2+PKCE flow instead. Endpoint URLs below are lower-confidence
    # than Oura/Whoop's — confirm against Garmin's current developer
    # portal before using real credentials.
    "garmin": {
        "client_id": cfg.garmin_client_id,
        "client_secret": cfg.garmin_client_secret,
        "authorize_url": "https://connect.garmin.com/oauth2Confirm",
        "token_url": "https://diauthz.garmin.com/di-oauth2-service/oauth/token",
        "scope": "",
        "pkce": True,
    },
}


def _redirect_uri(provider: str) -> str:
    return f"{cfg.public_base_url}/api/me/wearables/{provider}/callback"


def connect_url(provider: str, practitioner_id: str, client_id: str) -> str:
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown wearable provider: {provider!r}")
    vendor = PROVIDERS[provider]

    state_payload = {
        "practitioner_id": practitioner_id,
        "client_id": client_id,
        "provider": provider,
    }
    params = {
        "client_id": vendor["client_id"],
        "redirect_uri": _redirect_uri(provider),
        "response_type": "code",
        "scope": vendor["scope"],
    }
    if vendor["pkce"]:
        # RFC 7636: verifier is 43-128 chars of unreserved characters;
        # token_urlsafe(64) lands comfortably in that range. The verifier
        # travels inside the signed state so the callback can present it
        # at the token endpoint without any server-side session store.
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        state_payload["code_verifier"] = code_verifier
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    params["state"] = _state_serializer.dumps(state_payload)
    return f"{vendor['authorize_url']}?{urlencode(params)}"


def _exchange_code(provider: str, code: str, code_verifier: str | None) -> dict:
    """Real HTTP call to the vendor's token endpoint. The resulting token
    is not stored or used to pull data in this phase — see module
    docstring. This only proves the exchange succeeds."""
    vendor = PROVIDERS[provider]
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _redirect_uri(provider),
        "client_id": vendor["client_id"],
        "client_secret": vendor["client_secret"],
    }
    if code_verifier:
        data["code_verifier"] = code_verifier

    request = urllib.request.Request(
        vendor["token_url"],
        data=urlencode(data).encode(),
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode())


def handle_callback(provider: str, code: str, state: str) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown wearable provider.")

    try:
        payload = _state_serializer.loads(state)
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid or tampered state parameter.")

    if payload.get("provider") != provider:
        raise HTTPException(status_code=400, detail="State does not match provider.")

    practitioner_id = payload["practitioner_id"]
    client_id = payload["client_id"]

    try:
        _exchange_code(provider, code, payload.get("code_verifier"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not complete the {provider} token exchange: {exc}",
        )

    # Fixture stand-in for a live vendor data pull, per spec — deliberate
    # scope cut, not an oversight.
    vault.create_wearable_connection(practitioner_id, client_id, provider)
    vault.seed_fixture_wearable_data(practitioner_id, client_id, provider)

    return {"connected": True, "provider": provider, "data": "sample"}


def register(app: FastAPI) -> None:
    @app.post("/api/me/wearables/{provider}/connect")
    async def start_connect(
        provider: str, session: dict = Depends(auth.require_client)
    ):
        if provider not in PROVIDERS:
            raise HTTPException(status_code=404, detail="Unknown wearable provider.")
        # No OAuth app credentials configured for this provider on this
        # deployment — redirecting anyway sends the client to a vendor page
        # that will fail with no way back (specs/v2/13-known-issues.md H3).
        if not PROVIDERS[provider]["client_id"]:
            raise HTTPException(
                status_code=409,
                detail=f"{provider.capitalize()} isn't configured on this deployment yet.")

        practitioner_id = session["practitioner_id"]
        client_id = session["id"]
        return {"url": connect_url(provider, practitioner_id, client_id)}

    @app.get("/api/me/wearables")
    async def list_connections(session: dict = Depends(auth.require_client)):
        return vault.list_wearable_connections(session["practitioner_id"], session["id"])

    @app.get("/api/me/wearables/{provider}/callback")
    async def oauth_callback(provider: str, code: str, state: str):
        # The vendor's browser redirect lands here directly — send the
        # user back into the app instead of leaving their browser sitting
        # on a bare JSON response with no way back
        # (specs/v2/13-known-issues.md, adjacent to H3/M2). The page
        # re-fetches real connection state on load, so no query param is
        # needed for it to show as connected.
        handle_callback(provider, code, state)
        return RedirectResponse("/client/wearables")
