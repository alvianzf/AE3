"""Clinic — FastAPI app for the online clinic platform PoC.

Two portals over two vaults: the admin curates the knowledge library (Neo4j),
the practitioner works a patient file (SQLite) and consults the AI team.
"""
from __future__ import annotations

import asyncio
import io
import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

import neo4j.exceptions
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import core_store, gate, knowledge, llm, originals, patients
from .config import get_config

cfg = get_config()
STATIC = Path(__file__).parent.parent / "static"


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
    patients.ensure_schema()
    core_store.ensure_schema()
    yield


app = FastAPI(title="Clinic — Online Clinic Platform (PoC)", lifespan=lifespan)
gate.register(app)


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
        "patients": probe(patients.ping),
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
) -> dict:
    return knowledge.list_sources(
        search=search, topic=topic, kind=kind, min_grade=min_grade,
        max_grade=max_grade, sort=sort, page=page, per_page=per_page)


@app.get("/api/facets")
def get_facets() -> dict:
    return knowledge.facets()


@app.get("/api/graph")
def get_graph() -> dict:
    """Shape of the knowledge graph, plus anything not yet linked into it."""
    return {**knowledge.graph_stats(), "unlinked": knowledge.unlinked_sources()}


@app.post("/api/relink")
def relink() -> dict:
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
def consolidate() -> dict:
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
def source_related(source_id: str) -> dict:
    if knowledge.get_source(source_id) is None:
        raise HTTPException(404, "no such source")
    return {"concepts": knowledge.concepts_for(source_id),
            "neighbours": knowledge.neighbours_of(source_id)}


@app.get("/api/sources/{source_id}")
def get_source(source_id: str) -> dict:
    source = knowledge.get_source(source_id)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


@app.get("/api/sources/{source_id}/text")
def read_source(source_id: str) -> dict:
    """The source as ingested, so the original stays readable in the library."""
    source = knowledge.source_text(source_id)
    if source is None:
        raise HTTPException(404, "no such source")
    for p in source["passages"]:
        p["locator"] = _locator({**p, "passage_count": len(source["passages"])})
    return source


@app.get("/api/sources/{source_id}/original")
def download_source(source_id: str) -> FileResponse:
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
def regrade(source_id: str, body: GradeUpdate) -> dict:
    if not 1 <= body.grade <= 10:
        raise HTTPException(400, "grade must be between 1 and 10")
    source = knowledge.set_grade(source_id, body.grade)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


@app.delete("/api/sources/{source_id}")
def remove_source(source_id: str) -> dict:
    knowledge.delete_source(source_id)
    return {"deleted": source_id}


@app.get("/api/coverage")
def get_coverage() -> list[dict]:
    return knowledge.coverage()


@app.get("/api/audit")
def get_audit() -> list[dict]:
    """One paper trail for the admin, still two stores underneath.

    Library events live in Neo4j; anything naming a patient or quoting a clinical
    question lives in the SQLite vault. They are merged only for display, and each
    row says which store it came from.
    """
    merged = knowledge.audit() + patients.audit()
    merged.sort(key=lambda e: e["ts"], reverse=True)
    return merged[:100]


# --- Practitioner portal: patients --------------------------------------------

class NewPatient(BaseModel):
    name: str
    country: str = "SK"
    dob: str | None = None


@app.post("/api/patients")
def new_patient(body: NewPatient) -> dict:
    patient = patients.create_patient(body.name, body.country, body.dob)
    # Logged in the patient vault, not the knowledge library: the name is
    # patient data and must not be written outside the vault.
    patients.log("practitioner", "patient created", body.name, patient["id"])
    return patient


@app.get("/api/patients")
def get_patients(search: str = "", country: str = "") -> list[dict]:
    return patients.list_patients(search=search, country=country)


@app.get("/api/patients/{patient_id}/sessions")
def get_sessions(patient_id: str) -> list[dict]:
    if patients.get_patient(patient_id) is None:
        raise HTTPException(404, "no such patient")
    return patients.list_sessions(patient_id)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = patients.get_session(session_id)
    if session is None:
        raise HTTPException(404, "no such consultation")
    return session


@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: str) -> dict:
    patient = patients.get_patient(patient_id)
    if patient is None:
        raise HTTPException(404, "no such patient")
    return patient


@app.delete("/api/patients/{patient_id}")
def remove_patient(patient_id: str) -> dict:
    if not patients.delete_patient(patient_id):
        raise HTTPException(404, "no such patient")
    return {"deleted": patient_id}


class NewEntry(BaseModel):
    kind: str
    content: str


