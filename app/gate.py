"""A single-passphrase gate in front of the whole app.

The PoC has no user accounts, so this is not authentication — it is a shared
door code that keeps a public demo URL from being an open patient-record
database. It covers the API as well as the pages: gating only the HTML would
leave every /api route readable by anyone who guessed a path.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_config

cfg = get_config()

COOKIE = "clinic_access"
# Paths reachable without the passphrase: the gate itself and the health probe
# (so a monitor can check the server is up without holding the door code).
OPEN_PATHS = {"/gate", "/api/health"}


def _token() -> str:
    """A cookie value only someone who knows the passphrase could produce."""
    return hmac.new(cfg.session_secret.encode(),
                    cfg.access_passphrase.encode(), hashlib.sha256).hexdigest()


def _authorised(request: Request) -> bool:
    supplied = request.cookies.get(COOKIE, "")
    return bool(supplied) and hmac.compare_digest(supplied, _token())


GATE_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clinic</title>
<style>
  body {{ margin:0; min-height:100vh; display:flex; align-items:center;
    justify-content:center; background:#faf9f7; color:#23201c;
    font:15px/1.5 ui-sans-serif, system-ui, -apple-system, sans-serif; }}
  form {{ background:#fff; border:1px solid #e4e0da; border-radius:10px;
    padding:2rem; width:min(360px,90vw); box-shadow:0 8px 30px rgba(35,32,28,.07); }}
  h1 {{ font-size:1.05rem; margin:0 0 .3rem; }}
  p {{ color:#7d766c; font-size:.85rem; margin:0 0 1.2rem; }}
  input {{ width:100%; padding:.55rem .6rem; font:inherit; border:1px solid #e4e0da;
    border-radius:5px; margin-bottom:.7rem; box-sizing:border-box; }}
  button {{ width:100%; padding:.55rem; font:inherit; font-weight:600; color:#fff;
    background:#9c3f5a; border:1px solid #9c3f5a; border-radius:5px; cursor:pointer; }}
  .err {{ color:#9c3f5a; font-size:.82rem; margin:0 0 .7rem; }}
</style></head><body>
<form method="post" action="/gate">
  <h1>Clinic</h1>
  <p>Online clinic platform &middot; Phase 1 proof of concept.<br>Enter the access phrase to continue.</p>
  {error}
  <input type="password" name="passphrase" placeholder="Access phrase"
         autofocus autocomplete="current-password">
  <button type="submit">Continue</button>
</form></body></html>"""


def gate_page(error: str = "") -> HTMLResponse:
    markup = GATE_PAGE.format(
        error=f'<p class="err">{error}</p>' if error else "")
    # 401 on the first view so scrapers and monitors see a refusal, not a page.
    return HTMLResponse(markup, status_code=200 if not error else 401)


class AccessGate(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in OPEN_PATHS or _authorised(request):
            return await call_next(request)
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                {"detail": "Access phrase required. Open the site root first."},
                status_code=401)
        return gate_page()


def register(app) -> None:
    app.add_middleware(AccessGate)

    @app.post("/gate")
    async def submit_gate(request: Request):
        form = await request.form()
        supplied = str(form.get("passphrase", ""))
        # compare_digest to keep the check constant-time.
        if not hmac.compare_digest(supplied, cfg.access_passphrase):
            return gate_page("That access phrase is not correct.")
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            COOKIE, _token(), max_age=60 * 60 * 12, httponly=True,
            samesite="lax", secure=cfg.cookie_secure,
        )
        return response


def new_secret() -> str:
    return secrets.token_hex(32)
