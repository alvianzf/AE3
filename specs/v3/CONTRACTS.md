# v2 build contracts

Internal to the implementation, not part of the versioned spec proper —
this pins exact function signatures across modules so the phases in
`/Users/azfaturrahman/.claude/plans/compiled-growing-mountain.md` can be
built in parallel by separate workers without waiting on each other or
colliding on the same files. Each module below has exactly one owner.
**Nobody but the integrator touches `app/main.py`, `requirements.txt`, or
`app/config.py`** — those are done or are the final wiring pass.

Follow `app/patients.py` and `app/originals.py`'s existing style exactly:
module-level functions, no classes, a fresh SQLite connection per call,
`from __future__ import annotations`, docstrings only where the *why* isn't
obvious from the name.

---

## `app/auth.py` (new — owner: auth)

Replaces `app/gate.py`. Password hashing via `bcrypt`. Session is a signed
`itsdangerous.URLSafeTimedSerializer` cookie (`COOKIE = "clinic_session"`,
salt `"clinic-session"`, keyed by `cfg.session_secret`, `max_age = 60*60*12`)
carrying `{"role": "admin"|"practitioner"|"client", "id": <row id>}` — no
server-side session store.

```python
def hash_password(password: str) -> str
def verify_password(password: str, password_hash: str) -> bool

def current_session(request: Request) -> dict | None
    # None if no/invalid/expired cookie. Otherwise {"role": ..., "id": ...}.

def require_admin(request: Request) -> dict        # FastAPI Depends
def require_practitioner(request: Request) -> dict  # FastAPI Depends
def require_pro_practitioner(
    session: dict = Depends(require_practitioner)) -> dict
    # 403 if core_store.get_practitioner(session["id"])["plan"] != "pro"
    # or stripe_status == "past_due"/"blocked". Uses core_store (Phase 0/2).
def require_client(request: Request) -> dict        # FastAPI Depends

def ensure_bootstrap_admin() -> None
    # If core_store has zero admins and cfg.admin_bootstrap_email/password
    # are both set, create one. Called from main.py's lifespan, after
    # core_store.ensure_schema(). Idempotent — a no-op once an admin exists.

def register(app: FastAPI) -> None
    # POST /api/auth/login   {email, password} -> sets cookie, 401 on failure.
    #   Tries core_store.get_admin_by_email, then
    #   core_store.get_practitioner_by_email, then
    #   core_store.get_client_directory_entry (email) -> if found, verify the
    #   client's password_hash by opening that vault (import app.vault
    #   lazily inside the function body, not at module load — vault.py may
    #   not exist yet when this file is authored in parallel).
    # POST /api/auth/logout  -> clears cookie.
    # GET  /api/auth/me      -> current_session() or 401.
```

**Do not** import `app.vault` at module level — only inside the client-login
branch of the login handler, deferred, so this file works standalone before
`app/vault.py` exists.

---

## `app/core_store.py` (owner: core-data)

`app/core_store.py` already exists with `ensure_schema()`, `_connect()`,
`ping()`, `log(actor, action, detail)`, and the full schema (see the file).
**Add these functions to the same file** — do not change the schema unless
a function below needs a column it doesn't have yet (say so in your report
rather than guessing).

