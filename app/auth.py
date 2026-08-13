"""Real accounts, replacing app/gate.py's single shared passphrase.

A session is a signed itsdangerous cookie carrying {"role", "id"} — no
server-side session store, so any process can verify a cookie on its own.
Unlike gate.py this is not middleware: routes opt in individually via the
require_* dependencies below, since public routes (directory, signup,
contact) must stay reachable without a cookie at all.
"""
from __future__ import annotations

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
    if session.get("admin_role") != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required.")
    return session


def require_practitioner(request: Request) -> dict:
    session = current_session(request)
    if session is None or session["role"] != "practitioner":
        raise HTTPException(status_code=401, detail="Practitioner login required.")
    return session


def require_pro_practitioner(session: dict = Depends(require_practitioner)) -> dict:
    practitioner = core_store.get_practitioner(session["id"])
    if practitioner is None or practitioner["plan"] != "pro" or \
            practitioner.get("stripe_status") in ("past_due", "blocked"):
        raise HTTPException(status_code=403, detail="A Pro plan in good standing is required.")
    return session


def require_client(request: Request) -> dict:
    session = current_session(request)
    if session is None or session["role"] != "client":
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

        admin = core_store.get_admin_by_email(email)
        if admin is not None and admin["is_active"] and \
                verify_password(password, admin["password_hash"]):
            response = JSONResponse(
                {"role": "admin", "id": admin["id"], "admin_role": admin["role"]})
            _set_session_cookie(response, "admin", admin["id"],
                                admin_role=admin["role"])
            return response

        practitioner = core_store.get_practitioner_by_email(email)
        if practitioner is not None and verify_password(password, practitioner["password_hash"]):
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
                response = JSONResponse(
                    {"role": "client", "id": client["id"],
                     "practitioner_id": practitioner_id})
                _set_session_cookie(response, "client", client["id"],
                                    practitioner_id=practitioner_id)
                return response

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
