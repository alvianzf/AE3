"""Clinic — FastAPI app for the online clinic platform.

v2: a public website, an admin portal (practitioner management + the
knowledge library, unchanged from v1), a practitioner portal (Basic profile
only / Pro adds RAG + a client vault), and a client portal. Real per-role
accounts (app/auth.py) replace v1's single shared passphrase.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import mimetypes
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import neo4j.exceptions
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, billing, core_store, knowledge, llm, originals, vault, vault_files, wearables
from .config import get_config

cfg = get_config()
STATIC = Path(__file__).parent.parent / "static"
Path(cfg.photos_path).mkdir(parents=True, exist_ok=True)

# Encrypts/decrypts a practitioner's own Anthropic API key at rest. Falls
# back to a per-process ephemeral key when unconfigured — fine for local
# development (matches config.py's other dev-only defaults), but any real
# deployment must set VAULT_ENCRYPTION_KEY or every stored key becomes
# undecryptable across a restart.
_fernet = Fernet(cfg.vault_encryption_key.encode()) if cfg.vault_encryption_key \
    else Fernet(Fernet.generate_key())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On a cold boot Neo4j is still opening its bolt port when we start, so wait
    # for it rather than exiting and letting the supervisor crash-loop us.
    last: Exception | None = None
    for attempt in range(30):
        try:
            knowledge.ensure_schema()
            last = None
            break
        except Exception as exc:
            last = exc
            await asyncio.sleep(2)
    if last is not None:
        raise RuntimeError(f"Neo4j unreachable after 60s: {last}")
    core_store.ensure_schema()
    auth.ensure_bootstrap_admin()
    yield


app = FastAPI(title="Clinic — Online Clinic Platform", lifespan=lifespan)
auth.register(app)
billing.register(app)
wearables.register(app)


# --- Ops ----------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    def probe(fn):
        try:
            fn()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:200]}

    return {
        "neo4j": probe(knowledge.ping),
        "anthropic": probe(llm.ping),
        "core": probe(core_store.ping),
        "stats": knowledge.stats(),
    }


# --- Admin portal: the knowledge library --------------------------------------

def _extract_pages(filename: str, raw: bytes) -> list[tuple[int | None, str]]:
    """Return [(page_number, text), ...].

    PDFs are read page by page so a citation can name the page it came from.
    Plain text has no pagination, so its page number is None.
    """
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader

        return [(i + 1, page.extract_text() or "")
                for i, page in enumerate(PdfReader(io.BytesIO(raw)).pages)]
    return [(None, raw.decode("utf-8", errors="replace"))]


def _media_type(filename: str) -> str:
    """Fallback when the browser sent no content type on the upload."""
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _locator(p: dict) -> str:
    """Where in the source this passage sits, for the clinician to look up."""
    if p.get("page_start"):
        if p["page_end"] and p["page_end"] != p["page_start"]:
            return f"pages {p['page_start']}–{p['page_end']}"
        return f"page {p['page_start']}"
    total = p.get("passage_count") or 0
    if total:
        return f"passage {p['ordinal'] + 1} of {total}"
    return f"passage {p['ordinal'] + 1}"


@app.post("/api/sources")
async def add_source(
    kind: str = Form("article"),
    origin: str = Form("unspecified"),
    text: str = Form(""),
    replaces: str = Form(""),
    file: UploadFile | None = None,
    _admin: dict = Depends(auth.require_admin),
) -> dict:
    """Upload a source, or paste one. Read → tag → grade → split into passages.

    An exact re-upload is refused with 409 rather than quietly creating a second
    copy — the Reader is generative, so duplicates get different titles, summaries
    and grades and are near-impossible to spot in the library. Pass `replaces`
    with the existing source's id to supersede it deliberately.
    """
    original: tuple[bytes, str, str] | None = None
    if file is not None and file.filename:
        raw = await file.read()
        filename = file.filename
        pages = _extract_pages(filename, raw)
        # Keep the file itself as well as the passages: extraction drops tables,
        # figures and layout, and a clinician checking a citation needs the
        # document rather than our reading of it.
        original = (raw, filename,
                    file.content_type or _media_type(filename))
    else:
        filename = "pasted text"
        pages = [(None, text)]

    page_count = sum(1 for n, _ in pages if n is not None)
    body = "\n\n".join(t.strip() for _, t in pages if t.strip()).strip()
    if not body:
        raise HTTPException(
            400,
            "No text could be read from this source. If it is a scanned PDF, the "
            "pages are images and would need OCR before they can be ingested.",
        )

    digest = knowledge.content_hash(body)
    existing = knowledge.find_by_hash(digest)
    if existing and existing["id"] != replaces:
        raise HTTPException(409, {
            "message": (
                f'This is already in the library as "{existing["title"]}" '
                f'(grade {existing["grade"]}, ingested '
                f'{existing["created_at"][:10]}). Nothing was added.'
            ),
            "duplicate_of": existing["id"],
        })

    # Show the Reader the shelves already in use so it files this source
    # beside its neighbours instead of coining a new label.
    card = llm.read_source(body, filename, kind, origin,
                           known_topics=knowledge.all_topics())

    # Remove the superseded source only once the new one has been read, so a
    # failure part-way through does not leave the library short.
    if replaces:
        knowledge.delete_source(replaces)

    passages = knowledge.chunk_pages(pages)
    # Index each passage's concepts now, so it is connected to the rest of the
    # corpus the moment it lands rather than sitting as an island.
    try:
        for p, concepts in zip(passages, llm.extract_concepts(
                [p["text"] for p in passages])):
            p["concepts"] = concepts
    except Exception as exc:  # linking is additive; never lose the source over it
        logging.warning("concept extraction failed for %s: %s", filename, exc)

    try:
        return knowledge.ingest_source(
            title=card["title"], filename=filename, kind=kind, origin=origin,
            grade=card["suggested_grade"], summary=card["summary"],
            topics=card["topics"], passages=passages,
            digest=digest, body=body, author=card["author"],
            published=card["published"], reference=card["reference"],
            page_count=page_count, original=original,
        )
    except neo4j.exceptions.ConstraintError:
        # Another upload of the same body landed between our check and our write.
        raise HTTPException(409, {
            "message": "That source was ingested by another upload just now. "
                       "Nothing was added.",
            "duplicate_of": None,
        })


@app.get("/api/sources")
def get_sources(
    search: str = "", topic: str = "", kind: str = "",
    min_grade: int = 1, max_grade: int = 10,
    sort: str = "newest", page: int = 1, per_page: int = 10,
    _admin: dict = Depends(auth.require_admin),
) -> dict:
    return knowledge.list_sources(
        search=search, topic=topic, kind=kind, min_grade=min_grade,
        max_grade=max_grade, sort=sort, page=page, per_page=per_page)


@app.get("/api/facets")
def get_facets(_admin: dict = Depends(auth.require_admin)) -> dict:
    return knowledge.facets()


@app.get("/api/graph")
def get_graph(_admin: dict = Depends(auth.require_admin)) -> dict:
    """Shape of the knowledge graph, plus anything not yet linked into it."""
    return {**knowledge.graph_stats(), "unlinked": knowledge.unlinked_sources()}


@app.post("/api/relink")
def relink(_admin: dict = Depends(auth.require_admin)) -> dict:
    """Index concepts for sources that have none.

    Sources ingested before linking existed are islands: reachable when the
    Librarian opens them, invisible to traversal. This connects them.
    """
    done, failed = [], []
    for src in knowledge.unlinked_sources():
        full = knowledge.source_text(src["id"])
        if not full or not full["passages"]:
            failed.append(src["title"])
            continue
        try:
            concepts = llm.extract_concepts([p["text"] for p in full["passages"]])
            edges = knowledge.link_source(src["id"], concepts)
            knowledge.log("admin", "linked",
                          f"{src['title']} — {edges} concept links")
            done.append({"title": src["title"], "edges": edges})
        except Exception as exc:
            logging.warning("relink failed for %s: %s", src["title"], exc)
            failed.append(src["title"])
    return {"linked": done, "failed": failed, **knowledge.graph_stats()}


@app.post("/api/consolidate")
def consolidate(_admin: dict = Depends(auth.require_admin)) -> dict:
    """Let the model tidy the index, then rewrite the graph to match.

    The alias table in knowledge.py catches the predictable cases; this catches
    the tail — two labels for one idea that no static map anticipated. Merging
    them turns two disconnected halves of the library into one.
    """
    out = {}
    for label, names in (("Concept", knowledge.all_concepts()),
                         ("Topic", knowledge.all_topics())):
        groups = llm.merge_labels(names)
        absorbed = knowledge.merge_nodes(label, groups) if groups else 0
        if groups:
            knowledge.log("admin", "consolidated",
                          f"{label.lower()}s: " + "; ".join(
                              f"{g['canonical']} ← {', '.join(g['aliases'])}"
                              for g in groups)[:400])
        out[label.lower()] = {"groups": groups, "absorbed": absorbed,
                              "before": len(names)}
    return {**out, **knowledge.graph_stats()}


@app.get("/api/sources/{source_id}/related")
def source_related(source_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    if knowledge.get_source(source_id) is None:
        raise HTTPException(404, "no such source")
    return {"concepts": knowledge.concepts_for(source_id),
            "neighbours": knowledge.neighbours_of(source_id)}


@app.get("/api/sources/{source_id}")
def get_source(source_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    source = knowledge.get_source(source_id)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


@app.get("/api/sources/{source_id}/text")
def read_source(source_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    """The source as ingested, so the original stays readable in the library."""
    source = knowledge.source_text(source_id)
    if source is None:
        raise HTTPException(404, "no such source")
    for p in source["passages"]:
        p["locator"] = _locator({**p, "passage_count": len(source["passages"])})
    return source


@app.get("/api/sources/{source_id}/original")
def download_source(source_id: str, _admin: dict = Depends(auth.require_admin)) -> FileResponse:
    """The uploaded file itself — what the passages were extracted *from*.

    404 when no original was kept: pasted text, a source ingested before the file
    store existed, or an archive write that failed. The UI checks `original_name`
    on the source card rather than probing this.
    """
    source = knowledge.get_source(source_id)
    if source is None:
        raise HTTPException(404, "no such source")
    name = source.get("original_name")
    path = originals.path(source_id, name) if name else None
    if path is None:
        raise HTTPException(404, "no original file was kept for this source")
    # The filename came off the wire, so strip what would break — or forge — the
    # header before echoing it back.
    safe = "".join(c for c in Path(name).name if c.isprintable() and c != '"')
    media_type = source.get("original_media_type") or _media_type(name)
    # The media type is uploader-supplied and we serve from the app's own origin,
    # so anything but the two types we actually want to preview is a download.
    # Rendering an uploaded text/html inline would be stored XSS against the gate
    # cookie. nosniff stops the browser from second-guessing the same decision.
    disposition = ("inline" if media_type in ("application/pdf", "text/plain")
                   else "attachment")
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Content-Disposition": f'{disposition}; filename="{safe}"',
                 "X-Content-Type-Options": "nosniff"},
    )


class GradeUpdate(BaseModel):
    grade: int


@app.patch("/api/sources/{source_id}")
def regrade(source_id: str, body: GradeUpdate,
           _admin: dict = Depends(auth.require_admin)) -> dict:
    if not 1 <= body.grade <= 10:
        raise HTTPException(400, "grade must be between 1 and 10")
    source = knowledge.set_grade(source_id, body.grade)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


@app.delete("/api/sources/{source_id}")
def remove_source(source_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    knowledge.delete_source(source_id)
    return {"deleted": source_id}


@app.get("/api/coverage")
def get_coverage(_admin: dict = Depends(auth.require_admin)) -> list[dict]:
    return knowledge.coverage()


@app.get("/api/audit")
def get_audit(_admin: dict = Depends(auth.require_admin)) -> list[dict]:
    """The library's own paper trail — admin-only.

    Each Pro practitioner's vault carries its own separate audit trail
    (GET /api/me/clients/{id} exposes it per-client); this endpoint is the
    library's, and only the library's, per the same never-mix-the-two-stores
    rule v1 drew (specs/v1/07-security.md#the-leak-that-was-found).
    """
    return knowledge.audit()[:100]


def _decrypt_api_key(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


def _save_photo(practitioner_id: str, file: UploadFile, raw: bytes) -> str:
    suffix = Path(file.filename or "").suffix or ".jpg"
    dest = Path(cfg.photos_path) / f"{practitioner_id}{suffix}"
    dest.write_bytes(raw)
    return f"/photos/{dest.name}"


# --- Public website -------------------------------------------------------------

@app.get("/api/practitioners")
def list_practitioners_public(specialty: str = "", language: str = "") -> list[dict]:
    approved = core_store.list_practitioners(status="approved")
    if specialty:
        approved = [p for p in approved if specialty in p["specialties"]]
    if language:
        approved = [p for p in approved if language in p["languages"]]
    # Every card rendered in the directory counts as a view of that
    # practitioner (specs/v2/03-website.md).
    for p in approved:
        core_store.log_profile_view(p["id"])
    return approved


@app.get("/api/practitioners/{practitioner_id}")
def get_practitioner_public(practitioner_id: str) -> dict:
    practitioner = core_store.get_practitioner(practitioner_id)
    if practitioner is None or practitioner["status"] != "approved":
        raise HTTPException(404, "no such practitioner")
    core_store.log_profile_view(practitioner_id)
    return practitioner


@app.post("/api/practitioners")
async def practitioner_signup(
    name: str = Form(...), email: str = Form(...), password: str = Form(...),
    bio: str = Form(""), specialties: str = Form("[]"), languages: str = Form("[]"),
    years_experience: int = Form(0), consultation_price_cents: int = Form(0),
    photo: UploadFile | None = None,
) -> dict:
    if core_store.get_practitioner_by_email(email) is not None:
        raise HTTPException(409, "An account with that email already exists.")
    practitioner = core_store.create_practitioner_pending(
        email=email, password_hash=auth.hash_password(password), name=name,
        bio=bio, specialties=json.loads(specialties or "[]"),
        languages=json.loads(languages or "[]"),
        years_experience=years_experience,
        consultation_price_cents=consultation_price_cents,
    )
    if photo is not None and photo.filename:
        raw = await photo.read()
        photo_path = _save_photo(practitioner["id"], photo, raw)
        practitioner = core_store.update_practitioner_profile(
            practitioner["id"], photo_path=photo_path)
    return practitioner


class ContactSubmission(BaseModel):
    name: str
    email: str
    message: str


@app.post("/api/practitioners/{practitioner_id}/contact")
def contact_practitioner(practitioner_id: str, body: ContactSubmission) -> dict:
    if core_store.get_practitioner(practitioner_id) is None:
        raise HTTPException(404, "no such practitioner")
    return core_store.create_contact_submission(
        practitioner_id, body.name, body.email, body.message)


class ClientSignup(BaseModel):
    name: str
    email: str
    password: str
    practitioner_id: str | None = None


@app.post("/api/clients")
def client_signup(body: ClientSignup) -> dict:
    password_hash = auth.hash_password(body.password)
    existing = core_store.get_client_directory_entry(body.email)
    if existing is not None:
        # A Pro practitioner pre-created this client (specs/v2/05-practitioner-
        # portal.md); completing signup sets their password rather than
        # creating a duplicate account.
        client = vault.get_client(existing["practitioner_id"], existing["client_id"])
        if client is None:
            raise HTTPException(404, "invited client record is missing")
        vault.set_client_password(existing["practitioner_id"], client["id"], password_hash)
        return {"id": client["id"], "practitioner_id": existing["practitioner_id"]}

    if not body.practitioner_id:
        raise HTTPException(400, "practitioner_id is required for a new client")
    practitioner = core_store.get_practitioner(body.practitioner_id)
    if practitioner is None or practitioner["plan"] != "pro":
        raise HTTPException(400, "That practitioner cannot accept clients right now.")
    client = vault.create_client(body.practitioner_id, body.name, body.email, password_hash)
    core_store.add_client_directory_entry(body.email, body.practitioner_id, client["id"])
    return {"id": client["id"], "practitioner_id": body.practitioner_id}


# --- Admin: practitioner management ---------------------------------------------

@app.get("/api/admin/practitioners")
def admin_list_practitioners(
    status: str = "", _admin: dict = Depends(auth.require_admin),
) -> list[dict]:
    return core_store.list_practitioners(status=status or None)


@app.post("/api/admin/practitioners/{practitioner_id}/approve")
def admin_approve(practitioner_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    practitioner = core_store.approve_practitioner(practitioner_id)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return practitioner


@app.post("/api/admin/practitioners/{practitioner_id}/reject")
def admin_reject(practitioner_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    practitioner = core_store.reject_practitioner(practitioner_id)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return practitioner


@app.post("/api/admin/practitioners/{practitioner_id}/suspend")
def admin_suspend(practitioner_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    practitioner = core_store.suspend_practitioner(practitioner_id)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return practitioner


class PlanUpdate(BaseModel):
    plan: str


@app.put("/api/admin/practitioners/{practitioner_id}/plan")
def admin_set_plan(practitioner_id: str, body: PlanUpdate,
                   _admin: dict = Depends(auth.require_admin)) -> dict:
    if body.plan not in core_store.PLANS:
        raise HTTPException(400, f"unknown plan: {body.plan}")
    if body.plan == "pro":
        try:
            return core_store.activate_pro(practitioner_id)
        except ValueError:
            raise HTTPException(404, "no such practitioner")
    practitioner = core_store.set_plan(practitioner_id, body.plan)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return practitioner


@app.get("/api/admin/stats")
def admin_stats(_admin: dict = Depends(auth.require_admin)) -> dict:
    return core_store.site_stats()


@app.get("/api/admin/practitioners/{practitioner_id}/client-count")
def admin_client_count(practitioner_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    practitioner = core_store.get_practitioner(practitioner_id)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    count = len(vault.list_clients(practitioner_id)) if practitioner["plan"] == "pro" else 0
    return {"practitioner_id": practitioner_id, "clients": count,
            **core_store.practitioner_stats(practitioner_id)}


class QuestionnaireIn(BaseModel):
    title: str
    questions: list[dict]


@app.get("/api/admin/questionnaires")
def admin_list_questionnaires(_admin: dict = Depends(auth.require_admin)) -> list[dict]:
    return core_store.list_questionnaires()


@app.post("/api/admin/questionnaires")
def admin_create_questionnaire(body: QuestionnaireIn,
                               admin: dict = Depends(auth.require_admin)) -> dict:
    return core_store.create_questionnaire(body.title, body.questions, admin["id"])


@app.post("/api/admin/questionnaires/{questionnaire_id}")
def admin_edit_questionnaire(questionnaire_id: str, body: QuestionnaireIn,
                             admin: dict = Depends(auth.require_admin)) -> dict:
    try:
        return core_store.edit_questionnaire(
            questionnaire_id, body.title, body.questions, admin["id"])
    except ValueError:
        raise HTTPException(404, "no such questionnaire")


# --- Practitioner portal ---------------------------------------------------------

@app.get("/api/me/profile")
def me_profile(session: dict = Depends(auth.require_practitioner)) -> dict:
    return core_store.get_practitioner(session["id"])


@app.put("/api/me/profile")
async def me_update_profile(request: Request,
                            session: dict = Depends(auth.require_practitioner)) -> dict:
    practitioner_id = session["id"]
    content_type = request.headers.get("content-type", "")
    allowed = {"name", "bio", "specialties", "languages", "years_experience",
               "consultation_price_cents"}
    fields: dict = {}
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        for key in allowed:
            if key not in form:
                continue
            value = form[key]
            if key in ("specialties", "languages"):
                fields[key] = json.loads(value or "[]")
            elif key == "years_experience" or key == "consultation_price_cents":
                fields[key] = int(value)
            else:
                fields[key] = str(value)
        photo = form.get("photo")
        if photo is not None and getattr(photo, "filename", ""):
            raw = await photo.read()
            fields["photo_path"] = _save_photo(practitioner_id, photo, raw)
    else:
        body = await request.json()
        fields = {k: v for k, v in body.items() if k in allowed}
    practitioner = core_store.update_practitioner_profile(practitioner_id, **fields)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return practitioner


@app.get("/api/me/contacts")
def me_contacts(status: str = "",
                session: dict = Depends(auth.require_practitioner)) -> list[dict]:
    return core_store.list_contact_submissions(
        practitioner_id=session["id"], status=status or None)


class ContactStatusUpdate(BaseModel):
    status: str


@app.patch("/api/me/contacts/{submission_id}")
def me_update_contact(submission_id: str, body: ContactStatusUpdate,
                      session: dict = Depends(auth.require_practitioner)) -> dict:
    owned = core_store.list_contact_submissions(practitioner_id=session["id"])
    if not any(s["id"] == submission_id for s in owned):
        raise HTTPException(404, "no such submission")
    try:
        return core_store.update_contact_status(submission_id, body.status)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


class ApiKeyUpdate(BaseModel):
    api_key: str


@app.post("/api/me/anthropic-key")
def me_set_api_key(body: ApiKeyUpdate,
                   session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    encrypted = _fernet.encrypt(body.api_key.encode()).decode()
    core_store.set_practitioner_api_key(session["id"], encrypted)
    return {"ok": True}


# --- Practitioner portal: Pro clients + consultation -----------------------------

class NewClient(BaseModel):
    name: str
    email: str
    dob: str | None = None
    country: str | None = None


@app.get("/api/me/clients")
def me_list_clients(session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    return vault.list_clients(session["id"])


@app.post("/api/me/clients")
def me_create_client(body: NewClient,
                     session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    # No password yet — the client sets one when they complete signup
    # themselves (POST /api/clients), matched by email via client_directory.
    client = vault.create_client(
        practitioner_id, body.name, body.email,
        password_hash=auth.hash_password(str(uuid.uuid4())),
        dob=body.dob, country=body.country,
    )
    core_store.add_client_directory_entry(body.email, practitioner_id, client["id"])
    vault.log(practitioner_id, "practitioner", "client created", body.name, client["id"])
    return client


@app.get("/api/me/clients/{client_id}")
def me_get_client(client_id: str,
                  session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    client = vault.get_client(session["id"], client_id)
    if client is None:
        raise HTTPException(404, "no such client")
    return client


@app.delete("/api/me/clients/{client_id}")
def me_delete_client(client_id: str,
                     session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    if not vault.delete_client(session["id"], client_id):
        raise HTTPException(404, "no such client")
    return {"deleted": client_id}


class MeConsult(BaseModel):
    client_id: str
    question: str
    min_grade: int = cfg.min_grade
    run_check: bool = True
    session_id: str | None = None


@app.post("/api/me/consult")
def me_consult(body: MeConsult, session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    practitioner = core_store.get_practitioner(practitioner_id)
    if not practitioner.get("anthropic_api_key_encrypted"):
        raise HTTPException(
            400, "Set your Anthropic API key before starting a consultation.")
    client_llm = llm.client_for(_decrypt_api_key(practitioner["anthropic_api_key_encrypted"]))

    if vault.get_client(practitioner_id, body.client_id) is None:
        raise HTTPException(404, "no such client")

    client_file = vault.client_file_text(practitioner_id, body.client_id)

    session_id = body.session_id
    if session_id and vault.get_session(practitioner_id, session_id) is None:
        raise HTTPException(404, "no such consultation")
    if not session_id:
        session_id = vault.create_session(practitioner_id, body.client_id, body.question)["id"]
    history = vault.session_history(practitioner_id, session_id)[-6:]

    cards = knowledge.catalogue(body.min_grade)
    chosen, reasoning = llm.select_sources(body.question, client_file, cards,
                                          history, client=client_llm)
    focus = llm.question_concepts(body.question, client_file, history,
                                  client=client_llm) if chosen else []
    passages, hops = knowledge.traverse(chosen, body.min_grade, focus)
    available = hops["available"]

    matched = bool(passages)
    verdict = None
    if not matched:
        answer_text = (
            "No source in the library answers this question, so I have nothing to "
            "base an answer on and will not guess.\n\n"
            f"Why: {reasoning}\n\n"
            f"{len(cards)} source(s) were available at grade "
            f"≥ {body.min_grade}. Either lower the grade threshold, or add a "
            "source covering this topic to the library."
        )
    else:
        answer_text = llm.answer(body.question, client_file, passages, history,
                                 client=client_llm)
        if body.run_check:
            verdict = llm.check(body.question, answer_text, client_file, passages,
                                client=client_llm)

    vault.log(
        practitioner_id, "practitioner", "question asked",
        f"{body.question[:120]} — {len(chosen)}/{len(cards)} sources opened at "
        f"grade ≥{body.min_grade}",
        body.client_id,
    )
    result = {
        "session_id": session_id,
        "answer": answer_text,
        "matched": matched,
        "min_grade": body.min_grade,
        "check": verdict,
        "librarian": {
            "reasoning": reasoning,
            "considered": len(cards),
            "opened": [
                {"title": c["title"], "grade": c["grade"]}
                for c in cards if c["id"] in chosen
            ],
            "truncated": max(0, available - len(passages)),
        },
        "traversal": hops,
        "sources": [
            {
                "label": f"S{i + 1}",
                "source_id": p["source_id"],
                "title": p["title"],
                "grade": p["grade"],
                "locator": _locator(p),
                "origin": p["origin"],
                "author": p["author"],
                "published": p["published"],
                "reference": p["reference"],
                "kind": p["kind"],
                "filename": p["filename"],
                "snippet": p["text"],
                "via": p.get("via", "opened"),
                "shared": p.get("shared") or [],
            }
            for i, p in enumerate(passages)
        ],
    }
    vault.add_turn(practitioner_id, session_id, body.question, answer_text,
                  {k: v for k, v in result.items()
                   if k not in ("answer", "session_id")})
    return result


# --- Client portal -----------------------------------------------------------------

@app.get("/api/me/questionnaire")
def me_active_questionnaire(session: dict = Depends(auth.require_client)) -> dict | None:
    return core_store.get_active_questionnaire()


class QuestionnaireResponseIn(BaseModel):
    questionnaire_id: str
    questionnaire_version: int
    answers: dict


@app.post("/api/me/questionnaire")
def me_submit_questionnaire(
    body: QuestionnaireResponseIn, session: dict = Depends(auth.require_client),
) -> dict:
    return vault.save_questionnaire_response(
        session["practitioner_id"], session["id"], body.questionnaire_id,
        body.questionnaire_version, body.answers,
    )


@app.post("/api/me/files")
async def me_upload_file(
    file: UploadFile, session: dict = Depends(auth.require_client),
) -> dict:
    practitioner_id, client_id = session["practitioner_id"], session["id"]
    raw = await file.read()
    file_id = str(uuid.uuid4())
    filename = file.filename or "upload"
    if not vault_files.save(practitioner_id, file_id, raw, filename):
        raise HTTPException(500, "could not store the uploaded file")
    return vault.save_uploaded_file(
        practitioner_id, client_id, filename,
        file.content_type or _media_type(filename),
        str(vault_files.path(practitioner_id, file_id, filename)),
    )


# --- Frontend -----------------------------------------------------------------
#
# Clean top-level routes rather than exposing the static/public|practitioner|
# client directory layout in the URL — /static/ is left mounted only for the
# actual assets (css/js) these pages load, not as a way to reach the pages
# themselves.

app.mount("/photos", StaticFiles(directory=cfg.photos_path), name="photos")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _page(*parts: str) -> FileResponse:
    return FileResponse(STATIC.joinpath(*parts))


@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse("/login")


@app.get("/admin")
def admin_page() -> FileResponse:
    # The knowledge-library SPA carried over from v1 (unchanged, per
    # specs/v2/04-admin-portal.md) — its own routes are gated by
    # auth.require_admin, this just serves the shell.
    return _page("index.html")


@app.get("/about")
def about_page() -> FileResponse:
    return _page("public", "about.html")


@app.get("/directory")
def directory_page() -> FileResponse:
    return _page("public", "directory.html")


@app.get("/coach/{practitioner_id}")
def coach_page(practitioner_id: str) -> FileResponse:
    # practitioner_id isn't used server-side — the page reads it from
    # location.pathname and calls the API itself. The path param exists so
    # this route matches /coach/<anything> rather than only /coach.
    return _page("public", "coach.html")


@app.get("/login")
def login_page() -> FileResponse:
    return _page("public", "login.html")


@app.get("/account")
def account_page() -> FileResponse:
    return _page("public", "account.html")


@app.get("/signup")
def client_signup_page() -> FileResponse:
    return _page("public", "client-signup.html")


@app.get("/join")
def practitioner_signup_page() -> FileResponse:
    return _page("public", "practitioner-signup.html")


@app.get("/practitioner/profile")
def practitioner_profile_page() -> FileResponse:
    return _page("practitioner", "profile.html")


@app.get("/practitioner/contacts")
def practitioner_contacts_page() -> FileResponse:
    return _page("practitioner", "contacts.html")


@app.get("/practitioner/clients")
def practitioner_clients_page() -> FileResponse:
    return _page("practitioner", "clients.html")


@app.get("/practitioner/consult")
def practitioner_consult_page() -> FileResponse:
    return _page("practitioner", "consult.html")


@app.get("/practitioner/upgrade")
def practitioner_upgrade_page() -> FileResponse:
    return _page("practitioner", "upgrade.html")


@app.get("/client/questionnaire")
def client_questionnaire_page() -> FileResponse:
    return _page("client", "questionnaire.html")


@app.get("/client/files")
def client_files_page() -> FileResponse:
    return _page("client", "files.html")


@app.get("/client/wearables")
def client_wearables_page() -> FileResponse:
    return _page("client", "wearables.html")