```python
# Admins
def create_admin(email: str, password_hash: str, name: str) -> dict
def get_admin_by_email(email: str) -> dict | None

# Practitioners
def create_practitioner_pending(
    email: str, password_hash: str, name: str, bio: str = "",
    specialties: list[str] | None = None, languages: list[str] | None = None,
    years_experience: int = 0, consultation_price_cents: int = 0) -> dict
    # status="pending", plan="basic". specialties/languages stored as JSON.
def get_practitioner(practitioner_id: str) -> dict | None
    # specialties_json/languages_json decoded back to lists on the way out.
def get_practitioner_by_email(email: str) -> dict | None
def list_practitioners(status: str | None = None) -> list[dict]
def approve_practitioner(practitioner_id: str) -> dict | None
def reject_practitioner(practitioner_id: str) -> dict | None
def suspend_practitioner(practitioner_id: str) -> dict | None
def set_plan(practitioner_id: str, plan: str) -> dict | None
    # plan in ("basic", "pro"). Just the DB flip — vault creation is
    # activate_pro(), below, which calls this.
def update_practitioner_profile(practitioner_id: str, **fields) -> dict | None
    # Whitelist: name, bio, specialties, languages, years_experience,
    # consultation_price_cents, photo_path. Unknown keys raise ValueError.
def set_practitioner_api_key(practitioner_id: str, encrypted_key: str | None) -> None
    # Write-only from the API's perspective — no getter is exposed publicly;
    # only app/llm.py's consult path reads anthropic_api_key_encrypted, via
    # get_practitioner().
def set_stripe_fields(
    practitioner_id: str, customer_id: str | None = None,
    subscription_id: str | None = None, status: str | None = None) -> dict | None
    # Updates only the fields passed (None = leave unchanged).

def activate_pro(practitioner_id: str) -> dict
    # set_plan(id, "pro"), then ensure a vault exists. Idempotent: if
    # data/vaults/<id>.db already exists, don't recreate it (downgrade then
    # re-upgrade reuses the same vault — specs/v2/09-payments.md#downgrade).
    # Import app.vault lazily inside the function (same reasoning as
    # auth.py's deferred import — core_store.py may be authored/run before
    # vault.py exists).

# Contact forms
def create_contact_submission(
    practitioner_id: str, client_name: str, client_email: str,
    message: str) -> dict
def list_contact_submissions(
    practitioner_id: str | None = None, status: str | None = None) -> list[dict]
def update_contact_status(submission_id: str, status: str) -> dict | None
    # status in ("new", "contacted", "closed")

# Analytics
def log_profile_view(practitioner_id: str) -> None
def site_stats() -> dict
    # {"total_views": int, "total_contacts": int}
def practitioner_stats(practitioner_id: str) -> dict
    # {"views": int, "contacts": int}

# Questionnaires (versioned — see specs/v2/02-data-model.md)
def create_questionnaire(
    title: str, questions: list[dict], created_by: str) -> dict
    # questions: [{"prompt": str, "input_type": str, "options": list[str]}]
    # version=1, is_active=1, and flips every other questionnaire's
    # is_active to 0 (only one active at a time).
def edit_questionnaire(
    questionnaire_id: str, title: str, questions: list[dict],
    created_by: str) -> dict
    # Creates a NEW row (version = old.version + 1, is_active=1), flips the
    # old version's is_active off. Never mutates a version in place — a
    # client's already-submitted response stays attached to the version it
    # actually answered.
def get_active_questionnaire() -> dict | None
    # Includes its questions, ordinal-ordered.
def get_questionnaire(questionnaire_id: str) -> dict | None
def list_questionnaires() -> list[dict]
    # All versions, newest first.

# Client directory (routing pointer only — see the schema's own comment)
def add_client_directory_entry(
    email: str, practitioner_id: str, client_id: str) -> None
def get_client_directory_entry(email: str) -> dict | None
    # {"email", "practitioner_id", "client_id"} or None.
```

Every write function calls `log(actor, action, detail)` for admin-audit-
worthy actions (approve/reject/suspend/plan change/questionnaire edit), same
pattern as `patients.py`'s `log()` calls in `main.py` today. Do not log a
client's name, email, or message content here — that's the same
patient-data-never-in-the-library-store boundary v1 drew and re-broke once
(see `specs/v1/07-security.md#the-leak-that-was-found`); a contact
submission's existence can be logged, its content should not be.

---

## `app/vault.py` (new — owner: vault) and `app/vault_files.py` (new — same owner)

`app/vault.py` is `app/patients.py`'s exact schema and function set, with
every function taking a leading `practitioner_id: str` and resolving its
own SQLite file instead of a global `cfg.sqlite_path`:

