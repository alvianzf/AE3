"""Real accounts, replacing app/gate.py's single shared passphrase.

A session is a signed itsdangerous cookie carrying {"role", "id"} — no
server-side session store, so any process can verify a cookie on its own.
Unlike gate.py this is not middleware: routes opt in individually via the
require_* dependencies below, since public routes (directory, signup,
contact) must stay reachable without a cookie at all.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict

import bcrypt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import core_store
from .config import get_config

cfg = get_config()

COOKIE = "clinic_session"
_SALT = "clinic-session"
_MAX_AGE = 60 * 60 * 12

_serializer = URLSafeTimedSerializer(cfg.session_secret, salt=_SALT)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def check_email_format(email: str) -> None:
    """Raises 400 on an obviously-invalid email. Loose on purpose (no RFC
    5322 pedantry) — this only catches "clearly not an email," the same bar
    the login/signup forms' `type="email"` hint implies but never enforced
    server-side (specs/v4/04-known-issues.md#l2)."""
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")


def check_password_strength(password: str) -> None:
    """Raises 400 if too weak. Previously only change_password enforced this
    — every account-creation path (practitioner/client/admin signup) hashed
    and stored whatever was given, including empty or 1-character passwords,
    while the 'At least 8 characters' hint on those forms was purely
    cosmetic (specs/v4/04-known-issues.md#h9)."""
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters.")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def current_session(request: Request) -> dict | None:
    cookie = request.cookies.get(COOKIE)
    if not cookie:
        return None
    try:
        return _serializer.loads(cookie, max_age=_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def require_admin(request: Request) -> dict:
    session = current_session(request)
    if session is None or session["role"] != "admin":
        raise HTTPException(status_code=401, detail="Admin login required.")
    # Unlike require_practitioner/require_client, this hits the DB: an admin
    # suspension needs to take effect immediately, not after a stale
    # session's 12h cookie expires — same reasoning as
    # require_pro_practitioner checking live plan/stripe_status.
    admin = core_store.get_admin(session["id"])
    if admin is None or not admin["is_active"]:
        raise HTTPException(status_code=401, detail="Admin login required.")
    return session


def require_superadmin(session: dict = Depends(require_admin)) -> dict:
    # Live DB check, not the session cookie's cached admin_role claim: a
    # demotion (superadmin_set_admin_role) needs to take effect immediately,
    # not after the demoted admin's existing 12h cookie expires — same
    # reasoning require_admin already applies to is_active, just missed here
    # originally (found in review, specs/v4/04-known-issues.md#c9).
    admin = core_store.get_admin(session["id"])
    if admin is None or admin["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required.")
    return session


def require_practitioner(request: Request) -> dict:
    session = current_session(request)
    if session is None or session["role"] != "practitioner":
        raise HTTPException(status_code=401, detail="Practitioner login required.")
    # Live DB check, same reasoning as require_admin's is_active check: a
    # suspension needs to take effect immediately, not after a stale 12h
    # cookie expires. Found missing in the v2.6 review — a suspended
    # practitioner kept full portal access until this was added. Only
    # 'suspended' blocks access here — 'pending' can still log in and see
    # their own status; that's a feature, not the bug that was found.
    practitioner = core_store.get_practitioner(session["id"])
    if practitioner is None or practitioner["status"] == "suspended":
        raise HTTPException(status_code=401, detail="Practitioner login required.")
    return session


def require_pro_practitioner(session: dict = Depends(require_practitioner)) -> dict:
    practitioner = core_store.get_practitioner(session["id"])
    # status must be 'approved' too, not just not-suspended: require_practitioner
    # deliberately still lets 'pending'/'rejected' log in (to see their own
    # status), but Pro features — real clients, real consults — must wait for
    # admin review. Found missing: a pending or rejected applicant who reached
    # 'pro' via checkout (billing.upgrade also guards this now) could otherwise
    # use the full consult pipeline before ever being approved.
    if practitioner is None or practitioner["status"] != "approved" or \
            practitioner["plan"] != "pro" or \
            practitioner.get("stripe_status") in ("past_due", "blocked"):
        raise HTTPException(status_code=403, detail="A Pro plan in good standing is required.")
    return session


def require_client(request: Request) -> dict:
    session = current_session(request)
    if session is None or session["role"] != "client":
        raise HTTPException(status_code=401, detail="Client login required.")
    # A client's access is meaningless once their practitioner is
    # suspended — there's no separate "suspend a client" action, so this is
    # the only lever that matters for a client's own portal access.
    practitioner = core_store.get_practitioner(session["practitioner_id"])
    if practitioner is None or practitioner["status"] == "suspended":
        raise HTTPException(status_code=401, detail="Client login required.")
    return session


def ensure_bootstrap_admin() -> None:
    if not (cfg.admin_bootstrap_email and cfg.admin_bootstrap_password):
        return
    if core_store.get_admin_by_email(cfg.admin_bootstrap_email) is not None:
        return
    # The bootstrap account is, by construction, the only way to get a first
    # admin into a fresh deployment — it has to be a superadmin, or nothing
    # could ever create a second one.
    core_store.create_admin(
        cfg.admin_bootstrap_email,
        hash_password(cfg.admin_bootstrap_password),
        "Admin", role="superadmin",
    )


# In-memory login lockout — no persistence needed across a restart (a
# restart is itself a rare, high-friction event an attacker can't trigger),
# and this app runs as a single process (specs/v3/11-operations.md), so a
# module-level dict is sufficient without adding a dependency for something
# this small. Previously there was no rate limiting or lockout at all
# (specs/v4/04-known-issues.md#h11) — bcrypt slows brute force somewhat but
# doesn't stop it.
_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_LOCKOUT_SECONDS = 15 * 60
_failed_logins: dict[str, list[float]] = defaultdict(list)


def _check_login_lockout(email: str) -> None:
    now = time.monotonic()
    attempts = [t for t in _failed_logins[email] if now - t < _LOGIN_LOCKOUT_SECONDS]
    _failed_logins[email] = attempts
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again in 15 minutes.")


def _record_login_failure(email: str) -> None:
    _failed_logins[email].append(time.monotonic())


def _clear_login_failures(email: str) -> None:
    _failed_logins.pop(email, None)


def _set_session_cookie(response, role: str, account_id: str, **extra) -> None:
    token = _serializer.dumps({"role": role, "id": account_id, **extra})
    response.set_cookie(
        COOKIE, token, max_age=_MAX_AGE, httponly=True,
        samesite="lax", secure=cfg.cookie_secure,
    )


def register(app: FastAPI) -> None:
    @app.post("/api/auth/login")
    async def login(request: Request):
        body = await request.json()
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))

        _check_login_lockout(email)

        admin = core_store.get_admin_by_email(email)
        if admin is not None and admin["is_active"] and \
                verify_password(password, admin["password_hash"]):
            _clear_login_failures(email)
            response = JSONResponse(
                {"role": "admin", "id": admin["id"], "admin_role": admin["role"]})
            _set_session_cookie(response, "admin", admin["id"],
                                admin_role=admin["role"])
            return response

        practitioner = core_store.get_practitioner_by_email(email)
        if practitioner is not None and practitioner["status"] != "suspended" and \
                verify_password(password, practitioner["password_hash"]):
            _clear_login_failures(email)
            response = JSONResponse({"role": "practitioner", "id": practitioner["id"]})
            _set_session_cookie(response, "practitioner", practitioner["id"])
            return response

        directory_entry = core_store.get_client_directory_entry(email)
        if directory_entry is not None:
            # Deferred: app/vault.py may not exist yet when this module is
            # imported (built in parallel), only needed on this branch.
            from . import vault

            client = vault.get_client(directory_entry["practitioner_id"], directory_entry["client_id"])
            if client is not None and verify_password(password, client["password_hash"]):
                # A client's own vault is sharded by practitioner (app/vault.py),
                # so the session has to carry practitioner_id too, not just role
                # and id — every client-scoped route needs it to know which
                # vault file to open.
                practitioner_id = directory_entry["practitioner_id"]
                _clear_login_failures(email)
                response = JSONResponse(
                    {"role": "client", "id": client["id"],
                     "practitioner_id": practitioner_id})
                _set_session_cookie(response, "client", client["id"],
                                    practitioner_id=practitioner_id)
                return response

        _record_login_failure(email)
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    @app.post("/api/auth/change-password")
    async def change_password(request: Request):
        session = current_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="Not logged in.")
        body = await request.json()
        current_password = str(body.get("current_password", ""))
        new_password = str(body.get("new_password", ""))
        if len(new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New password must be at least 8 characters.")

        role = session["role"]
        if role == "admin":
            account = core_store.get_admin(session["id"])
            verify_and_set = lambda h: core_store.set_admin_password(session["id"], h)
        elif role == "practitioner":
            account = core_store.get_practitioner(session["id"])
            verify_and_set = lambda h: core_store.set_practitioner_password(session["id"], h)
        elif role == "client":
            # Deferred import — same reasoning as the login handler's client
            # branch: app/vault.py may not exist at module load time.
            from . import vault
            account = vault.get_client(session["practitioner_id"], session["id"])
            verify_and_set = lambda h: vault.set_client_password(
                session["practitioner_id"], session["id"], h)
        else:
            raise HTTPException(status_code=400, detail="Unknown role.")

        if account is None or not verify_password(current_password, account["password_hash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect.")
        verify_and_set(hash_password(new_password))
        return {"ok": True}

    @app.post("/api/auth/logout")
    async def logout():
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE)
        return response

    @app.get("/api/auth/me")
    async def me(request: Request):
        session = current_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="Not logged in.")
        return session