@app.post("/api/patients/{patient_id}/entries")
def add_entry(patient_id: str, body: NewEntry) -> dict:
    if patients.get_patient(patient_id) is None:
        raise HTTPException(404, "no such patient")
    try:
        return patients.add_entry(patient_id, body.kind, body.content)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


class SummaryRequest(BaseModel):
    # Either summarise a stored consultation, or a transcript passed in directly.
    session_id: str | None = None
    transcript: str = ""


@app.post("/api/patients/{patient_id}/summary")
def save_summary(patient_id: str, body: SummaryRequest) -> dict:
    if patients.get_patient(patient_id) is None:
        raise HTTPException(404, "no such patient")
    transcript = body.transcript
    if body.session_id:
        transcript = patients.session_transcript(body.session_id)
    if not transcript.strip():
        raise HTTPException(400, "nothing to summarise")
    summary = llm.summarize_session(transcript)
    entry = patients.add_entry(patient_id, "session_summary", summary)
    patients.log("practitioner", "session summary saved",
                 "Consultation summary written into the record", patient_id)
    return entry


# --- The consultation ---------------------------------------------------------

class Consult(BaseModel):
    patient_id: str
    question: str
    min_grade: int = cfg.min_grade
    run_check: bool = True
    # Continue an existing consultation, or omit to start a new one. History is
    # read from the vault rather than trusted from the client.
    session_id: str | None = None


@app.post("/api/consult")
def consult(body: Consult) -> dict:
    if patients.get_patient(body.patient_id) is None:
        raise HTTPException(404, "no such patient")

    patient_file = patients.patient_file_text(body.patient_id)

    session_id = body.session_id
    if session_id and patients.get_session(session_id) is None:
        raise HTTPException(404, "no such consultation")
    if not session_id:
        session_id = patients.create_session(body.patient_id, body.question)["id"]
    # Read from the vault rather than trusting a client-supplied history, and cap
    # it so a long consultation cannot grow the prompt without bound.
    history = patients.session_history(session_id)[-6:]

    # The grade filter is applied to the catalogue, so a source below the bar is
    # never even offered to the Librarian.
    cards = knowledge.catalogue(body.min_grade)
    chosen, reasoning = llm.select_sources(body.question, patient_file, cards,
                                          history)
    # Traverse rather than just read the chosen sources. The question's concepts
    # anchor the walk, so a relevant passage deep inside a long document is found;
    # reading-order edges rejoin split claims; concept edges reach related passages
    # in sources the Librarian never opened.
    focus = llm.question_concepts(body.question, patient_file, history) if chosen else []
    passages, hops = knowledge.traverse(chosen, body.min_grade, focus)
    available = hops["available"]

    # With nothing retrieved there is nothing to ground an answer in, so the
    # Specialist is not asked. Relying on the prompt to make it decline would
    # leave a real chance of it answering from its own training instead; not
    # calling it makes that impossible rather than unlikely.
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
        answer_text = llm.answer(body.question, patient_file, passages, history)
        if body.run_check:
            verdict = llm.check(body.question, answer_text, patient_file, passages)

    # The question itself is clinical detail about this patient, so it is logged
    # in the vault. The library only ever sees which sources were opened.
    patients.log(
        "practitioner", "question asked",
        f"{body.question[:120]} — {len(chosen)}/{len(cards)} sources opened at "
        f"grade ≥{body.min_grade}",
        body.patient_id,
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
        # How the corpus was walked, so the answer's context is auditable.
        "traversal": hops,
        "sources": [
            {
                "label": f"S{i + 1}",
                "source_id": p["source_id"],
                "title": p["title"],
                "grade": p["grade"],
                # Provenance: everything a clinician needs to find this claim in
                # the original and judge who is making it.
                "locator": _locator(p),
                "origin": p["origin"],
                "author": p["author"],
                "published": p["published"],
                "reference": p["reference"],
                "kind": p["kind"],
                "filename": p["filename"],
                "snippet": p["text"],
                # Why this passage is here: opened by the Librarian, pulled in as a
                # reading-order neighbour, or linked by shared concepts.
                "via": p.get("via", "opened"),
                "shared": p.get("shared") or [],
            }
            for i, p in enumerate(passages)
        ],
    }
    # Persist the turn so the consultation can be reopened later, and so a
    # follow-up question has the history to resolve against.
    patients.add_turn(session_id, body.question, answer_text,
                      {k: v for k, v in result.items()
                       if k not in ("answer", "session_id")})
    return result


# --- Frontend -----------------------------------------------------------------

app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