```python
def _connect(practitioner_id: str) -> sqlite3.Connection
    # Path(cfg.vaults_path) / f"{practitioner_id}.db", mkdir parents.

def ensure_schema(practitioner_id: str) -> None
    # Same tables as patients.py (patients -> clients) PLUS:
    #   questionnaire_responses(id, client_id, questionnaire_id,
    #     questionnaire_version, answers_json, submitted_at)
    #   uploaded_files(id, client_id, original_name, media_type,
    #     storage_path, uploaded_at)
    #   wearable_connections(id, client_id, provider, status, connected_at)
    #   wearable_data_points(id, client_id, provider, metric, value,
    #     recorded_at)

def ping(practitioner_id: str) -> bool

def create_client(
    practitioner_id: str, name: str, email: str, password_hash: str,
    dob: str | None = None, country: str | None = None) -> dict
def get_client(practitioner_id: str, client_id: str) -> dict | None
def get_client_by_email(practitioner_id: str, email: str) -> dict | None
def list_clients(practitioner_id: str) -> list[dict]
def delete_client(practitioner_id: str, client_id: str) -> bool
    # Same redact-audit-not-delete-it behavior as patients.delete_patient.

def add_entry(practitioner_id: str, client_id: str, kind: str, content: str) -> dict
    # kind in patients.py's KINDS tuple, reused verbatim.

def create_session(practitioner_id: str, client_id: str, title: str) -> dict
def add_turn(practitioner_id: str, session_id: str, question: str,
             answer: str, payload: dict) -> None
def list_sessions(practitioner_id: str, client_id: str) -> list[dict]
def get_session(practitioner_id: str, session_id: str) -> dict | None
def session_history(practitioner_id: str, session_id: str) -> list[dict]
def session_transcript(practitioner_id: str, session_id: str) -> str

def log(practitioner_id: str, actor: str, action: str, detail: str,
        client_id: str | None = None) -> None
def audit(practitioner_id: str, limit: int = 100) -> list[dict]
def client_file_text(practitioner_id: str, client_id: str) -> str
    # patients.patient_file_text's flattening logic, same shape.

def save_questionnaire_response(
    practitioner_id: str, client_id: str, questionnaire_id: str,
    questionnaire_version: int, answers: dict) -> dict
def get_questionnaire_response(practitioner_id: str, client_id: str) -> dict | None

def create_wearable_connection(
    practitioner_id: str, client_id: str, provider: str) -> dict
    # provider in ("oura", "whoop", "garmin"). status="connected".
def seed_fixture_wearable_data(
    practitioner_id: str, client_id: str, provider: str) -> list[dict]
    # Writes a handful of representative sample wearable_data_points rows.
    # This IS the v2 stand-in for a live vendor pull — label it clearly in
    # a comment so nobody mistakes it for real later.
def list_wearable_data(practitioner_id: str, client_id: str) -> list[dict]
```

`app/vault_files.py` mirrors `app/originals.py` exactly, parameterized:

```python
def _dir(practitioner_id: str) -> Path
    # Path(cfg.vault_files_path) / practitioner_id, mkdir parents.
def save(practitioner_id: str, file_id: str, raw: bytes, filename: str) -> bool
def path(practitioner_id: str, file_id: str, filename: str) -> Path | None
def delete(practitioner_id: str, file_id: str) -> None
```

---

## `app/llm.py` (owner: llm — edits an existing file, self-contained)

Add, without changing any prompt/schema constant:

```python
def client_for(api_key: str | None) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key) if api_key else _client
```

Give these functions a trailing `client: anthropic.Anthropic | None = None`
parameter, and use `(client or _client)` wherever the function currently
reaches for `_client` directly, or pass `client=client` down into
`_json_call`:

- `_json_call(model, system, prompt, schema, max_tokens=2000, client=None)`
- `question_concepts(question, patient_file, history=None, client=None)`
- `select_sources(question, patient_file, cards, history=None, client=None)`
- `answer(question, patient_file, passages, history=None, client=None)`
- `check(question, answer_text, patient_file, passages, client=None)`
- `summarize_session(transcript, client=None)`

**Do not touch** `read_source`, `extract_concepts`, `merge_labels`, `ping` —
they always run on the platform key (admin ingestion operations), no
parameter change needed.

---

## `app/billing.py` (new — owner: billing)

```python
def create_checkout_session(practitioner_id: str, email: str) -> str
    # Returns the Stripe Checkout redirect URL for cfg.stripe_price_id_pro.
    # success_url/cancel_url point back at cfg.public_base_url.

def handle_webhook(payload: bytes, sig_header: str) -> dict
    # stripe.Webhook.construct_event(payload, sig_header, cfg.stripe_webhook_secret)
    # checkout.session.completed      -> core_store.activate_pro(practitioner_id)
    #                                     (practitioner_id resolved from session
    #                                     metadata set at checkout creation)
    #                                     + core_store.set_stripe_fields(...)
    # customer.subscription.updated   -> core_store.set_stripe_fields(status=...)
    # customer.subscription.deleted   -> core_store.set_plan(id, "basic")
    #                                     (vault untouched, per 09-payments.md)
    # invoice.payment_failed          -> core_store.set_stripe_fields(status="past_due")
    # Returns {"handled": <event type>}.

def billing_portal_url(customer_id: str) -> str
    # stripe.billing_portal.Session.create(...).url

def register(app: FastAPI) -> None
    # POST /api/me/upgrade         Depends(auth.require_practitioner) -> {"url": ...}
    # POST /api/stripe/webhook     no auth (verified by signature instead)
    # GET  /api/me/billing-portal  Depends(auth.require_pro_practitioner) -> {"url": ...}
```

