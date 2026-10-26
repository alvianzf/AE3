"""Dedicated-endpoint lifecycle control — Nebius Token Factory's control-plane
API (docs.tokenfactory.nebius.com/api-reference/dedicated-endpoints).

Separate surface from app/clients/llm_client.py's OpenAI-compatible chat
completions: same bearer token (cfg.nebius_api_key), but a plain JSON REST
API at /v0/dedicated_endpoints rather than the /v1/ OpenAI-compatible path,
so it's called directly rather than through the openai SDK. urllib (stdlib)
rather than a new HTTP dependency — same choice app/scraper.py already made.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..config import get_config

cfg = get_config()

# Nebius's dedicated-endpoints control plane — distinct from
# cfg.nebius_base_url, which already has the OpenAI-compatible /v1/ suffix
# baked in for chat completions and points at a different API surface.
_CONTROL_BASE_URL = "https://api.tokenfactory.nebius.com/v0"


class NebiusAdminError(RuntimeError):
    """A dedicated-endpoints control-plane call failed."""


def _request(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{_CONTROL_BASE_URL}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {cfg.nebius_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise NebiusAdminError(f"{method} {path} -> {exc.code}: {detail}") from exc


def list_dedicated_endpoints() -> list[dict]:
    """Every dedicated endpoint on this Nebius account, with live status.

    Each entry's `deployment.status` is one of starting/running/updating/
    stopping/stopped/error; `enabled` reflects the last requested state,
    which is what start/stop below actually flips.
    """
    return _request("GET", "/dedicated_endpoints").get("data", [])


def _set_enabled(endpoint_id: str, enabled: bool) -> dict:
    return _request("PATCH", f"/dedicated_endpoints/{endpoint_id}", {"enabled": enabled})


def start_dedicated_endpoint(endpoint_id: str) -> dict:
    """Re-enable a stopped dedicated endpoint, spinning its GPU deployment
    back up. Not instant — the response reflects deployment.status moving
    to "starting", not yet "running"."""
    return _set_enabled(endpoint_id, True)


def stop_dedicated_endpoint(endpoint_id: str) -> dict:
    """Disable a running dedicated endpoint to stop GPU billing while idle.

    Only compute (GPU/vCPU/RAM) is released; the endpoint's config and
    routing_key are retained for a later start. Any AI-team role still
    routed to this endpoint's routing_key (app/config.py) will fail chat
    completions until it's started again — this does not fail over to
    another model on its own.
    """
    return _set_enabled(endpoint_id, False)