`stripe.api_key = cfg.stripe_secret_key` set once at module load, same
singleton-config pattern as `app/llm.py`'s `_client`.

---

## `app/wearables.py` (new — owner: wearables)

```python
PROVIDERS = {
    "oura":   {"client_id": cfg.oura_client_id,   "client_secret": cfg.oura_client_secret,
               "authorize_url": "...", "token_url": "..."},
    "whoop":  {...},
    "garmin": {...},
}
    # Real endpoints per vendor docs; if a vendor's OAuth shape doesn't fit
    # this dict (e.g. Garmin's OAuth1-style flow), say so in your report
    # rather than forcing it to match — that's a real constraint, not
    # something to paper over.

def connect_url(provider: str, practitioner_id: str, client_id: str) -> str
    # Builds the vendor authorize URL with redirect_uri =
    # f"{cfg.public_base_url}/api/me/wearables/{provider}/callback", and a
    # signed state param encoding (practitioner_id, client_id) so the
    # callback can't be redirected to write into someone else's vault.

def handle_callback(provider: str, code: str, state: str) -> dict
    # Verifies state, exchanges code for a token (real HTTP call — but per
    # spec, what happens NEXT is fixture data, not a live metrics pull):
    #   vault.create_wearable_connection(practitioner_id, client_id, provider)
    #   vault.seed_fixture_wearable_data(practitioner_id, client_id, provider)
    # Returns a payload that clearly marks the data as sample/fixture, e.g.
    # {"connected": True, "provider": provider, "data": "sample"}.

def register(app: FastAPI) -> None
    # POST /api/me/wearables/{provider}/connect  Depends(auth.require_client)
    # GET  /api/me/wearables/{provider}/callback  (no cookie auth — state
    #      param carries identity, per OAuth convention)
```

---

## Frontend (new directories — owner: frontend)

`static/public/` (about, practitioner-directory, coach-detail,
practitioner-signup, client-signup), `static/practitioner/` (profile editor,
contacts inbox — Basic; client list, consult, Pro upgrade — Pro),
`static/client/` (questionnaire, file upload, wearable connect buttons).

Reuse `static/style.css`'s existing classes (cards, chip/pill, form
controls — grep `app.js`/`index.html` for the class names in use) rather
than inventing new ones. Vanilla JS `fetch()` calls against the routes
listed in `specs/v2/08-api.md`, no build step, no framework — match
`static/app.js`'s existing style (read it first). Each new HTML entry point
is a full page (`<!doctype html>...`), not a fragment — there's no router,
these are server-served static files at their own paths (e.g.
`/static/public/directory.html`).

---

## Route-to-dependency table (for the integrator's reference — do not wire
routes yourselves; `app/main.py` is the integrator's file)

| Route prefix | Dependency |
|---|---|
| `/api/practitioners`, `/api/practitioners/{id}`, `/api/practitioners/{id}/contact`, `/api/clients` (signup), `/api/health` | none (public) |
| `/api/auth/*` | none / self-contained |
| `/api/sources*`, `/api/graph`, `/api/relink`, `/api/consolidate`, `/api/coverage`, `/api/audit`, `/api/facets`, `/api/admin/*` | `auth.require_admin` |
| `/api/me/profile`, `/api/me/contacts`, `/api/me/upgrade`, `/api/me/billing-portal` | `auth.require_practitioner` (profile/contacts work on Basic too) |
| `/api/me/clients*`, `/api/me/consult`, `/api/me/anthropic-key` | `auth.require_pro_practitioner` |
| `/api/me/questionnaire`, `/api/me/files`, `/api/me/wearables/*` | `auth.require_client` |
| `/api/stripe/webhook`, `/api/me/wearables/{provider}/callback` | none (signature/state verified instead) |
