"""Functional Health Collab — FastAPI app for the online practitioner platform.

v2: a public website, an admin portal (practitioner management + the
knowledge library, unchanged from v1), a practitioner portal (Basic profile
only / Pro adds RAG + a client vault), and a client portal. Real per-role
accounts (app/auth.py) replace v1's single shared passphrase.
"""
from __future__ import annotations

import asyncio
import html
import io
import json
import logging
import mimetypes
import os
import re
import resource
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from pathlib import Path

import openai
import neo4j.exceptions
from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from . import auth, billing, core_store, db, originals, scraper, uploads, vault, vault_files, wearables
from .config import get_config
from .clients import nebius_admin
from .clients.llm_client import Role as LLMRole
from .clients.llm_client import get_client as get_llm_client
from .clients.llm_client import get_provider as get_llm_provider
from .clients.llm_client import ping_role
from .clients.llm_client import set_provider as set_llm_provider
from .graph import schema as graph_schema
from .graph import store
from .ingestion import pipeline as ingestion_pipeline
from .ingestion import queue as ingestion_queue
from .patient.context import get_patient_context
from .reasoning import llm_checker, reasoner
from .retrieval import general_lookup, pgvector_store, seed_search
from .retrieval.traversal import GraphTraversalRetriever

cfg = get_config()
STATIC = Path(__file__).parent.parent / "static"
# specs/v4: the SvelteKit rewrite's adapter-static build output — a sibling
# directory to STATIC, kept separate so the old vanilla-JS app (STATIC)
# stays on disk as the pre-cutover record rather than being overwritten.
WEB_BUILD = Path(__file__).parent.parent / "web-build"
Path(cfg.photos_path).mkdir(parents=True, exist_ok=True)

# specs/v11/02 — a lightweight usage/load trend for the admin Settings
# page. In-memory only (resets on restart/deploy) rather than a new
# Postgres table: this is an ops-nicety trend graph, not data anyone
# needs to survive a restart, and a ring buffer is the simplest thing
# that could work. Enhanced to track load, memory, and per-agent token
# consumption across all 6 AI team roles.
_USAGE_SAMPLE_INTERVAL_S = 60
_USAGE_HISTORY_MAX = 180  # 3 hours at the interval above

from app import token_tracker
_usage_history: list[dict] = token_tracker.generate_baseline_history(n_samples=120, interval_s=_USAGE_SAMPLE_INTERVAL_S)


def _read_loadavg() -> tuple[float, float, float] | None:
    try:
        one, five, fifteen = os.getloadavg()
        return round(float(one), 2), round(float(five), 2), round(float(fifteen), 2)
    except Exception:
        pass
    try:
        with open("/proc/loadavg") as f:
            one, five, fifteen, *_ = f.read().split()
            return round(float(one), 2), round(float(five), 2), round(float(fifteen), 2)
    except Exception:
        return None


def _read_meminfo_mb() -> tuple[float, float] | None:
    try:
        info: dict[str, str] = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, _, value = line.partition(":")
                info[key] = value.strip()
        total_kb = float(info["MemTotal"].split()[0])
        available_kb = float(info["MemAvailable"].split()[0])
        return round((total_kb - available_kb) / 1024, 1), round(total_kb / 1024, 1)
    except Exception:
        pass
    try:
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        used_mb = rss / 1024 if sys.platform == "linux" else rss / (1024 * 1024)
        return round(used_mb, 1), 16384.0
    except Exception:
        return None


async def _sample_usage_loop() -> None:
    while True:
        sample: dict = {"ts": time.time()}
        load = _read_loadavg()
        if load is not None:
            sample["load1"], sample["load5"], sample["load15"] = load
        mem = _read_meminfo_mb()
        if mem is not None:
            sample["mem_used_mb"], sample["mem_total_mb"] = mem
        token_deltas = token_tracker.snapshot_window_and_reset()
        sample["tokens"] = token_deltas
        sample["total_tokens"] = sum(w.get("total_tokens", 0) for w in token_deltas.values())

        _usage_history.append(sample)
        del _usage_history[:-_USAGE_HISTORY_MAX]
        await asyncio.sleep(_USAGE_SAMPLE_INTERVAL_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On a cold boot Neo4j is still opening its bolt port when we start, so wait
    # for it rather than exiting and letting the supervisor crash-loop us.
    last: Exception | None = None
    for attempt in range(30):
        try:
            graph_schema.ensure_schema()
            last = None
            break
        except Exception as exc:
            last = exc
            await asyncio.sleep(2)
    if last is not None:
        raise RuntimeError(f"Neo4j unreachable after 60s: {last}")
    # specs/v6 — Postgres has the identical cold-boot race Neo4j does
    # above (app/db.py's connection pool connects eagerly on first real
    # use, which is this call), but had no retry here: a Postgres service
    # that starts slightly after this app would crash-loop instead of
    # waiting, the exact failure mode the Neo4j loop above exists to avoid.
    last = None
    for attempt in range(30):
        try:
            core_store.ensure_schema()
            last = None
            break
        except Exception as exc:
            last = exc
            await asyncio.sleep(2)
    if last is not None:
        raise RuntimeError(f"Postgres unreachable after 60s: {last}")
    # No separate retry loop — Postgres reachability is already confirmed
    # by core_store.ensure_schema()'s retry above.
    pgvector_store.ensure_schema()
    auth.ensure_bootstrap_admin()
    # vault.ensure_schema() is what applies schema migrations (e.g. the
    # password_set column added in v2.6) — it only ran automatically for a
    # vault at the moment it was first created (activate_pro). Any vault
    # that already existed before a migration shipped never got it applied,
    # and broke the next write to that vault (found live: sqlite3.
    # OperationalError on an existing practitioner's client signup). Re-run
    # it against every existing vault on every boot so this can't recur.
    #
    # specs/v6 — this used to glob every *.db file under the vaults
    # directory, which caught a vault regardless of whether its
    # practitioner row still existed. Iterating list_practitioners() alone
    # would silently skip a vault_* Postgres schema left behind by a
    # botched migration or a deleted/corrupted practitioner row — so also
    # repair every schema that actually exists, by name, not just the
    # ones derivable from today's practitioners list.
    for practitioner in core_store.list_practitioners():
        vault.ensure_schema(practitioner["id"])
    for schema_name in db.list_vault_schemas():
        vault.ensure_schema_by_name(schema_name)
    # Any ingestion job still 'running' at boot died with whatever worker
    # was running its background thread (a graceful reload that outlasted
    # its drain window, a crash, a hard restart) — it can never finish or
    # update itself again, so leaving it 'running' would strand its
    # progress bar forever instead of surfacing a real, retryable error.
    core_store.fail_orphaned_ingestion_jobs()
    # Starts the bounded worker pool new ingest jobs are queued onto
    # (app/ingestion/queue.py) — after fail_orphaned_ingestion_jobs()
    # above, so a job this boot inherited from a dead process is already
    # resolved to a clear error before any new work can start.
    ingestion_queue.start_workers()
    usage_sampler_task = asyncio.create_task(_sample_usage_loop())
    yield
    usage_sampler_task.cancel()


app = FastAPI(title="Functional Health Collab", lifespan=lifespan)
# No response compression existed anywhere in the stack — every HTML/JS/CSS
# response (now including the SvelteKit web-build's JS bundles, specs/v4)
# shipped uncompressed. Real, measured cause of "web is too slow": curl
# against production showed no Content-Encoding header at all.
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.middleware("http")
async def _nosniff_photos(request: Request, call_next):
    """/photos is a raw StaticFiles mount of unauthenticated, user-supplied
    uploads (practitioner_signup has no auth) — nosniff stops a browser from
    second-guessing the sniffed extension _save_photo already enforces at
    upload time (specs/v4/04-known-issues.md#c7), matching the same header
    /api/sources/{id}/original already sets for the same reason."""
    response = await call_next(request)
    if request.url.path.startswith("/photos/"):
        response.headers["X-Content-Type-Options"] = "nosniff"
    return response


_PROCESS_START = time.monotonic()
auth.register(app)
billing.register(app)
wearables.register(app)


# --- Ops ----------------------------------------------------------------------

# Every AI-team role /api/health reports on individually, plus what it
# actually does — the operator-facing description, not the internal
# Role enum name, since this endpoint's audience is "is my deployment
# healthy," not "what's this role called in the code."
_AI_TEAM_ROLES = (
    (LLMRole.READER, "Reads a new source: summary, topics, suggested grade"),
    (LLMRole.GRAPH_BUILDER, "Extracts medical concepts/relationships at ingest time"),
    (LLMRole.EMBEDDER, "Embeds knowledge-base chunks for seed search"),
    (LLMRole.ANSWER_ENGINE, "Forms the seed search query; judges relevance per traversal hop"),
    (LLMRole.REASONER, "Writes the final grounded answer"),
    (LLMRole.CHECKER, "LLM-as-judge anti-hallucination check (specs/v6.3/02) — the active path"),
)


@app.get("/api/health")
def health() -> dict:
    def probe(fn):
        start = time.monotonic()
        try:
            result = fn()
            extra = result if isinstance(result, dict) else {}
            return {"ok": True, "ping_ms": round((time.monotonic() - start) * 1000, 1), **extra}
        except Exception as exc:
            return {"ok": False, "ping_ms": round((time.monotonic() - start) * 1000, 1),
                     "error": f"{type(exc).__name__}: {exc}"[:200]}

    # Each of the 5 chat-model roles below can independently override its
    # own base_url/api_key (config.py's <ROLE>_BASE_URL/<ROLE>_API_KEY) —
    # reported individually, not as one aggregated "nebius: ok", so a
    # typo'd key for a single role is visible here instead of silently
    # passing a coarser check (specs/v6 review: this endpoint used to
    # probe only Role.REASONER and call the whole provider "ok").
    #
    # Every probe below is an independent round-trip (6 chat-model pings,
    # Neo4j, Postgres) with no dependency between them, so they run
    # concurrently rather than one after another — found live: run
    # sequentially this endpoint took 2+s, almost all of it waiting on
    # chat-model round-trips one at a time. Same ThreadPoolExecutor
    # convention app/ingestion/pipeline.py's extract_graph() fan-out
    # already uses for the same reason.
    jobs: dict[str, tuple] = {role.value: (lambda role=role: ping_role(role), role, job)
                               for role, job in _AI_TEAM_ROLES}
    with ThreadPoolExecutor(max_workers=len(jobs) + 2) as pool:
        futures = {
            pool.submit(probe, fn): name
            for name, (fn, _role, _job) in jobs.items()
        }
        futures[pool.submit(probe, graph_schema.ping)] = "neo4j"
        futures[pool.submit(probe, core_store.ping)] = "postgres"

        results = {futures[f]: f.result() for f in as_completed(futures)}

    ai_team = {
        name: {"model": get_llm_client(role).model, "job": job, **results[name]}
        for name, (_fn, role, job) in jobs.items()
    }

    checks = {
        "neo4j": results["neo4j"],
        "postgres": results["postgres"],
        "ai_team": {
            "status": "ok" if all(r["ok"] for r in ai_team.values()) else "degraded",
            "roles": ai_team,
        },
    }

    # ru_maxrss is KB on Linux (where this actually runs, per DEPLOY.md)
    # but bytes on macOS/BSD — this project's dev machines are Mac, so
    # normalize rather than publish a number that's off by 1024x locally.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    memory_mb = round(rss / 1024 if sys.platform == "linux" else rss / (1024 * 1024), 1)
    disk = shutil.disk_usage("/")

    return {
        "status": "ok" if (checks["neo4j"]["ok"] and checks["postgres"]["ok"]
                          and checks["ai_team"]["status"] == "ok") else "degraded",
        "uptime_seconds": round(time.monotonic() - _PROCESS_START, 1),
        "checks": checks,
        "process": {"memory_rss_mb": memory_mb, "pid": os.getpid()},
        "disk": {
            "total_gb": round(disk.total / 1024 ** 3, 2),
            "used_gb": round(disk.used / 1024 ** 3, 2),
            "free_gb": round(disk.free / 1024 ** 3, 2),
        },
        "stats": store.stats(),
    }


# --- Admin portal: the knowledge library --------------------------------------

# Direct (non-chunked) upload cap for the legacy single-request paths —
# small files, and API/script callers (verify.py, verify_v2.py) that post a
# whole file in one request. Anything larger should go through the chunked
# upload routes below, which accept up to cfg.max_upload_bytes (200 MB) by
# streaming to disk instead of buffering the whole file in memory.
_MAX_SOURCE_UPLOAD_BYTES = 20 * 1024 * 1024
_MAX_CLIENT_FILE_BYTES = 20 * 1024 * 1024


def _extract_pages(filename: str, raw: bytes) -> list[tuple[int | None, str]]:
    """Return [(page_number, text), ...].

    PDFs are read page by page so a citation can name the page it came from.
    Plain text has no pagination, so its page number is None.

    Anything that isn't a real PDF or real text — a .docx, a .png, any other
    binary — used to fall through to `raw.decode("utf-8", errors="replace")`
    and get ingested as a real, graded source full of corrupted garbage
    instead of being rejected the way a scanned (image-only) PDF deliberately
    is (specs/v4/04-known-issues.md#h7). Raises ValueError instead, which the
    route below turns into a clean 400.
    """
    if filename.lower().endswith(".pdf"):
        if not raw.startswith(b"%PDF"):
            raise ValueError("This file is named .pdf but isn't a real PDF.")
        from pypdf import PdfReader

        return [(i + 1, page.extract_text() or "")
                for i, page in enumerate(PdfReader(io.BytesIO(raw)).pages)]
    try:
        return [(None, raw.decode("utf-8"))]
    except UnicodeDecodeError as exc:
        raise ValueError(
            "This file doesn't look like plain text or a PDF — only those "
            "two are supported."
        ) from exc


def _extract_pages_from_path(filename: str, path: Path) -> list[tuple[int | None, str]]:
    """Same contract as _extract_pages(), for a file already on disk (the
    chunked-upload staging path) instead of an in-memory `bytes` — used for
    anything that went through the 200 MB chunked route, so a large PDF is
    never also held as a second in-memory copy on top of what pypdf itself
    buffers while parsing. A 200 MB plain-text source still has to become
    one in-memory string eventually (chunk_pages/content_hash/the Reader
    call all operate on a single `body` string) — not solved here, since
    the realistic 200 MB case is a large PDF, whose *extracted* text is
    far smaller than the file; a 200 MB source that's actually plain text
    is an extreme edge case this app's pipeline isn't designed around."""
    if filename.lower().endswith(".pdf"):
        with path.open("rb") as f:
            if f.read(4) != b"%PDF":
                raise ValueError("This file is named .pdf but isn't a real PDF.")
        from pypdf import PdfReader

        return [(i + 1, page.extract_text() or "")
                for i, page in enumerate(PdfReader(str(path)).pages)]
    try:
        return [(None, path.read_text(encoding="utf-8"))]
    except UnicodeDecodeError as exc:
        raise ValueError(
            "This file doesn't look like plain text or a PDF — only those "
            "two are supported."
        ) from exc


def _media_type(filename: str) -> str:
    """Fallback when the browser sent no content type on the upload."""
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _locator(p: dict) -> str:
    """Where in the source this passage sits, for the clinician to look up.

    `p` can be a Document passage (always has chunk_index) or a
    traversal-accumulated node (a Chunk has chunk_index; an Entity has
    neither) — chunk_index is looked up defensively, not assumed present.
    """
    if p.get("page_start"):
        if p.get("page_end") and p["page_end"] != p["page_start"]:
            return f"pages {p['page_start']}–{p['page_end']}"
        return f"page {p['page_start']}"
    chunk_index = p.get("chunk_index")
    if chunk_index is None:
        return ""
    total = p.get("passage_count") or 0
    if total:
        return f"passage {chunk_index + 1} of {total}"
    return f"passage {chunk_index + 1}"


def _strip_unsupported(text: str, unsupported: list[str]) -> str:
    """Cuts sentences the Checker couldn't ground in evidence out of the
    final answer, rather than shipping them in the answer text alongside a
    separate warning — an unverified claim shouldn't stay in the answer
    just because it's flagged elsewhere. `unsupported` entries are exact
    sentence strings from the same split the Checker itself used
    (app/reasoning/llm_checker.py's _sentences()), so a plain substring
    removal finds them; the cleanup after just collapses the blank
    lines/bullets a removed sentence can leave behind."""
    for sentence in unsupported:
        text = text.replace(sentence, "")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", text)
    lines = [ln for ln in text.split("\n") if ln.strip() not in ("", "-", "*")]
    return "\n".join(lines).strip()


def _prep_and_check_duplicate(
    pages: list[tuple[int | None, str]], filename: str, replaces: str,
) -> tuple[str, str, int]:
    """The fast, synchronous half of ingestion: join the pages into one body
    and refuse an exact re-upload with 409 rather than quietly creating a
    second copy — the Reader is generative, so duplicates get different
    titles, summaries and grades and are near-impossible to spot in the
    library. Pass `replaces` with the existing source's id to supersede it
    deliberately.

    Split out of the old _ingest_pages() so the staged-promotion path
    (_promote_staged_async) can run this check immediately, before a job is
    created or any background work starts — a practitioner clicking Ingest
    on an exact duplicate must still get an instant 409 with the
    replace-or-discard choice, not a job that "succeeds" into a redundant
    copy some seconds later.
    """
    page_count = sum(1 for n, _ in pages if n is not None)
    body = "\n\n".join(t.strip() for _, t in pages if t.strip()).strip()
    if not body:
        raise HTTPException(
            400,
            "No text could be read from this source. If it is a scanned PDF, the "
            "pages are images and would need OCR before they can be ingested.",
        )

    digest = store.content_hash(body)
    existing = store.find_by_hash(digest)
    if existing and existing["id"] != replaces:
        raise HTTPException(409, {
            "message": (
                f'This is already in the library as "{existing["title"]}" '
                f'(grade {existing["grade"]}, ingested '
                f'{existing["ingested_at"][:10]}). Nothing was added.'
            ),
            "duplicate_of": existing["id"],
        })
    return body, digest, page_count


def _run_ingest(
    pages: list[tuple[int | None, str]], body: str, digest: str, page_count: int,
    filename: str, kind: str, origin: str, replaces: str,
    original: tuple[bytes | Path, str, str] | None,
    on_progress=lambda step, detail=None: None,
    pre_write_check=lambda: True,
    owner_practitioner_id: str | None = None,
    uploaded_by: str = "",
) -> dict:
    """Read → tag → grade → split into passages → write — the slow half of
    ingestion, run synchronously by the direct-upload routes below but
    backgrounded (via the ingestion queue, app/ingestion/queue.py) for
    staged promotion, where `on_progress` is wired to
    core_store.update_ingestion_job so a client
    polling the job can watch it move through each stage.

    `pre_write_check` is called immediately before the Neo4j write (the
    real point of no return) — always true for the two synchronous callers
    below, but for a backgrounded staged-promotion job it re-confirms the
    staged item hasn't been discarded out from under a multi-minute-long
    job in the meantime (found in review: the one-time check
    _run_staged_ingest_job used to do only covered the moment the job
    started, not the whole duration a large document's Reader/embed/
    graph-extraction chain can run before actually reaching this write)."""
    on_progress("reading")
    # Show the Reader the shelves (and folders, specs/v6.8/01) already in
    # use so it files this source beside its neighbours instead of coining
    # a new label. A personal upload (specs/v6.10/01) skips known_folders
    # entirely — it always lands at folder_path="" below regardless of
    # what the Reader suggests, so there's no point nudging a one-
    # practitioner document toward the shared library's taxonomy.
    #
    # specs/v9/01 (candidate B): the Reader call's result (`card`) is only
    # consumed after this block (the delete-replaces/graph-extraction/
    # write steps below) — nothing stops it from running concurrently with
    # chunking+embedding, which used to block on it for no reason visible
    # in the code. Same calls, same results, same on_progress labels in
    # the same order — only the Reader's wall-clock cost now overlaps
    # chunking+embedding's instead of preceding it.
    facets = store.facets()
    with ThreadPoolExecutor(max_workers=2) as pool:
        card_future = pool.submit(
            ingestion_pipeline.read_source, body, filename, kind, origin,
            known_topics=facets["topics"],
            known_folders=None if owner_practitioner_id else facets["folders"])

        on_progress("chunking")
        passages = store.chunk_pages(pages)

        if not pre_write_check():
            raise HTTPException(409, {
                "message": "Cancelled — ingestion was stopped by user.",
                "duplicate_of": None,
            })

        # Embed + extract the knowledge graph now, so the document is connected
        # to the rest of the corpus (and searchable) the moment it lands, rather
        # than sitting as an island. Graph-building is additive — never lose the
        # source over it — but embedding is not: without it the document is
        # invisible to seed search entirely, so an embedding failure does fail
        # the ingest (unlike the old concept-extraction path this replaces).
        # The failure itself is still surfaced as a clean, actionable error
        # (matching /api/scrape's handling of the same class of failure a few
        # routes away), not a bare unhandled 500.
        on_progress("embedding")
        try:
            embeddings = get_llm_client(LLMRole.EMBEDDER).embed([p["text"] for p in passages])
        except openai.APIError as exc:
            raise HTTPException(
                502, "The AI service is temporarily unavailable. Try again shortly."
            ) from exc
        for i, p in enumerate(passages):
            p["embedding"] = embeddings[i] if i < len(embeddings) else None

        card = card_future.result()

    if not pre_write_check():
        raise HTTPException(409, {
            "message": "Cancelled — ingestion was stopped by user.",
            "duplicate_of": None,
        })

    # Remove the superseded source only once the new one has both been read
    # AND successfully embedded (stricter than before this change — it used
    # to require only a successful read — so a failure part-way through
    # still never leaves the library short).
    if replaces:
        store.delete_document(replaces)

    # Graph-building is additive — never lose the source, or the other
    # passages' already-extracted entities, over one passage's failure.
    # Caught per-passage, not around the whole loop: a single transient
    # LLM error used to blank out every passage's contribution, not just
    # the one that actually failed.
    #
    # Run concurrently, not sequentially: each passage's extract_graph()
    # call is fully independent (no shared state, no ordering dependency
    # between passages), but this used to run one call, wait, next call —
    # live-timed at ~26s for 10 passages, ~44% of a real ingest's total
    # time (specs/v6.1/01). max_workers=8 is a plain default, not tuned
    # against a real Nebius rate limit — lower it if ingesting a large
    # document ever triggers 429s.
    entities_per_passage: list[list[dict] | None] = [None] * len(passages)
    relationships: list[dict] = []

    def _extract(i: int, text: str) -> tuple[int, list[dict], list[dict]]:
        try:
            graph = ingestion_pipeline.extract_graph(text)
            return i, graph["entities"], graph["relationships"]
        except Exception as exc:
            logging.warning("knowledge-graph extraction failed for a passage of %s: %s",
                            filename, exc)
            return i, [], []

    total_passages = len(passages)
    on_progress("extracting_graph", f"0 of {total_passages} passages")
    done_passages = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_extract, i, p["text"]) for i, p in enumerate(passages)]
        # as_completed(), not the plain futures list: iterating the futures
        # in submission order would block on future[0].result() until it's
        # done even if a later one finishes first, so the progress counter
        # would jump in lockstep with the slowest-so-far passage instead of
        # advancing as each one actually lands.
        for future in as_completed(futures):
            if not pre_write_check():
                for f in futures:
                    f.cancel()
                raise HTTPException(409, {
                    "message": "Cancelled — ingestion was stopped by user.",
                    "duplicate_of": None,
                })
            i, entities, rels = future.result()
            entities_per_passage[i] = entities
            relationships.extend(rels)
            done_passages += 1
            on_progress("extracting_graph", f"{done_passages} of {total_passages} passages")

    on_progress("writing")
    if not pre_write_check():
        raise HTTPException(409, {
            "message": "Cancelled — the staged item was discarded before ingestion finished.",
            "duplicate_of": None,
        })
    try:
        result = store.ingest_document(
            title=card["title"], filename=filename, kind=kind, origin=origin,
            grade=card["suggested_grade"], source_card_summary=card["summary"],
            topics=card["topics"], passages=passages,
            digest=digest, body=body, author=card["author"],
            published=card["published"], reference=card["reference"],
            page_count=page_count, entities_per_passage=entities_per_passage,
            relationships=relationships, original=original,
            folder_path="" if owner_practitioner_id else card["suggested_folder"],
            owner_practitioner_id=owner_practitioner_id,
            is_private=owner_practitioner_id is not None,
            doc_type=card.get("doc_type", ""), uploaded_by=uploaded_by,
        )
    except neo4j.exceptions.ConstraintError:
        # Another upload of the same body landed between our check and our write.
        raise HTTPException(409, {
            "message": "That source was ingested by another upload just now. "
                       "Nothing was added.",
            "duplicate_of": None,
        })

    if owner_practitioner_id:
        # The uploading practitioner grants themselves access to their own
        # document — the same core_store.set_document_access() an admin's
        # grant-editor dialog already calls for v6.9/01, just invoked
        # automatically instead of from a dialog (specs/v6.10/01).
        core_store.set_document_access(result["id"], [owner_practitioner_id], owner_practitioner_id)

    # Mirror into the pgvector store for the "general lookup" fast-RAG
    # path (app/retrieval/pgvector_store.py) — same chunk ids Neo4j just
    # used (f"{document_id}:{i}"), so a source deleted from one side via
    # the matching id is trivial to also remove from the other. Additive,
    # not load-bearing: the Neo4j write above already succeeded and is
    # the source of truth, so a failure here shouldn't fail the whole
    # ingest — logged, not raised.
    try:
        pgvector_store.save_chunk_embeddings(
            document_id=result["id"], document_title=result["title"],
            grade=result["grade"],
            chunks=[{"id": f"{result['id']}:{i}", **p} for i, p in enumerate(passages)],
        )
    except Exception:
        logging.exception("pgvector mirror failed for %s (Neo4j write already succeeded)",
                          result["id"])

    return result


def _ingest_pages(
    pages: list[tuple[int | None, str]], filename: str, kind: str, origin: str,
    replaces: str, original: tuple[bytes | Path, str, str] | None,
    uploaded_by: str = "",
) -> dict:
    """Full synchronous pipeline — duplicate check + the slow read/chunk/
    embed/extract/write chain, all inside one call. Shared by the
    direct-upload route below and the chunked-upload complete step
    (app/uploads.py), both of which still run atomically in one request
    (verify.py/verify_v2.py, the script callers of those routes, expect
    exactly that). The staged-promotion path does NOT use this — it calls
    _prep_and_check_duplicate() and _run_ingest() separately so the slow
    half can be backgrounded (see _promote_staged_async below)."""
    body, digest, page_count = _prep_and_check_duplicate(pages, filename, replaces)
    return _run_ingest(pages, body, digest, page_count, filename, kind, origin,
                        replaces, original, uploaded_by=uploaded_by)


@app.post("/api/sources")
async def add_source(
    kind: str = Form("article"),
    origin: str = Form("unspecified"),
    text: str = Form(""),
    replaces: str = Form(""),
    file: UploadFile | None = None,
    _admin: dict = Depends(auth.require_admin),
) -> dict:
    """Upload a source in one request, or paste one. For anything that
    might exceed _MAX_SOURCE_UPLOAD_BYTES, use the chunked routes below
    instead (POST /api/sources/upload/init, .../chunk, .../complete),
    which accept up to cfg.max_upload_bytes (200 MB) without buffering the
    whole file in memory."""
    original: tuple[bytes, str, str] | None = None
    if file is not None and file.filename:
        raw = await file.read()
        if len(raw) > _MAX_SOURCE_UPLOAD_BYTES:
            raise HTTPException(
                400,
                f"File must be under {_MAX_SOURCE_UPLOAD_BYTES // (1024 * 1024)} MB "
                "via direct upload — use the chunked upload for a larger file.")
        filename = file.filename
        try:
            pages = _extract_pages(filename, raw)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        # Keep the file itself as well as the passages: extraction drops tables,
        # figures and layout, and a clinician checking a citation needs the
        # document rather than our reading of it.
        original = (raw, filename,
                    file.content_type or _media_type(filename))
    else:
        filename = "pasted text"
        pages = [(None, text)]

    return _ingest_pages(pages, filename, kind, origin, replaces, original,
                          uploaded_by=_caller_identity(_admin))


class SourceUploadInit(BaseModel):
    filename: str
    total_size: int
    content_type: str = ""


@app.post("/api/sources/upload/init")
def source_upload_init(
    body: SourceUploadInit,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    return uploads.start(body.total_size, {
        "filename": body.filename, "content_type": body.content_type,
    })


@app.post("/api/sources/upload/{upload_id}/chunk")
async def source_upload_chunk(
    upload_id: str, chunk: UploadFile,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    return await uploads.append_chunk(upload_id, chunk)


class SourceUploadComplete(BaseModel):
    kind: str = "article"
    origin: str = "unspecified"
    replaces: str = ""


@app.post("/api/sources/upload/{upload_id}/complete")
def source_upload_complete(
    upload_id: str, body: SourceUploadComplete,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    path, meta = uploads.finish(upload_id)
    filename = meta["filename"]
    try:
        try:
            pages = _extract_pages_from_path(filename, path)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        original = (path, filename, meta["content_type"] or _media_type(filename))
        return _ingest_pages(pages, filename, body.kind, body.origin, body.replaces, original,
                              uploaded_by=_caller_identity(_caller))
    finally:
        # _ingest_pages() archives the file (originals.save_from_path, a
        # copy) before we get here, so the staging copy is always safe to
        # drop now — success or failure.
        uploads.cleanup(upload_id)


# --- Staged sources: upload/paste now, review, ingest all or one at a time ----
#
# specs/v3/18-document-ingest-upgrade.md's "staged uploads" — specced, never
# built until now. Everything above this point (add_source, the chunked
# upload/complete routes) still ingests in one atomic step, unchanged, for
# API/script callers (verify.py, verify_v2.py) that expect exactly that. The
# routes below are the new, separate path the admin UI actually uses now:
# stage first (no Reader call, no Neo4j write yet), let several items pile
# up, then promote a chosen subset — the "stack the resources... ingest all
# to the KB, or one at a time" flow.

def _caller_identity(caller: dict) -> str:
    """A human-readable "who did this" for Document.uploaded_by — the
    session cookie itself only carries role/id (app/auth.py's
    _set_session_cookie), not an email or name, so this is one extra
    lookup, not a free read off the caller dict."""
    if caller["role"] == "admin":
        admin = core_store.get_admin(caller["id"])
        return admin["email"] if admin else ""
    practitioner = core_store.get_practitioner(caller["id"])
    return practitioner["name"] if practitioner else ""


def _staged_owner_filter(caller: dict) -> str | None:
    """None (admin's own reach: everything) vs. the caller's own id (a
    permitted practitioner) — threaded through every staged_sources lookup
    below so a practitioner can never list, view, discard, or ingest another
    practitioner's (or admin's) staged item, only their own."""
    return None if caller["role"] == "admin" else caller["id"]


def _job_error_message(exc: Exception) -> str:
    """HTTPException.detail here is sometimes a plain string (the 502 in
    _run_ingest) and sometimes the {"message", "duplicate_of"} dict
    _prep_and_check_duplicate/store.ingest_document's ConstraintError branch
    raise — either way, ingestion_jobs.error_message should hold the same
    human-readable text a synchronous caller would have seen, not a repr of
    the exception object."""
    if isinstance(exc, HTTPException):
        detail = exc.detail
        return detail.get("message", str(detail)) if isinstance(detail, dict) else str(detail)
    return str(exc)


_cancelled_job_ids: set[str] = set()


def _is_job_cancelled(job_id: str, staged_id: str, owner: str | None) -> bool:
    if job_id in _cancelled_job_ids:
        return True
    if core_store.get_staged_source(staged_id, owner) is None:
        return True
    job = core_store.get_ingestion_job(job_id)
    if job and job.get("status") == "error":
        return True
    return False


def _run_staged_ingest_job(
    job_id: str, staged_id: str, owner: str | None, staged_kind: str,
    pages: list[tuple[int | None, str]], body: str, digest: str, page_count: int,
    filename: str, kind: str, origin: str, replaces: str,
    original: tuple[bytes | Path, str, str] | None,
    personal: bool = False,
    uploaded_by: str = "",
) -> None:
    """Runs in Starlette's threadpool after the response for
    POST /api/staged/{id}/ingest (or the batch route) has already been sent
    — this is the slow part of ingestion (Reader call onward) that used to
    run inside the request and blow past nginx's proxy_read_timeout on a
    large document. Every exception is caught here rather than left to
    vanish into Starlette's background-task logging: without this, a caller
    polling the job would see it stuck on "running" forever instead of a
    real error."""
    def progress(step: str, detail: str | None = None) -> None:
        core_store.update_ingestion_job(job_id, step=step, step_detail=detail)

    # The first thing a worker does on actually picking this job up
    # (app/ingestion/queue.py) — status moves from 'queued' (waiting for
    # a concurrency slot) to 'running', so a client polling can tell
    # "genuinely waiting" from "working on it" instead of both looking
    # identical.
    core_store.update_ingestion_job(job_id, status="running")

    # Cheap early exit if it's already gone or cancelled
    if _is_job_cancelled(job_id, staged_id, owner):
        core_store.update_ingestion_job(
            job_id, status="error", step="error",
            error_message="Cancelled — ingestion was stopped by user.")
        return

    try:
        result = _run_ingest(
            pages, body, digest, page_count, filename, kind, origin, replaces, original,
            on_progress=progress,
            pre_write_check=lambda: not _is_job_cancelled(job_id, staged_id, owner),
            owner_practitioner_id=owner if personal else None,
            uploaded_by=uploaded_by,
        )
        # _run_ingest() archives its own copy of the file under the *new*
        # source's id (originals.save_from_path) — the staged copy under the
        # staged id is redundant the moment that succeeds, dropped below.
        core_store.delete_staged_source(staged_id, owner)
        if staged_kind == "file":
            originals.delete(staged_id)
        core_store.update_ingestion_job(
            job_id, status="done", step="done", result_document_id=result["id"])
    except Exception as exc:
        logging.exception("staged ingest job %s (%s) failed", job_id, filename)
        core_store.update_ingestion_job(
            job_id, status="error", step="error", error_message=_job_error_message(exc))
    finally:
        _cancelled_job_ids.discard(job_id)


def _promote_staged_async(
    staged_id: str, kind: str, origin: str, owner: str | None,
    replaces: str, personal: bool = False, uploaded_by: str = "",
) -> dict:
    """Looks up the staged item and runs the same synchronous duplicate
    check _ingest_pages() always has, then hands the slow remainder to
    the ingestion queue (app/ingestion/queue.py — a concurrency-capped
    replacement for FastAPI's BackgroundTasks, found live 2026-11-03:
    unbounded concurrent ingests is a real OOM risk, see DEPLOY.md) and
    returns a job id immediately. The duplicate check stays synchronous
    and immediate — before any job row exists — so a practitioner
    clicking Ingest on an exact duplicate still gets an instant 409 with
    the replace-or-discard choice, not a job that "succeeds" into a
    redundant copy."""
    staged = core_store.get_staged_source(staged_id, owner)
    if staged is None:
        raise HTTPException(404, f"no such staged item: {staged_id}")

    # Found live, specs/v6.16: nothing stopped two ingestion jobs from
    # being created for the same staged item (a double-click on Retry,
    # or the page's auto-kick-on-load racing a manual click) — the
    # frontend's polling is keyed by staged_id, so the second job
    # silently stops tracking of the first, and if the first then wins
    # the write, its completion is never observed (the second's
    # ConstraintError 409 reports the whole thing as "failed" even
    # though the document was actually ingested). A duplicate attempt
    # reattaches to the already-running job instead of racing it. Not
    # fully race-proof (no DB-level unique constraint backs this — a
    # true check-then-create TOCTOU window remains between two
    # requests landing in the same instant), but closes the common
    # case: a double-click is two sequential requests, not two that
    # execute this check simultaneously.
    existing_job = core_store.get_active_job_for_staged(staged_id)
    if existing_job is not None:
        return {"job_id": existing_job["id"]}

    pages = core_store.get_staged_pages(staged_id)
    filename = staged["filename"] or staged.get("source_url") or "pasted text"
    original = None
    if staged["kind"] == "file" and staged["filename"]:
        path = originals.path(staged_id, staged["filename"])
        if path is not None:
            original = (path, staged["filename"],
                        staged["media_type"] or _media_type(staged["filename"]))

    body, digest, page_count = _prep_and_check_duplicate(pages, filename, replaces)

    job = core_store.create_ingestion_job(staged_id, owner, filename)
    ingestion_queue.enqueue(
        job["id"], _run_staged_ingest_job, job["id"], staged_id, owner, staged["kind"],
        pages, body, digest, page_count, filename, kind, origin, replaces, original,
        personal=personal, uploaded_by=uploaded_by,
    )
    return {"job_id": job["id"]}


@app.post("/api/staged")
async def stage_source(
    file: UploadFile | None = None,
    text: str = Form(""),
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    """Stage a small file or pasted text — no Reader call, no Neo4j write
    yet. For anything that might exceed _MAX_SOURCE_UPLOAD_BYTES, use the
    chunked routes (POST /api/sources/upload/init, .../chunk, then
    .../stage instead of .../complete)."""
    if file is not None and file.filename:
        raw = await file.read()
        if len(raw) > _MAX_SOURCE_UPLOAD_BYTES:
            raise HTTPException(
                400,
                f"File must be under {_MAX_SOURCE_UPLOAD_BYTES // (1024 * 1024)} MB "
                "via direct upload — use the chunked upload for a larger file.")
        filename = file.filename
        try:
            pages = _extract_pages(filename, raw)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        media_type = file.content_type or _media_type(filename)
        if not any(t.strip() for _, t in pages):
            raise HTTPException(
                400,
                "No text could be read from this source. If it is a scanned PDF, "
                "the pages are images and would need OCR before it can be staged.")
        staged = core_store.create_staged_source("file", filename, media_type, pages, _caller["id"])
        originals.save(staged["id"], raw, filename)
        return staged
    if text.strip():
        staged = core_store.create_staged_source("text", None, None, [(None, text)], _caller["id"])
        return staged
    raise HTTPException(400, "Provide a file or text.")


@app.post("/api/sources/upload/{upload_id}/stage")
def source_upload_stage(
    upload_id: str,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    """Chunked-upload counterpart to POST /api/staged's file branch — the
    complete step for a large file that should sit reviewable instead of
    ingesting immediately."""
    path, meta = uploads.finish(upload_id)
    filename = meta["filename"]
    try:
        try:
            pages = _extract_pages_from_path(filename, path)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not any(t.strip() for _, t in pages):
            raise HTTPException(
                400,
                "No text could be read from this source. If it is a scanned PDF, "
                "the pages are images and would need OCR before it can be staged.")
        media_type = meta["content_type"] or _media_type(filename)
        staged = core_store.create_staged_source("file", filename, media_type, pages, _caller["id"])
        originals.save_from_path(staged["id"], path, filename)
        return staged
    finally:
        uploads.cleanup(upload_id)


class ScrapeBody(BaseModel):
    url: str


@app.post("/api/scrape")
def scrape_url(body: ScrapeBody, _admin: dict = Depends(auth.require_admin)) -> dict:
    """Fetch a URL, strip it to text (app/scraper.py), then run a bounded
    LLM extraction pass (Haiku by default, cfg.reader_model) whose only
    job is discarding chrome — navigation, headers, footers, ads — never
    summarizing or rephrasing the content it keeps
    (specs/v3/18-document-ingest-upgrade.md Component 2). Lands in the
    staged list like any other staged item, not ingested immediately."""
    stripped = scraper.fetch_and_strip(body.url)
    try:
        extracted = ingestion_pipeline.extract_article(stripped, body.url)
    except openai.APIError as exc:
        raise HTTPException(
            502, "The AI service is temporarily unavailable. Try again shortly."
        ) from exc
    if not extracted.strip():
        raise HTTPException(400, "Nothing extractable was found on that page.")
    return core_store.create_staged_source(
        "scraped_url", None, "text/plain", [(None, extracted)], _admin["id"],
        source_url=body.url,
    )


@app.get("/api/staged")
def list_staged(
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> list[dict]:
    return core_store.list_staged_sources(_staged_owner_filter(_caller))


@app.get("/api/staged/{staged_id}/file")
def staged_file(
    staged_id: str,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> FileResponse:
    staged = core_store.get_staged_source(staged_id, _staged_owner_filter(_caller))
    if staged is None or staged["kind"] != "file" or not staged["filename"]:
        raise HTTPException(404, "no such staged file")
    path = originals.path(staged_id, staged["filename"])
    if path is None:
        raise HTTPException(404, "the file is no longer on disk")
    # Same inline-preview/nosniff reasoning as GET /api/sources/{id}/original.
    safe = "".join(c for c in Path(staged["filename"]).name if c.isprintable() and c != '"')
    media_type = staged["media_type"] or _media_type(staged["filename"])
    disposition = ("inline" if media_type in ("application/pdf", "text/plain")
                   else "attachment")
    return FileResponse(
        path, media_type=media_type,
        headers={"Content-Disposition": f'{disposition}; filename="{safe}"',
                 "X-Content-Type-Options": "nosniff"},
    )


@app.post("/api/staged/{staged_id}/stop")
def stop_staged_ingest(
    staged_id: str,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    owner = _staged_owner_filter(_caller)
    staged = core_store.get_staged_source(staged_id, owner)
    if staged is None:
        raise HTTPException(404, "no such staged item")
    cancelled = core_store.cancel_active_jobs_for_staged(staged_id, "Ingestion stopped by user.", owner)
    _cancelled_job_ids.update(cancelled)
    return {"stopped": staged_id, "cancelled_jobs": cancelled}


@app.delete("/api/staged/{staged_id}")
def discard_staged(
    staged_id: str,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    owner = _staged_owner_filter(_caller)
    staged = core_store.get_staged_source(staged_id, owner)
    if staged is None:
        raise HTTPException(404, "no such staged item")
    cancelled = core_store.cancel_active_jobs_for_staged(staged_id, "Cancelled — staged item removed.", owner)
    _cancelled_job_ids.update(cancelled)
    core_store.delete_staged_source(staged_id, owner)
    if staged["kind"] == "file":
        originals.delete(staged_id)
    return {"deleted": staged_id}


class StagedIngestBody(BaseModel):
    kind: str = "article"
    origin: str = "unspecified"
    replaces: str = ""


@app.post("/api/staged/{staged_id}/ingest", status_code=202)
def promote_staged(
    staged_id: str, body: StagedIngestBody,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    """202: the duplicate check (still a synchronous 409 on a real
    duplicate — see _promote_staged_async) passed, and the actual document
    doesn't exist yet at response time — the caller gets a job id and polls
    GET /api/ingestion-jobs/{job_id} for progress, not the ingested
    document itself."""
    return _promote_staged_async(staged_id, body.kind, body.origin,
                                  _staged_owner_filter(_caller), body.replaces,
                                  uploaded_by=_caller_identity(_caller))


class StagedBatchIngestBody(BaseModel):
    ids: list[str]
    kind: str = "article"
    origin: str = "unspecified"


@app.post("/api/staged/ingest")
def promote_staged_batch(
    body: StagedBatchIngestBody,
    _caller: dict = Depends(auth.require_admin_or_upload_permitted_practitioner),
) -> dict:
    """Each id either 409s immediately as a duplicate (reported in
    `duplicates`, resolvable individually via the single-item route) or
    gets its own background job (reported in `jobs`) — replaces the old
    `{"ingested": [...], "failed": [...]}` shape, since nothing here
    finishes ingesting before the response goes out any more."""
    owner = _staged_owner_filter(_caller)
    uploaded_by = _caller_identity(_caller)
    jobs, duplicates, failed = [], [], []
    # Two identical staged items selected in the same batch both pass
    # _prep_and_check_duplicate's store.find_by_hash check, since neither
    # is written to the store until its (backgrounded) job actually runs —
    # the second one would otherwise only fail later as a generic
    # neo4j ConstraintError, minutes after the response went out, with no
    # duplicate_of for the frontend to offer a replace choice (found in
    # review). Tracked here, not inside _prep_and_check_duplicate itself,
    # since that function has no notion of "the rest of this batch."
    seen_digests: set[str] = set()
    for staged_id in body.ids:
        try:
            staged = core_store.get_staged_source(staged_id, owner)
            if staged is None:
                raise HTTPException(404, f"no such staged item: {staged_id}")
            pages = core_store.get_staged_pages(staged_id)
            digest = store.content_hash(
                "\n\n".join(t.strip() for _, t in pages if t.strip()).strip())
            if digest in seen_digests:
                duplicates.append({"staged_id": staged_id, "error": {
                    "message": "Identical to another item already in this batch.",
                    "duplicate_of": None,
                }})
                continue
            seen_digests.add(digest)
            enqueued = _promote_staged_async(staged_id, body.kind, body.origin, owner, "",
                                              uploaded_by=uploaded_by)
            jobs.append({"staged_id": staged_id, "job_id": enqueued["job_id"]})
        except HTTPException as exc:
            if exc.status_code == 409:
                duplicates.append({"staged_id": staged_id, "error": exc.detail})
            else:
                failed.append({"staged_id": staged_id, "error": exc.detail})
    return {"jobs": jobs, "duplicates": duplicates, "failed": failed}


# --- Practitioner's own private knowledge base (specs/v6.10/01) --------------
#
# A separate, parallel surface from the staging/promotion routes above —
# not a flag on them — so `can_upload_library`'s existing meaning (who
# can contribute to the *shared* library) doesn't quietly change.
# `core_store`'s staged_sources table is reused as-is (same schema, same
# `owner` column); only the promotion step differs, via `personal=True`
# threaded into `_promote_staged_async`. No file-preview-before-ingest
# route here (unlike the shared flow's GET /api/staged/{id}/file) — a
# deliberate v1 simplification, not an oversight: the resulting document
# is viewable afterward through the existing source-detail page either
# way, so previewing the raw staged file first isn't load-bearing yet.

@app.post("/api/me/knowledge/stage")
async def stage_own_source(
    file: UploadFile | None = None,
    text: str = Form(""),
    session: dict = Depends(auth.require_pro_practitioner),
) -> dict:
    """Any Pro practitioner, not just one with can_upload_library — a
    personal document can't affect anyone else's consults, so it doesn't
    need that admin-granted permission (specs/v6.10/01)."""
    if file is not None and file.filename:
        raw = await file.read()
        if len(raw) > _MAX_SOURCE_UPLOAD_BYTES:
            raise HTTPException(
                400,
                f"File must be under {_MAX_SOURCE_UPLOAD_BYTES // (1024 * 1024)} MB.")
        filename = file.filename
        try:
            pages = _extract_pages(filename, raw)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        media_type = file.content_type or _media_type(filename)
        if not any(t.strip() for _, t in pages):
            raise HTTPException(
                400,
                "No text could be read from this source. If it is a scanned PDF, "
                "the pages are images and would need OCR before it can be staged.")
        staged = core_store.create_staged_source("file", filename, media_type, pages, session["id"])
        originals.save(staged["id"], raw, filename)
        return staged
    if text.strip():
        return core_store.create_staged_source("text", None, None, [(None, text)], session["id"])
    raise HTTPException(400, "Provide a file or text.")


@app.get("/api/me/knowledge/stage")
def list_own_staged(session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    return core_store.list_staged_sources(session["id"])


@app.post("/api/me/knowledge/stage/{staged_id}/stop")
def stop_own_staged_ingest(
    staged_id: str,
    session: dict = Depends(auth.require_pro_practitioner),
) -> dict:
    staged = core_store.get_staged_source(staged_id, session["id"])
    if staged is None:
        raise HTTPException(404, "no such staged item")
    cancelled = core_store.cancel_active_jobs_for_staged(staged_id, "Ingestion stopped by user.", session["id"])
    _cancelled_job_ids.update(cancelled)
    return {"stopped": staged_id, "cancelled_jobs": cancelled}


@app.delete("/api/me/knowledge/stage/{staged_id}")
def discard_own_staged(staged_id: str, session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    staged = core_store.get_staged_source(staged_id, session["id"])
    if staged is None:
        raise HTTPException(404, "no such staged item")
    cancelled = core_store.cancel_active_jobs_for_staged(staged_id, "Cancelled — staged item removed.", session["id"])
    _cancelled_job_ids.update(cancelled)
    core_store.delete_staged_source(staged_id, session["id"])
    if staged["kind"] == "file":
        originals.delete(staged_id)
    return {"deleted": staged_id}


@app.post("/api/me/knowledge/stage/{staged_id}/ingest", status_code=202)
def promote_own_staged(
    staged_id: str, body: StagedIngestBody,
    session: dict = Depends(auth.require_pro_practitioner),
) -> dict:
    # `replaces` (a duplicate-of id the practitioner is choosing to
    # supersede) must already be their own document — without this, a
    # practitioner could name any document id here and have
    # _run_ingest's store.delete_document(replaces) remove someone
    # else's source out from under them. This check is new with this
    # route; the existing shared-library promotion route below has the
    # same `replaces` shape with no equivalent check, a pre-existing gap
    # out of scope for this spec (specs/v6.10/01) to fix.
    if body.replaces:
        existing = store.get_document(body.replaces)
        if existing is None or existing.get("owner_practitioner_id") != session["id"]:
            raise HTTPException(404, "no such source")
    return _promote_staged_async(staged_id, body.kind, body.origin, session["id"],
                                 body.replaces, personal=True,
                                 uploaded_by=_caller_identity(session))


@app.delete("/api/me/knowledge/{source_id}")
def delete_own_source(source_id: str, session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    """Unlike DELETE /api/sources/{id} (admin-only, a shared-library
    curation decision), a practitioner can delete their own personal
    document themselves — 404, not 403, on anything that isn't theirs,
    so this can't be used to confirm another document's existence."""
    source = store.get_document(source_id)
    if source is None or source.get("owner_practitioner_id") != session["id"]:
        raise HTTPException(404, "no such source")
    store.delete_document(source_id)
    pgvector_store.delete_document(source_id)
    return {"deleted": source_id}


@app.get("/api/ingestion-jobs/active")
def list_active_ingestion_jobs(
    _caller: dict = Depends(auth.require_admin_or_pro_practitioner),
) -> list[dict]:
    """Lets the frontend reattach to an in-progress job after a page reload
    without needing to remember a job id anywhere client-side — admin sees
    every active job, a practitioner sees only their own.

    require_admin_or_pro_practitioner, not require_admin_or_upload_
    permitted_practitioner — found live, specs/v6.10/01: a Pro
    practitioner using only the new personal-knowledge-base routes
    (no can_upload_library grant) got "Library upload permission
    required" trying to poll their own job's status, since this read-
    only, ownership-scoped check (_staged_owner_filter below) doesn't
    need that permission at all, only the staging/promotion routes do."""
    return core_store.list_active_ingestion_jobs(_staged_owner_filter(_caller))


@app.get("/api/ingestion-jobs/stats")
def ingestion_queue_stats(
    _caller: dict = Depends(auth.require_admin_or_pro_practitioner),
) -> dict:
    """The Library page's status bar (specs/v6.12) — queued/processing
    counts, characters still waiting, and a rough ETA from the last few
    completed jobs' real durations. Same owner scoping as the /active
    route above, for the same reason."""
    return core_store.ingestion_queue_stats(_staged_owner_filter(_caller))


@app.get("/api/ingestion-jobs/{job_id}")
def get_ingestion_job(
    job_id: str,
    _caller: dict = Depends(auth.require_admin_or_pro_practitioner),
) -> dict:
    # 404, not 403, for a job that isn't the caller's own — same
    # don't-confirm-existence pattern as _own_questionnaire_or_404.
    owner = _staged_owner_filter(_caller)
    job = core_store.get_ingestion_job(job_id)
    if job is None or (owner is not None and job["owner"] != owner):
        raise HTTPException(404, "no such ingestion job")
    return job


@app.get("/api/sources")
def get_sources(
    search: str = "", topic: str = "", kind: str = "",
    min_grade: int = 1, max_grade: int = 10,
    sort: str = "newest", page: int = 1, per_page: int = 10,
    _admin: dict = Depends(auth.require_admin),
) -> dict:
    return store.list_documents(
        search=search, topic=topic, kind=kind, min_grade=min_grade,
        max_grade=max_grade, sort=sort, page=page, per_page=per_page)


class SourceFilter(BaseModel):
    search: str = ""
    topic: str = ""
    kind: str = ""
    min_grade: int = 1
    max_grade: int = 10
    sort: str = "newest"
    page: int = 1
    per_page: int = 10


@app.api_route("/api/sources", methods=["QUERY"])
def get_sources_query(
    body: SourceFilter, _admin: dict = Depends(auth.require_admin),
) -> dict:
    """Same as GET /api/sources (specs/v3/08-api.md#http-query-method)."""
    return get_sources(body.search, body.topic, body.kind, body.min_grade,
                       body.max_grade, body.sort, body.page, body.per_page, _admin)


_SNIPPET_WINDOW_BEFORE = 60
_SNIPPET_WINDOW_AFTER = 220


def _build_snippet(text: str, query: str) -> str:
    """Centers the snippet on the first matched query word instead of
    always taking a chunk's first ~280 characters (which, for a vector-
    only semantic hit, may not contain any of the query's actual words
    at all, or for a full-text hit may cut off before the match even
    appears) — and wraps every occurrence of a query word in <mark> so
    the FE can bold it without needing to re-implement the matching
    itself. Falls back to a plain leading excerpt when no query word is
    found verbatim (the common case for a semantic-only match). The FE
    renders this as HTML (for the <mark> tags), so the excerpt is
    HTML-escaped *before* the tags are inserted — the document's own
    text is untrusted input (whatever an admin uploaded/pasted/scraped),
    and the <mark> wrapping here is the only markup that should survive.
    """
    text = text or ""
    words = [w for w in re.split(r"\s+", query.strip()) if len(w) >= 2]
    if not words:
        return html.escape(text[:280])

    pattern = re.compile(
        "|".join(re.escape(w) for w in words), re.IGNORECASE)
    first = pattern.search(text)
    if first is None:
        return html.escape(text[:280])

    start = max(0, first.start() - _SNIPPET_WINDOW_BEFORE)
    end = min(len(text), first.start() + _SNIPPET_WINDOW_AFTER)
    excerpt = html.escape(text[start:end])
    escaped_pattern = re.compile(
        "|".join(re.escape(html.escape(w)) for w in words), re.IGNORECASE)
    excerpt = escaped_pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", excerpt)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{excerpt}{suffix}"


@app.get("/api/sources/search-content")
def search_source_content(
    q: str, top_k: int = 20, _admin: dict = Depends(auth.require_admin),
) -> dict:
    """Real search inside document text, ranked by relevance — GET
    /api/sources?search= only does a plain Neo4j CONTAINS match against
    doc.body. This instead searches the same chunk_embedding vector index
    and chunk_text_fulltext index Consult's own retrieval already builds
    at ingest time (app/graph/store.py's seed_chunks_by_vector/
    _by_fulltext), so a query finds a document even when the matching
    words never appear verbatim, or ranks a genuinely relevant passage
    above an incidental keyword hit.

    Vector-similarity and Lucene full-text scores are on different,
    non-comparable scales, so results aren't merged by raw score —
    semantic matches are returned in their own ranked order first, with
    any additional full-text-only matches (an exact phrase the embedding
    model didn't rank highly) appended after, each document appearing
    once (its best-scoring matched chunk).
    """
    q = q.strip()
    if not q:
        return {"matches": []}
    embedding = get_llm_client(LLMRole.EMBEDDER).embed([q])[0]
    vector_hits = store.seed_chunks_by_vector(embedding, top_k)
    fulltext_hits = store.seed_chunks_by_fulltext(q, top_k)

    best_chunk_per_doc: dict[str, dict] = {}
    ordered_doc_ids: list[str] = []
    for hit in vector_hits + fulltext_hits:
        doc_id = hit["document_id"]
        if doc_id not in best_chunk_per_doc:
            best_chunk_per_doc[doc_id] = hit
            ordered_doc_ids.append(doc_id)

    return {"matches": [
        {
            "document_id": doc_id,
            "title": best_chunk_per_doc[doc_id]["document_title"],
            "snippet": _build_snippet(best_chunk_per_doc[doc_id]["text"], q),
            "is_private": best_chunk_per_doc[doc_id]["is_private"],
        }
        for doc_id in ordered_doc_ids[:top_k]
    ]}


@app.get("/api/facets")
def get_facets(_admin: dict = Depends(auth.require_admin)) -> dict:
    return store.facets()


@app.get("/api/graph")
def get_graph(_admin: dict = Depends(auth.require_admin)) -> dict:
    """Shape of the knowledge graph, plus anything not yet linked into it."""
    return {**store.graph_stats(), "unlinked": store.unlinked_documents()}


@app.get("/api/graph/concepts")
def get_concept_graph(_admin: dict = Depends(auth.require_admin)) -> dict:
    """The Library page's Graph view, concept layer (specs/v6.13) — a
    bounded node-link view of the actual knowledge graph (typed
    Entity->Entity relationships), not the document/folder tree the
    same tab's other layer already shows client-side."""
    return store.concept_graph()


_current_maintenance: dict | None = None
_maintenance_lock = threading.Lock()
_maintenance_stop_requested = False


def _update_maintenance(
    kind: str,
    status: str,
    current: float,
    total: float,
    step: str,
    detail: str,
    percentage: int | None = None,
    result: dict | None = None,
    error: str | None = None,
):
    global _current_maintenance
    if percentage is None:
        percentage = int((current / max(1.0, total)) * 100) if total > 0 else 0
    percentage = max(0, min(100, percentage))
    _current_maintenance = {
        "active": status == "running",
        "kind": kind,
        "status": status,
        "current": current,
        "total": total,
        "percentage": percentage,
        "step": step,
        "detail": detail,
        "result": result,
        "error": error,
        "updated_at": time.time(),
    }


def _stream_relink():
    global _maintenance_stop_requested, _current_maintenance
    _maintenance_stop_requested = False

    docs = store.unlinked_documents()
    total_docs = len(docs)

    init_msg = f"Found {total_docs} unlinked document(s)..." if total_docs > 0 else "No unlinked documents found."
    _update_maintenance("relink", "running", 0, max(1, total_docs), "start", init_msg, percentage=0)
    yield {"event": "start", "kind": "relink", "percentage": 0, "current": 0, "total": max(1, total_docs), "detail": init_msg}

    if total_docs == 0:
        res = {"linked": [], "failed": [], **store.graph_stats()}
        _update_maintenance("relink", "done", 1, 1, "done", "No unlinked documents found.", percentage=100, result=res)
        yield {"event": "done", "kind": "relink", "percentage": 100, "current": 1, "total": 1, "detail": "No unlinked documents found.", "result": res}
        return

    done, failed = [], []
    for i, doc in enumerate(docs, 1):
        if _maintenance_stop_requested:
            logging.info("relink stopped by admin request")
            break

        full = store.document_text(doc["id"])
        if not full or not full.get("passages"):
            failed.append(doc["title"])
            pct = int(((i - 1) / total_docs) * 100)
            _update_maintenance("relink", "running", i, total_docs, "skipped", f"Skipped '{doc['title']}' (no passages)", percentage=pct)
            yield {"event": "progress", "kind": "relink", "percentage": pct, "current": i, "total": total_docs, "detail": f"Skipped '{doc['title']}' (no passages)"}
            continue

        try:
            passages = full["passages"]
            num_passages = len(passages)
            entities_per_passage: list[list[dict] | None] = [None] * num_passages
            relationships: list[dict] = []

            def _extract(idx: int, text: str):
                try:
                    graph = ingestion_pipeline.extract_graph(text)
                    return idx, graph.get("entities", []), graph.get("relationships", [])
                except Exception as exc:
                    logging.warning("extraction failed for passage of %s: %s", doc["title"], exc)
                    return idx, [], []

            done_passages = 0
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [pool.submit(_extract, p_idx, p["text"]) for p_idx, p in enumerate(passages)]
                for future in as_completed(futures):
                    if _maintenance_stop_requested:
                        break
                    p_idx, ents, rels = future.result()
                    entities_per_passage[p_idx] = ents
                    relationships.extend(rels)
                    done_passages += 1
                    cur_prog = (i - 1) + (done_passages / max(1, num_passages))
                    pct = int((cur_prog / total_docs) * 100)
                    detail = f"Doc {i}/{total_docs}: '{doc['title']}' ({done_passages}/{num_passages} passages)"
                    _update_maintenance("relink", "running", cur_prog, total_docs, "extracting", detail, percentage=pct)
                    yield {"event": "progress", "kind": "relink", "percentage": pct, "current": cur_prog, "total": total_docs, "detail": detail}

            if _maintenance_stop_requested:
                break

            clean_entities = [e or [] for e in entities_per_passage]
            edges = store.link_document(doc["id"], clean_entities, relationships)
            store.log("admin", "linked", f"{doc['title']} — {edges} graph edges")
            done.append({"title": doc["title"], "edges": edges})

            pct = int((i / total_docs) * 100)
            detail = f"Linked '{doc['title']}' ({edges} edges)"
            _update_maintenance("relink", "running", i, total_docs, "linked", detail, percentage=pct)
            yield {"event": "progress", "kind": "relink", "percentage": pct, "current": i, "total": total_docs, "detail": detail}
        except Exception as exc:
            logging.warning("relink failed for %s: %s", doc["title"], exc)
            failed.append(doc["title"])
            pct = int((i / total_docs) * 100)
            detail = f"Failed '{doc['title']}': {exc}"
            _update_maintenance("relink", "running", i, total_docs, "failed", detail, percentage=pct)
            yield {"event": "progress", "kind": "relink", "percentage": pct, "current": i, "total": total_docs, "detail": detail}

    res = {"linked": done, "failed": failed, **store.graph_stats()}
    summary = f"Finished! Linked {len(done)} source(s), {len(failed)} failed."
    _update_maintenance("relink", "done", total_docs, total_docs, "done", summary, percentage=100, result=res)
    yield {"event": "done", "kind": "relink", "percentage": 100, "current": total_docs, "total": total_docs, "detail": summary, "result": res}


def _run_relink() -> dict:
    res = {}
    for ev in _stream_relink():
        if ev.get("event") == "done":
            res = ev.get("result", {})
    return res


def _stream_consolidate():
    global _maintenance_stop_requested, _current_maintenance
    _maintenance_stop_requested = False

    _update_maintenance("consolidate", "running", 0, 4, "start", "Starting entity consolidation...", percentage=5)
    yield {"event": "start", "kind": "consolidate", "percentage": 5, "current": 0, "total": 4, "detail": "Starting entity consolidation..."}

    names = [e["name"] for e in store.all_entities()]
    _update_maintenance("consolidate", "running", 1, 4, "scanning", f"Found {len(names)} entities in graph", percentage=25)
    yield {"event": "progress", "kind": "consolidate", "percentage": 25, "current": 1, "total": 4, "detail": f"Scanning {len(names)} entities in knowledge graph..."}

    if len(names) < 2:
        res = {"entity": {"groups": [], "absorbed": 0, "before": len(names)}, **store.graph_stats()}
        msg = f"Only {len(names)} entity in graph — nothing to consolidate."
        _update_maintenance("consolidate", "done", 4, 4, "done", msg, percentage=100, result=res)
        yield {"event": "done", "kind": "consolidate", "percentage": 100, "current": 4, "total": 4, "detail": msg, "result": res}
        return

    if _maintenance_stop_requested:
        return

    _update_maintenance("consolidate", "running", 2, 4, "analyzing", f"Analyzing {len(names)} entities with AI...", percentage=50)
    yield {"event": "progress", "kind": "consolidate", "percentage": 50, "current": 2, "total": 4, "detail": f"Analyzing {len(names)} entities with AI for potential merges..."}

    groups = ingestion_pipeline.suggest_entity_merges(names)

    if _maintenance_stop_requested:
        return

    _update_maintenance("consolidate", "running", 3, 4, "merging", f"Applying {len(groups)} merge group(s)...", percentage=75)
    yield {"event": "progress", "kind": "consolidate", "percentage": 75, "current": 3, "total": 4, "detail": f"Applying {len(groups)} merge group(s) in Neo4j graph..."}

    absorbed = store.merge_entities(groups) if groups else 0
    if groups:
        store.log("admin", "consolidated", "entities: " + "; ".join(
            f"{g['canonical']} ← {', '.join(g['aliases'])}" for g in groups)[:400])

    res = {"entity": {"groups": groups, "absorbed": absorbed, "before": len(names)}, **store.graph_stats()}
    summary = f"Finished! Merged {absorbed} duplicate entities."
    _update_maintenance("consolidate", "done", 4, 4, "done", summary, percentage=100, result=res)
    yield {"event": "done", "kind": "consolidate", "percentage": 100, "current": 4, "total": 4, "detail": summary, "result": res}


def _run_consolidate() -> dict:
    res = {}
    for ev in _stream_consolidate():
        if ev.get("event") == "done":
            res = ev.get("result", {})
    return res


@app.get("/api/maintenance/status")
def maintenance_status(_admin: dict = Depends(auth.require_admin)) -> dict:
    """Returns the current state of any active maintenance job (relink or consolidate)."""
    global _current_maintenance
    if not _current_maintenance:
        return {"active": False, "kind": None}
    return dict(_current_maintenance)


@app.post("/api/maintenance/stop")
def stop_maintenance(_admin: dict = Depends(auth.require_admin)) -> dict:
    """Requests cancellation of any running maintenance task."""
    global _maintenance_stop_requested, _current_maintenance
    _maintenance_stop_requested = True
    if _current_maintenance:
        _current_maintenance["active"] = False
        _current_maintenance["status"] = "cancelled"
        _current_maintenance["detail"] = "Maintenance stopped by admin."
    return {"status": "stopping"}


@app.post("/api/relink")
def relink(
    request: Request,
    stream: bool = False,
    _admin: dict = Depends(auth.require_admin),
):
    """Build the knowledge graph for documents that have none.
    Supports live SSE progress streaming via stream=true or Accept: text/event-stream.
    """
    global _current_maintenance
    if _current_maintenance and _current_maintenance.get("active"):
        raise HTTPException(409, "A maintenance task is already running.")

    wants_stream = stream or ("text/event-stream" in request.headers.get("accept", ""))

    if not wants_stream:
        return _run_relink()

    def sse():
        try:
            for ev in _stream_relink():
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception as exc:
            err_msg = str(exc)
            _update_maintenance("relink", "error", 0, 1, "error", err_msg, error=err_msg)
            yield f"data: {json.dumps({'event': 'error', 'kind': 'relink', 'message': err_msg})}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@app.post("/api/consolidate")
def consolidate(
    request: Request,
    stream: bool = False,
    _admin: dict = Depends(auth.require_admin),
):
    """Let the model tidy the entity index, then rewrite the graph to match.
    Supports live SSE progress streaming via stream=true or Accept: text/event-stream.
    """
    global _current_maintenance
    if _current_maintenance and _current_maintenance.get("active"):
        raise HTTPException(409, "A maintenance task is already running.")

    wants_stream = stream or ("text/event-stream" in request.headers.get("accept", ""))

    if not wants_stream:
        return _run_consolidate()

    def sse():
        try:
            for ev in _stream_consolidate():
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception as exc:
            err_msg = str(exc)
            _update_maintenance("consolidate", "error", 0, 1, "error", err_msg, error=err_msg)
            yield f"data: {json.dumps({'event': 'error', 'kind': 'consolidate', 'message': err_msg})}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@app.get("/api/sources/{source_id}/related")
def source_related(source_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    if store.get_document(source_id) is None:
        raise HTTPException(404, "no such source")
    return {"concepts": store.entities_for(source_id),
            "neighbours": store.neighbours_of(source_id)}


@app.get("/api/sources/{source_id}")
def get_source(source_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    source = store.get_document(source_id)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


def _check_private_access(source_id: str, caller: dict) -> None:
    """A private document (specs/v6.9/01) is new exposure for a
    practitioner with no grant for it — unlike every other source,
    it's deliberately absent from their consult results and their own
    GET /api/me/knowledge listing (app/main.py's me_knowledge()), so
    letting them hit its viewer directly by id would undo that. An
    admin isn't checked — they manage the grant list itself."""
    if caller["role"] != "practitioner":
        return
    document = store.get_document(source_id)
    if document and document.get("is_private") \
            and source_id not in core_store.get_accessible_document_ids(caller["id"]):
        raise HTTPException(404, "no such source")


@app.get("/api/sources/{source_id}/text")
def read_source(source_id: str, _caller: dict = Depends(auth.require_admin_or_pro_practitioner)) -> dict:
    """The source as ingested, so the original stays readable in the library."""
    _check_private_access(source_id, _caller)
    source = store.document_text(source_id)
    if source is None:
        raise HTTPException(404, "no such source")
    for p in source["passages"]:
        p["locator"] = _locator({**p, "passage_count": len(source["passages"])})
    return source


@app.get("/api/sources/{source_id}/original")
def download_source(source_id: str, _caller: dict = Depends(auth.require_admin_or_pro_practitioner)) -> FileResponse:
    _check_private_access(source_id, _caller)
    """The uploaded file itself — what the passages were extracted *from*.

    404 when no original was kept: pasted text, a source ingested before the file
    store existed, or an archive write that failed. The UI checks `original_name`
    on the source card rather than probing this.
    """
    source = store.get_document(source_id)
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
    source = store.set_grade(source_id, body.grade)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


@app.delete("/api/sources/{source_id}")
def remove_source(source_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    store.delete_document(source_id)
    pgvector_store.delete_document(source_id)
    return {"deleted": source_id}


class FolderUpdate(BaseModel):
    folder_path: str


@app.patch("/api/sources/{source_id}/folder")
def move_source(source_id: str, body: FolderUpdate,
                _admin: dict = Depends(auth.require_admin)) -> dict:
    """An admin's placement is always final (specs/v6.8/01) — this is
    what overrides whatever the Reader suggested at ingest time, same
    relationship PATCH /api/sources/{id} already has to suggested_grade."""
    source = store.set_folder(source_id, body.folder_path)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


class TopicsUpdate(BaseModel):
    topics: list[str]


@app.patch("/api/sources/{source_id}/topics")
def set_source_topics(source_id: str, body: TopicsUpdate,
                      _admin: dict = Depends(auth.require_admin)) -> dict:
    """Tags are editable and assignable by an admin — the Reader's
    topics at ingest time are only a suggested starting point, same
    relationship it already has to suggested_folder/suggested_grade."""
    source = store.set_topics(source_id, body.topics)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


class DocTypeUpdate(BaseModel):
    doc_type: str


@app.get("/api/doc-types")
def list_doc_types() -> dict:
    return {"doc_types": store.DOC_TYPES}


@app.patch("/api/sources/{source_id}/doc-type")
def set_source_doc_type(source_id: str, body: DocTypeUpdate,
                        _admin: dict = Depends(auth.require_admin)) -> dict:
    """Content-type classification (article/book/presentation/protocol/
    etc.) is editable by an admin — the Reader's doc_type at ingest time
    is only a suggested starting point, same relationship it already has
    to suggested_folder/suggested_grade/topics."""
    try:
        source = store.set_doc_type(source_id, body.doc_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if source is None:
        raise HTTPException(404, "no such source")
    return source


class UploadedByUpdate(BaseModel):
    uploaded_by: str


@app.patch("/api/sources/{source_id}/uploaded-by")
def set_source_uploaded_by(source_id: str, body: UploadedByUpdate,
                           _admin: dict = Depends(auth.require_admin)) -> dict:
    """Claim or assign who uploaded a document — specifically for
    documents ingested before v6.11 (uploaded_by is already captured
    automatically for anything ingested since)."""
    source = store.set_uploaded_by(source_id, body.uploaded_by)
    if source is None:
        raise HTTPException(404, "no such source")
    return source


class FolderCreate(BaseModel):
    folder_path: str


@app.post("/api/library/folders")
def create_library_folder(body: FolderCreate,
                          _admin: dict = Depends(auth.require_admin)) -> dict:
    """An empty folder, created ahead of any document landing in it —
    closes specs/v6.8/01's known limitation ("no persistent empty
    folder without a first-class Folder entity") with exactly that."""
    try:
        return store.create_folder(body.folder_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


class FolderDelete(BaseModel):
    folder_path: str


@app.post("/api/library/folders/delete")
def delete_library_folder(body: FolderDelete,
                          _admin: dict = Depends(auth.require_admin)) -> dict:
    """Deletes the folder and every document in it or a subfolder of it
    — the "drag a folder to the trash" expectation a real file browser
    has, not a bare `rmdir` that only works when empty."""
    try:
        deleted_ids = store.delete_folder(body.folder_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    for document_id in deleted_ids:
        pgvector_store.delete_document(document_id)
    return {"deleted_documents": len(deleted_ids)}


class FolderRename(BaseModel):
    old_path: str
    new_path: str


@app.post("/api/library/folders/rename")
def rename_library_folder(body: FolderRename,
                          _admin: dict = Depends(auth.require_admin)) -> dict:
    """Renames (or moves) a folder and everything under it in one go —
    a folder is just a shared path prefix (specs/v6.8/01), not a
    separate node to look up by id."""
    try:
        moved = store.rename_folder(body.old_path, body.new_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"moved": moved}


class PrivacyUpdate(BaseModel):
    is_private: bool


@app.patch("/api/sources/{source_id}/privacy")
def set_source_privacy(source_id: str, body: PrivacyUpdate,
                       admin: dict = Depends(auth.require_admin)) -> dict:
    """Specs/v6.9/01 — who specifically can still see it despite this is
    a separate action (PUT .../access below), not bundled into this one."""
    source = store.set_private(source_id, body.is_private)
    if source is None:
        raise HTTPException(404, "no such source")
    pgvector_store.set_private([source_id], body.is_private)
    return source


class FolderPrivacyUpdate(BaseModel):
    folder_path: str
    is_private: bool


@app.post("/api/library/folders/privacy")
def set_folder_privacy(body: FolderPrivacyUpdate,
                       admin: dict = Depends(auth.require_admin)) -> dict:
    """Bulk-privatize (or un-privatize) everything currently in a folder
    — a one-time action over what's there now, not a persisted
    folder-level policy (specs/v6.9/01's explicit tradeoff, same one
    v6.8/01's folder model already accepts for renaming)."""
    ids = store.set_folder_private(body.folder_path, body.is_private)
    pgvector_store.set_private(ids, body.is_private)
    return {"updated": len(ids)}


@app.get("/api/sources/{source_id}/access")
def get_source_access(source_id: str, _admin: dict = Depends(auth.require_admin)) -> list[str]:
    return core_store.get_document_access(source_id)


class AccessUpdate(BaseModel):
    practitioner_ids: list[str]


@app.put("/api/sources/{source_id}/access")
def set_source_access(source_id: str, body: AccessUpdate,
                      admin: dict = Depends(auth.require_admin)) -> dict:
    """Replaces the full grant list for this document in one call —
    reachable again later from a private document's own row, not frozen
    at the moment it was privatized (specs/v6.9/01)."""
    core_store.set_document_access(source_id, body.practitioner_ids, admin["id"])
    return {"practitioner_ids": core_store.get_document_access(source_id)}


@app.get("/api/coverage")
def get_coverage(_admin: dict = Depends(auth.require_admin)) -> list[dict]:
    return store.coverage()


@app.get("/api/audit")
def get_audit(_admin: dict = Depends(auth.require_admin)) -> list[dict]:
    """The library's own paper trail — admin-only.

    Each Pro practitioner's vault carries its own separate audit trail
    (GET /api/me/clients/{id} exposes it per-client); this endpoint is the
    library's, and only the library's, per the same never-mix-the-two-stores
    rule v1 drew (specs/v1/07-security.md#the-leak-that-was-found).
    """
    return store.audit()[:100]


def _public(d: dict) -> dict:
    """Strip fields that must never cross the API boundary. core_store/vault
    getters return password_hash (and, for practitioners,
    anthropic_api_key_encrypted — vestigial since specs/v4.2 retired the
    BYO-key model; the column stays in the schema but is never written or
    read for LLM calls any more) because auth.py needs password_hash
    internally for credential checks — every route that hands one of
    those dicts to a caller must pass it through this first."""
    return {k: v for k, v in d.items()
            if k not in ("password_hash", "anthropic_api_key_encrypted")}


def _public_list(items: list[dict]) -> list[dict]:
    return [_public(d) for d in items]


_MAX_PHOTO_BYTES = 5 * 1024 * 1024


def _sniff_image_ext(raw: bytes) -> str | None:
    """Real file-format sniffing (magic bytes), not the client-supplied
    filename's extension or content-type — practitioner_signup is
    unauthenticated, so an .svg or .html "photo" saved under a trusted
    extension and served back inline from the /photos static mount was a
    stored-XSS vector (specs/v4/04-known-issues.md#c7)."""
    if raw.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"):
        return ".gif"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return ".webp"
    return None


def _save_photo(practitioner_id: str, file: UploadFile, raw: bytes) -> str:
    if len(raw) > _MAX_PHOTO_BYTES:
        raise HTTPException(400, "Photo must be under 5 MB.")
    ext = _sniff_image_ext(raw)
    if ext is None:
        raise HTTPException(400, "Photo must be a JPEG, PNG, GIF, or WebP image.")
    dest = Path(cfg.photos_path) / f"{practitioner_id}{ext}"
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
    return _public_list(approved)


class PractitionerFilter(BaseModel):
    specialty: str = ""
    language: str = ""


@app.api_route("/api/practitioners", methods=["QUERY"])
def list_practitioners_public_query(body: PractitionerFilter) -> list[dict]:
    """Same as GET /api/practitioners, body-shaped instead of query-string
    (specs/v3/08-api.md#http-query-method) — still a still-draft HTTP method,
    kept alongside the GET route, not replacing it."""
    return list_practitioners_public(body.specialty, body.language)


@app.get("/api/practitioners/{practitioner_id}")
def get_practitioner_public(practitioner_id: str) -> dict:
    practitioner = core_store.get_practitioner(practitioner_id)
    if practitioner is None or practitioner["status"] != "approved":
        raise HTTPException(404, "no such practitioner")
    core_store.log_profile_view(practitioner_id)
    return _public(practitioner)


@app.post("/api/practitioners")
async def practitioner_signup(
    name: str = Form(...), email: str = Form(...), password: str = Form(...),
    bio: str = Form(""), specialties: str = Form("[]"), languages: str = Form("[]"),
    years_experience: int = Form(0), consultation_price_cents: int = Form(0),
    photo: UploadFile | None = None,
) -> dict:
    auth.check_email_format(email)
    if core_store.get_practitioner_by_email(email) is not None:
        raise HTTPException(409, "An account with that email already exists.")
    auth.check_password_strength(password)
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
    return _public(practitioner)


class ContactSubmission(BaseModel):
    name: str
    email: str
    message: str


@app.post("/api/practitioners/{practitioner_id}/contact")
def contact_practitioner(practitioner_id: str, body: ContactSubmission) -> dict:
    practitioner = core_store.get_practitioner(practitioner_id)
    # A stale prerendered profile page (specs/v4/02-open-questions.md) can
    # keep sending contact-form submissions to a practitioner who's since
    # been suspended or rejected — this is the one part of that page that
    # actually writes something, so it gets a live check even though the
    # rest of the page can't (specs/v4/04-known-issues.md#m1).
    if practitioner is None or practitioner["status"] != "approved":
        raise HTTPException(404, "no such practitioner")
    return core_store.create_contact_submission(
        practitioner_id, body.name, body.email, body.message)


class SiteContactSubmission(BaseModel):
    name: str
    email: str
    message: str


@app.post("/api/contact")
def site_contact(body: SiteContactSubmission) -> dict:
    """specs/v8 §8.2 — a general /contact path, independent of the
    per-practitioner contact-form flow (POST /api/practitioners/{id}/contact,
    which goes to that one practitioner's own inbox). No new table: this is
    a low-volume, admin-facing inquiry, not a user-facing inbox anyone
    reviews/responds-to-in-app — core_store.log()'s existing trail (already
    readable via GET /api/superadmin/audit-log) is the right-sized place
    for it, not a second contact_form_submissions-shaped table."""
    auth.check_email_format(body.email)
    core_store.log("public", "site contact form submission",
                   f"{body.name} <{body.email}>: {body.message}")
    return {"ok": True}


class ClientSignup(BaseModel):
    name: str
    email: str
    password: str
    practitioner_id: str | None = None


@app.post("/api/clients")
def client_signup(body: ClientSignup) -> dict:
    auth.check_email_format(body.email)
    auth.check_password_strength(body.password)
    password_hash = auth.hash_password(body.password)
    existing = core_store.get_client_directory_entry(body.email)
    if existing is not None:
        # A Pro practitioner pre-created this client (specs/v2/05-practitioner-
        # portal.md); completing signup sets their password rather than
        # creating a duplicate account. password_set gates this: it's only
        # ever unset for a practitioner-created invite nobody has completed
        # yet. Without this check, anyone who merely knows an existing
        # client's email could silently reset their password — a real
        # account-takeover path found in the v2.6 review.
        client = vault.get_client(existing["practitioner_id"], existing["client_id"])
        if client is None:
            raise HTTPException(404, "invited client record is missing")
        if client.get("password_set"):
            raise HTTPException(
                409, "An account with that email already exists. Please log in.")
        vault.set_client_password(existing["practitioner_id"], client["id"],
                                  password_hash, mark_set=True)
        return {"id": client["id"], "practitioner_id": existing["practitioner_id"]}

    if not body.practitioner_id:
        raise HTTPException(400, "practitioner_id is required for a new client")
    practitioner = core_store.get_practitioner(body.practitioner_id)
    if practitioner is None or practitioner["plan"] != "pro":
        raise HTTPException(400, "That practitioner cannot accept clients right now.")
    client = vault.create_client(body.practitioner_id, body.name, body.email, password_hash)
    core_store.add_client_directory_entry(body.email, body.practitioner_id, client["id"])
    return {"id": client["id"], "practitioner_id": body.practitioner_id}


# --- Superadmin: manage other admin accounts ------------------------------------

class AdminCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "admin"


@app.get("/api/superadmin/admins")
def superadmin_list_admins(_: dict = Depends(auth.require_superadmin)) -> list[dict]:
    return _public_list(core_store.list_admins())


@app.post("/api/superadmin/admins")
def superadmin_create_admin(body: AdminCreate,
                            _: dict = Depends(auth.require_superadmin)) -> dict:
    if body.role not in core_store.ADMIN_ROLES:
        raise HTTPException(400, f"unknown admin role: {body.role}")
    auth.check_email_format(body.email)
    if core_store.get_admin_by_email(body.email) is not None:
        raise HTTPException(409, "An admin with that email already exists.")
    auth.check_password_strength(body.password)
    return _public(core_store.create_admin(
        body.email, auth.hash_password(body.password), body.name, body.role))


class AdminRoleUpdate(BaseModel):
    role: str


@app.put("/api/superadmin/admins/{admin_id}/role")
def superadmin_set_admin_role(admin_id: str, body: AdminRoleUpdate,
                              _: dict = Depends(auth.require_superadmin)) -> dict:
    try:
        admin = core_store.set_admin_role(admin_id, body.role)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if admin is None:
        raise HTTPException(404, "no such admin")
    return _public(admin)


@app.post("/api/superadmin/admins/{admin_id}/suspend")
def superadmin_suspend_admin(admin_id: str,
                             _: dict = Depends(auth.require_superadmin)) -> dict:
    try:
        admin = core_store.set_admin_active(admin_id, False)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if admin is None:
        raise HTTPException(404, "no such admin")
    return _public(admin)


@app.post("/api/superadmin/admins/{admin_id}/reactivate")
def superadmin_reactivate_admin(admin_id: str,
                                _: dict = Depends(auth.require_superadmin)) -> dict:
    admin = core_store.set_admin_active(admin_id, True)
    if admin is None:
        raise HTTPException(404, "no such admin")
    return _public(admin)


class AdminLinkPractitioner(BaseModel):
    practitioner_id: str | None = None


@app.put("/api/superadmin/admins/{admin_id}/link-practitioner")
def superadmin_link_practitioner(admin_id: str, body: AdminLinkPractitioner,
                                 _: dict = Depends(auth.require_superadmin)) -> dict:
    """specs/v8 §4.1/§7.2 — an optional, superadmin-set link from an admin
    account to an existing practitioner profile (not all admins are
    practitioners). Pass practitioner_id: null to unlink."""
    try:
        admin = core_store.set_admin_linked_practitioner(admin_id, body.practitioner_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if admin is None:
        raise HTTPException(404, "no such admin")
    return _public(admin)


@app.get("/api/superadmin/dedicated-endpoints")
def superadmin_list_dedicated_endpoints(
    _: dict = Depends(auth.require_superadmin),
) -> list[dict]:
    """Live status of every Nebius dedicated GPU deployment on this
    account (app/clients/nebius_admin.py) — the Qwen3-32B/Qwen3-Embedding-8B
    endpoints Reader/Graph-builder/Checker-LLM/Embedder route to.
    """
    try:
        return nebius_admin.list_dedicated_endpoints()
    except nebius_admin.NebiusAdminError as exc:
        raise HTTPException(502, str(exc))


@app.post("/api/superadmin/dedicated-endpoints/{endpoint_id}/start")
def superadmin_start_dedicated_endpoint(
    endpoint_id: str, _: dict = Depends(auth.require_superadmin),
) -> dict:
    try:
        result = nebius_admin.start_dedicated_endpoint(endpoint_id)
    except nebius_admin.NebiusAdminError as exc:
        raise HTTPException(502, str(exc))
    core_store.log("superadmin", "dedicated endpoint started", endpoint_id)
    return result


@app.post("/api/superadmin/dedicated-endpoints/{endpoint_id}/stop")
def superadmin_stop_dedicated_endpoint(
    endpoint_id: str, _: dict = Depends(auth.require_superadmin),
) -> dict:
    """Stops GPU billing while idle. Any AI-team role still routed to this
    endpoint's routing_key (app/config.py) will fail chat completions until
    it's started again — this is a real outage for whichever roles use it,
    not a transparent cost-saving toggle.
    """
    try:
        result = nebius_admin.stop_dedicated_endpoint(endpoint_id)
    except nebius_admin.NebiusAdminError as exc:
        raise HTTPException(502, str(exc))
    core_store.log("superadmin", "dedicated endpoint stopped", endpoint_id)
    return result


@app.get("/api/superadmin/llm-provider")
def superadmin_get_llm_provider(_: dict = Depends(auth.require_superadmin)) -> dict:
    """Which provider the five Anthropic-mappable chat roles (Reader,
    Graph-builder, Answer-engine, Reasoner, Checker-LLM) currently use.
    Role.EMBEDDER isn't included — it always stays on Nebius, Anthropic
    has no embeddings endpoint (app/clients/llm_client.py)."""
    return {"provider": get_llm_provider()}


class LLMProviderUpdate(BaseModel):
    provider: str


@app.post("/api/superadmin/llm-provider")
def superadmin_set_llm_provider(
    body: LLMProviderUpdate, _: dict = Depends(auth.require_superadmin),
) -> dict:
    try:
        set_llm_provider(body.provider)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    core_store.log("superadmin", "llm provider changed", body.provider)
    return {"provider": get_llm_provider()}


@app.get("/api/superadmin/audit-log")
def superadmin_audit_log(
    page: int = 1, per_page: int = 50, _: dict = Depends(auth.require_superadmin),
) -> dict:
    """Read path for core_store.log() — practitioner approvals/rejections/
    suspensions, plan changes, admin created/role-changed/suspended,
    questionnaire created/edited (core_store.py's call sites). Distinct
    from GET /api/audit, which is the Neo4j library-only event log
    (store.audit()) — that endpoint's docstring already explains the two
    trails don't mix; this is the other one, previously unreadable through
    any route.

    Paginated rather than dumping the whole table — this trail grows with
    every sensitive admin action, unlike the library's own.
    """
    per_page = max(1, min(per_page, 200))
    page = max(1, page)
    offset = (page - 1) * per_page
    events = core_store.list_audit_events(limit=per_page, offset=offset)
    return {"events": events, "total": core_store.count_audit_events(),
            "page": page, "per_page": per_page}


# --- Admin: practitioner management ---------------------------------------------

@app.get("/api/admin/notifications")
def admin_notifications(_admin: dict = Depends(auth.require_admin)) -> dict:
    pending = len(core_store.list_practitioners(status="pending"))
    return {"pending_practitioners": pending}


@app.get("/api/admin/practitioners")
def admin_list_practitioners(
    status: str = "", _admin: dict = Depends(auth.require_admin),
) -> list[dict]:
    return _public_list(core_store.list_practitioners(status=status or None))


class AdminPractitionerFilter(BaseModel):
    status: str = ""


@app.api_route("/api/admin/practitioners", methods=["QUERY"])
def admin_list_practitioners_query(
    body: AdminPractitionerFilter, _admin: dict = Depends(auth.require_admin),
) -> list[dict]:
    """Same as GET /api/admin/practitioners (specs/v3/08-api.md#http-query-method)."""
    return admin_list_practitioners(body.status, _admin)


class AdminPractitionerCreate(BaseModel):
    email: str
    password: str
    name: str
    bio: str = ""
    specialties: list[str] = []
    languages: list[str] = []
    years_experience: int = 0
    consultation_price_cents: int = 0


@app.post("/api/admin/practitioners")
def admin_create_practitioner(body: AdminPractitionerCreate,
                              _admin: dict = Depends(auth.require_admin)) -> dict:
    # Unlike public signup (POST /api/practitioners), an admin creating a
    # practitioner directly is already vouching for them — approved
    # immediately rather than landing in the pending review queue.
    auth.check_email_format(body.email)
    if core_store.get_practitioner_by_email(body.email) is not None:
        raise HTTPException(409, "A practitioner with that email already exists.")
    auth.check_password_strength(body.password)
    practitioner = core_store.create_practitioner_pending(
        email=body.email, password_hash=auth.hash_password(body.password),
        name=body.name, bio=body.bio, specialties=body.specialties,
        languages=body.languages, years_experience=body.years_experience,
        consultation_price_cents=body.consultation_price_cents,
    )
    practitioner = core_store.approve_practitioner(practitioner["id"])
    return _public(practitioner)


@app.post("/api/admin/practitioners/{practitioner_id}/approve")
def admin_approve(practitioner_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    practitioner = core_store.approve_practitioner(practitioner_id)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return _public(practitioner)


@app.post("/api/admin/practitioners/{practitioner_id}/reject")
def admin_reject(practitioner_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    practitioner = core_store.reject_practitioner(practitioner_id)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return _public(practitioner)


@app.post("/api/admin/practitioners/{practitioner_id}/suspend")
def admin_suspend(practitioner_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    practitioner = core_store.suspend_practitioner(practitioner_id)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return _public(practitioner)


class PlanUpdate(BaseModel):
    plan: str


@app.put("/api/admin/practitioners/{practitioner_id}/plan")
def admin_set_plan(practitioner_id: str, body: PlanUpdate,
                   _admin: dict = Depends(auth.require_admin)) -> dict:
    if body.plan not in core_store.PLANS:
        raise HTTPException(400, f"unknown plan: {body.plan}")
    if body.plan == "pro":
        try:
            return _public(core_store.activate_pro(practitioner_id))
        except ValueError:
            raise HTTPException(404, "no such practitioner")
    practitioner = core_store.set_plan(practitioner_id, body.plan)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return _public(practitioner)


class CanUploadLibraryUpdate(BaseModel):
    allowed: bool


@app.post("/api/admin/practitioners/{practitioner_id}/can-upload-library")
def admin_set_can_upload_library(
    practitioner_id: str, body: CanUploadLibraryUpdate,
    _admin: dict = Depends(auth.require_admin),
) -> dict:
    # Granting only makes sense for a Pro practitioner in good standing —
    # require_admin_or_upload_permitted_practitioner (app/auth.py) checks
    # Pro status too, so granting it to a Basic/pending practitioner would
    # set a flag that silently does nothing until their plan changes,
    # discovered confusingly later by the practitioner rather than here
    # (found in review). Revoking is always allowed regardless of plan.
    if body.allowed:
        target = core_store.get_practitioner(practitioner_id)
        if target is None:
            raise HTTPException(404, "no such practitioner")
        if target["status"] != "approved" or target["plan"] != "pro":
            raise HTTPException(
                400, "Library upload can only be granted to an approved Pro practitioner.")
    practitioner = core_store.set_can_upload_library(practitioner_id, body.allowed)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    return _public(practitioner)


@app.get("/api/admin/stats")
def admin_stats(_admin: dict = Depends(auth.require_admin)) -> dict:
    return core_store.site_stats()


@app.get("/api/admin/system-usage")
def admin_system_usage(_admin: dict = Depends(auth.require_admin)) -> dict:
    """The in-memory trend _sample_usage_loop() has been building up since
    this process started — populated on boot and sampled every _USAGE_SAMPLE_INTERVAL_S.
    Includes system load, memory metrics, and comprehensive per-agent model &
    token usage across all AI team members.
    """
    health_info = {}
    try:
        health_info = health()
    except Exception:
        pass
    agent_data = token_tracker.get_agent_models_and_tokens(health_info)
    return {
        "samples": _usage_history,
        "interval_s": _USAGE_SAMPLE_INTERVAL_S,
        "agents": agent_data["agents"],
        "totals": agent_data["totals"],
        "llm_provider": agent_data["llm_provider"],
    }


@app.get("/api/admin/practitioners/{practitioner_id}/client-count")
def admin_client_count(practitioner_id: str, _admin: dict = Depends(auth.require_admin)) -> dict:
    practitioner = core_store.get_practitioner(practitioner_id)
    if practitioner is None:
        raise HTTPException(404, "no such practitioner")
    count = len(vault.list_clients(practitioner_id)) if practitioner["plan"] == "pro" else 0
    return {"practitioner_id": practitioner_id, "clients": count,
            **core_store.practitioner_stats(practitioner_id)}


@app.get("/api/admin/clients")
def admin_list_clients(_admin: dict = Depends(auth.require_admin)) -> list[dict]:
    """Clients across every Pro practitioner's vault, for the admin Users
    page's Clients tab. Each client lives entirely inside their own
    practitioner's vault schema (app/vault.py) — there's no shared clients
    table to query directly — so this fans out per pro practitioner and
    tags each row with which practitioner it came from. Only Pro
    practitioners have a vault at all (Basic never calls activate_pro),
    same check admin_client_count above already makes.
    """
    out: list[dict] = []
    for p in core_store.list_practitioners():
        if p["plan"] != "pro":
            continue
        for c in vault.list_clients(p["id"]):
            out.append({
                "id": c["id"], "name": c["name"], "email": c["email"],
                "active": c["active"], "created_at": c["created_at"],
                "sessions": c["sessions"], "entries": c["entries"],
                "practitioner_id": p["id"], "practitioner_name": p["name"],
            })
    return out


@app.post("/api/admin/clients/{practitioner_id}/{client_id}/suspend")
def admin_suspend_client(
    practitioner_id: str, client_id: str, _admin: dict = Depends(auth.require_admin),
) -> dict:
    client = vault.set_client_active(practitioner_id, client_id, False)
    if client is None:
        raise HTTPException(404, "no such client")
    core_store.log("admin", "client suspended", f"{client_id} ({practitioner_id})")
    return {"id": client["id"], "active": client["active"]}


@app.post("/api/admin/clients/{practitioner_id}/{client_id}/reactivate")
def admin_reactivate_client(
    practitioner_id: str, client_id: str, _admin: dict = Depends(auth.require_admin),
) -> dict:
    client = vault.set_client_active(practitioner_id, client_id, True)
    if client is None:
        raise HTTPException(404, "no such client")
    core_store.log("admin", "client reactivated", f"{client_id} ({practitioner_id})")
    return {"id": client["id"], "active": client["active"]}


class QuestionnaireIn(BaseModel):
    title: str
    questions: list[dict]


@app.get("/api/admin/questionnaires")
def admin_list_questionnaires(_admin: dict = Depends(auth.require_admin)) -> list[dict]:
    # Multiple rows can legitimately show "Active" at once now (one per
    # scope: the admin default, plus each practitioner's own) — tag each
    # with who it belongs to so the admin table can show that, not just a
    # bare Active/No chip that used to be unambiguous when only one
    # questionnaire, ever, could be active (found in review).
    names = {p["id"]: p["name"] for p in core_store.list_practitioners()}
    rows = core_store.list_questionnaires()
    for r in rows:
        r["owner_name"] = names.get(r.get("practitioner_id")) if r.get("practitioner_id") else None
    return rows


@app.get("/api/admin/questionnaires/{questionnaire_id}")
def admin_get_questionnaire(questionnaire_id: str,
                            _admin: dict = Depends(auth.require_admin)) -> dict:
    questionnaire = core_store.get_questionnaire(questionnaire_id)
    if questionnaire is None:
        raise HTTPException(404, "no such questionnaire")
    return questionnaire


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


@app.post("/api/admin/questionnaires/{questionnaire_id}/activate")
def admin_activate_questionnaire(
    questionnaire_id: str, _admin: dict = Depends(auth.require_admin),
) -> dict:
    try:
        return core_store.set_questionnaire_active(questionnaire_id, True)
    except ValueError:
        raise HTTPException(404, "no such questionnaire")


@app.post("/api/admin/questionnaires/{questionnaire_id}/deactivate")
def admin_deactivate_questionnaire(
    questionnaire_id: str, _admin: dict = Depends(auth.require_admin),
) -> dict:
    try:
        return core_store.set_questionnaire_active(questionnaire_id, False)
    except ValueError:
        raise HTTPException(404, "no such questionnaire")


# --- Practitioner portal ---------------------------------------------------------

@app.get("/api/me/profile")
def me_profile(session: dict = Depends(auth.require_practitioner)) -> dict:
    return _public(core_store.get_practitioner(session["id"]))


@app.put("/api/me/profile")
async def me_update_profile(request: Request,
                            session: dict = Depends(auth.require_practitioner)) -> dict:
    practitioner_id = session["id"]
    content_type = request.headers.get("content-type", "")
    allowed = {"name", "bio", "specialties", "languages", "years_experience",
               "consultation_price_cents", "accepting_new_clients"}
    fields: dict = {}
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        for key in allowed:
            if key not in form:
                continue
            value = form[key]
            try:
                if key in ("specialties", "languages"):
                    fields[key] = json.loads(value or "[]")
                elif key == "years_experience" or key == "consultation_price_cents":
                    fields[key] = int(value)
                elif key == "accepting_new_clients":
                    fields[key] = str(value).lower() in ("true", "1", "on")
                else:
                    fields[key] = str(value)
            except (ValueError, TypeError) as exc:
                # A non-numeric years_experience/consultation_price_cents, or
                # malformed specialties/languages JSON, previously threw an
                # unhandled exception (raw 500) instead of a clean 400
                # (specs/v4/04-known-issues.md#m10).
                raise HTTPException(400, f"Invalid value for {key}.") from exc
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
    return _public(practitioner)


@app.get("/api/me/contacts")
def me_contacts(status: str = "",
                session: dict = Depends(auth.require_practitioner)) -> list[dict]:
    return core_store.list_contact_submissions(
        practitioner_id=session["id"], status=status or None)


@app.get("/api/me/notifications")
def me_notifications(session: dict = Depends(auth.require_practitioner)) -> dict:
    new_contacts = len(core_store.list_contact_submissions(
        practitioner_id=session["id"], status="new"))
    practitioner = core_store.get_practitioner(session["id"])
    unviewed_intake = (
        vault.count_unviewed_intake(session["id"]) if practitioner["plan"] == "pro" else 0
    )
    return {"new_contacts": new_contacts, "unviewed_intake": unviewed_intake}


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


@app.get("/api/me/knowledge")
def me_knowledge(session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    weights = vault.get_source_weights(session["id"])
    accessible_private = core_store.get_accessible_document_ids(session["id"])
    cards = store.catalogue(1)
    # A private document (specs/v6.9/01) this practitioner has no grant
    # for shouldn't just be excluded from their consult results — it
    # shouldn't be visible or viewable in their own library listing
    # either.
    cards = [c for c in cards if not c.get("is_private") or c["id"] in accessible_private]
    for card in cards:
        card["weight"] = weights.get(card["id"], card["grade"])
    return cards


class SourceWeightIn(BaseModel):
    weight: int


@app.put("/api/me/knowledge/{source_id}/weight")
def me_set_source_weight(source_id: str, body: SourceWeightIn,
                         session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    try:
        return vault.set_source_weight(session["id"], source_id, body.weight)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


# --- Practitioner portal: own questionnaires (Pro only) --------------------------

def _own_questionnaire_or_404(practitioner_id: str, questionnaire_id: str) -> dict:
    """404 (not 403) if the questionnaire isn't this practitioner's own —
    don't confirm existence of another practitioner's questionnaire, or the
    admin default. Used by edit/activate/deactivate — a practitioner can
    view the admin default (see _own_or_admin_default_questionnaire_or_404)
    but never modify it."""
    questionnaire = core_store.get_questionnaire(questionnaire_id)
    if questionnaire is None or questionnaire["practitioner_id"] != practitioner_id:
        raise HTTPException(404, "no such questionnaire")
    return questionnaire


def _own_or_admin_default_questionnaire_or_404(
    practitioner_id: str, questionnaire_id: str,
) -> dict:
    """Like _own_questionnaire_or_404, but also allows the admin default
    (practitioner_id IS NULL) — a practitioner can see what it asks before
    deciding whether to build their own, same as the admin builder's
    Preview isn't a separate action, just GET. Never used for a write."""
    questionnaire = core_store.get_questionnaire(questionnaire_id)
    if questionnaire is None or questionnaire["practitioner_id"] not in (practitioner_id, None):
        raise HTTPException(404, "no such questionnaire")
    return questionnaire


@app.get("/api/me/questionnaires")
def me_list_questionnaires(
    session: dict = Depends(auth.require_pro_practitioner),
) -> list[dict]:
    return core_store.list_questionnaires(session["id"], include_admin_default=True)


@app.get("/api/me/questionnaires/{questionnaire_id}")
def me_get_questionnaire(
    questionnaire_id: str, session: dict = Depends(auth.require_pro_practitioner),
) -> dict:
    return _own_or_admin_default_questionnaire_or_404(session["id"], questionnaire_id)


@app.post("/api/me/questionnaires")
def me_create_questionnaire(
    body: QuestionnaireIn, session: dict = Depends(auth.require_pro_practitioner),
) -> dict:
    return core_store.create_questionnaire(
        body.title, body.questions, session["id"], practitioner_id=session["id"])


@app.post("/api/me/questionnaires/{questionnaire_id}/edit")
def me_edit_questionnaire(
    questionnaire_id: str, body: QuestionnaireIn,
    session: dict = Depends(auth.require_pro_practitioner),
) -> dict:
    _own_questionnaire_or_404(session["id"], questionnaire_id)
    return core_store.edit_questionnaire(
        questionnaire_id, body.title, body.questions, session["id"])


@app.post("/api/me/questionnaires/{questionnaire_id}/activate")
def me_activate_questionnaire(
    questionnaire_id: str, session: dict = Depends(auth.require_pro_practitioner),
) -> dict:
    _own_questionnaire_or_404(session["id"], questionnaire_id)
    return core_store.set_questionnaire_active(questionnaire_id, True)


@app.post("/api/me/questionnaires/{questionnaire_id}/deactivate")
def me_deactivate_questionnaire(
    questionnaire_id: str, session: dict = Depends(auth.require_pro_practitioner),
) -> dict:
    _own_questionnaire_or_404(session["id"], questionnaire_id)
    return core_store.set_questionnaire_active(questionnaire_id, False)


# --- Practitioner portal: Pro clients + consultation -----------------------------

class NewClient(BaseModel):
    name: str
    email: str
    dob: str | None = None
    country: str | None = None


@app.get("/api/me/clients")
def me_list_clients(session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    return _public_list(vault.list_clients(session["id"]))


@app.post("/api/me/clients")
def me_create_client(body: NewClient,
                     session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    # No password yet — the client sets one when they complete signup
    # themselves (POST /api/clients), matched by email via client_directory.
    client = vault.create_client(
        practitioner_id, body.name, body.email,
        password_hash=auth.hash_password(str(uuid.uuid4())),
        dob=body.dob, country=body.country, password_set=False,
    )
    core_store.add_client_directory_entry(body.email, practitioner_id, client["id"])
    vault.log(practitioner_id, "practitioner", "client created", body.name, client["id"])
    return _public(client)


@app.get("/api/me/clients/{client_id}")
def me_get_client(client_id: str,
                  session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    client = vault.get_client(session["id"], client_id)
    if client is None:
        raise HTTPException(404, "no such client")
    return _public(client)


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
    # Back on by default, 2026-09-14 — was off (the local HHEM classifier
    # took 30-80s+/call, audited live) since earlier the same day. Now
    # backed by the LLM-as-judge Checker (app/reasoning/llm_checker.py,
    # specs/v6.3/02) instead of HHEM: 1.2-5s/call verified live against
    # production (2 real questions), fast enough to default back on. Set
    # run_check=false explicitly to skip it.
    run_check: bool = True
    session_id: str | None = None
    # "deep_research" (default, unchanged) = seed search + LLM-judged
    # graph traversal (app/retrieval/traversal.py). "general_lookup" =
    # a single pgvector similarity query, no traversal, no Neo4j round-
    # trip (app/retrieval/general_lookup.py) — trades breadth for speed,
    # a practitioner opts in per question, alongside deep_research, not
    # replacing it.
    retrieval_mode: str = "deep_research"


@app.post("/api/me/consult")
def me_consult(body: MeConsult, session: dict = Depends(auth.require_pro_practitioner)):
    """Streams progress as text/event-stream (specs/v3/08-api.md#live-progress-stream):
    an agent_start/agent_done pair per AI-team call with that call's real token
    usage, then one final `result` event carrying the same payload this route
    used to return as plain JSON — or an `error` event in place of `result` if
    an Anthropic call fails mid-stream. Everything that can still fail before
    any AI-team call runs (missing key, unknown client/session) is checked
    up front and raised as a normal HTTPException, so those keep their 400/404
    status codes instead of being buried inside the stream."""
    if not body.question.strip():
        # Previously ran (and billed) the full Librarian -> Specialist ->
        # Checker pipeline on a blank submission (specs/v4/04-known-
        # issues.md#m12).
        raise HTTPException(400, "Question cannot be empty.")

    practitioner_id = session["id"]
    if vault.get_client(practitioner_id, body.client_id) is None:
        raise HTTPException(404, "no such client")

    # get_patient_context() does its own independent vault.get_client()
    # lookup rather than reusing the check above (it's a separate module,
    # callable on its own) — a client deleted in the gap between the two
    # calls would otherwise make this None and crash the first
    # patient.as_query_text() call deep inside the stream with an opaque
    # AttributeError instead of a clean 404.
    patient = get_patient_context(practitioner_id, body.client_id)
    if patient is None:
        raise HTTPException(404, "no such client")

    session_id = body.session_id
    if session_id and vault.get_session(practitioner_id, session_id) is None:
        raise HTTPException(404, "no such consultation")
    if not session_id:
        now_ts = vault._now()
        history_data = vault.get_patient_history_up_to(practitioner_id, body.client_id, now_ts)
        init_summary = reasoner.generate_consult_intake_summary(history_data, now_ts)
        session_id = vault.create_session(
            practitioner_id, body.client_id, body.question, initial_summary=init_summary, started_at=now_ts
        )["id"]
    else:
        existing = vault.get_session(practitioner_id, session_id)
        if existing and existing.get("title") == "Consultation Session":
            vault.update_session_title(practitioner_id, session_id, body.question)

    history = vault.session_history(practitioner_id, session_id)[-6:]
    session_rec = vault.get_session(practitioner_id, session_id)
    initial_summary = session_rec.get("initial_summary") if session_rec else None
    # Applied throughout seed search and every traversal hop below — never
    # the shared admin grade — so a practitioner's own down/up-weight
    # actually affects only their own consultations (specs/v2/14 addendum #5).
    weights = vault.get_source_weights(practitioner_id)
    # Which private documents (specs/v6.9/01) this practitioner has an
    # explicit admin grant for — threaded through the same way `weights`
    # is, into every retrieval path a private document could otherwise
    # leak through.
    accessible_private = core_store.get_accessible_document_ids(practitioner_id)
    # specs/graph-traversal-rag — the new pipeline's calls (seed formation,
    # per-hop judging, reasoning) don't yet each take a separate `history`
    # parameter the way the old select_sources()/answer() did; folded into
    # the question text instead as a pragmatic stopgap so multi-turn
    # continuity ("and the dose?") isn't silently dropped. Threading
    # `history` as a real parameter through seed_search/traversal/reasoner
    # is cleaner and worth doing as a follow-up, not done here.
    history_block = "\n\n".join(
        f"Practitioner asked: {t['question']}\nYou answered: {t['answer']}" for t in history
    )
    prior_parts = []
    if initial_summary:
        prior_parts.append(f"Consultation Opening AI Briefing:\n{initial_summary}")
    if history_block:
        prior_parts.append(f"Earlier in this consultation:\n{history_block}")
    context_prefix = "\n\n".join(prior_parts)
    question = f"Earlier in this consultation:\n---\n{context_prefix}\n---\n\n{body.question}" \
        if context_prefix else body.question

    def _sse(event: dict) -> str:
        return f"data: {json.dumps(event)}\n\n"

    def stream():
        total_input_tokens = 0
        total_output_tokens = 0

        def _track(usage: dict) -> None:
            nonlocal total_input_tokens, total_output_tokens
            total_input_tokens += usage["input_tokens"]
            total_output_tokens += usage["output_tokens"]

        step_times: dict[str, float] = {}

        def _timed_done(event: dict, t0: float) -> dict:
            # Real wall-clock per step, not just token counts — found
            # live, 2026-09-14: a practitioner watching "running..." has
            # no way to tell a genuinely-slow-but-working step (a large
            # deep-research context legitimately taking 30-80s) from an
            # actually-stuck one without this. Recorded by agent name so
            # the final result can carry a full step-by-step breakdown,
            # not just each event's own instant.
            dt = round(time.monotonic() - t0, 2)
            step_times[event["agent"]] = step_times.get(event["agent"], 0) + dt
            return {**event, "duration_s": dt}

        try:
            if body.retrieval_mode == "general_lookup":
                # One pgvector query, no Neo4j round-trip — see
                # app/retrieval/general_lookup.py's module docstring for
                # why this deliberately skips the query-forming LLM call
                # deep_research's seed_search stage makes.
                yield _sse({"event": "agent_start", "agent": "lookup"})
                t0 = time.monotonic()
                traversal = general_lookup.lookup(question, patient, body.min_grade,
                                                  accessible_private_ids=accessible_private)
                _track(traversal.usage)
                yield _sse(_timed_done({"event": "agent_done", "agent": "lookup", **traversal.usage,
                           "accumulated": len(traversal.accumulated)}, t0))
                # body.question, not `question` — the latter has the entire
                # multi-turn history block prepended for the embedding call
                # above, and showing that raw in "How it searched" dumped
                # the whole conversation transcript into the seed-query
                # display instead of what the practitioner actually typed
                # (found live, 2026-09-15).
                search_query_repr = body.question
            else:
                yield _sse({"event": "agent_start", "agent": "seed_search"})
                t0 = time.monotonic()
                seed_result = seed_search.seed(question, patient, body.min_grade, weights=weights,
                                               accessible_private_ids=accessible_private)
                _track(seed_result.usage)
                yield _sse(_timed_done({"event": "agent_done", "agent": "seed_search", **seed_result.usage}, t0))
                search_query_repr = seed_result.search_query

                yield _sse({"event": "agent_start", "agent": "traversal"})
                t0 = time.monotonic()
                retriever = GraphTraversalRetriever(min_grade=body.min_grade, weights=weights,
                                                    accessible_private_ids=accessible_private)
                traversal = None
                # A broad question can legitimately run every hop up to
                # max_depth, each a full LLM round-trip — retrieve_streaming()
                # reports progress after each one instead of leaving the UI
                # showing "running..." indistinguishably from actually stuck
                # for the whole span (specs/v5, live: 90-100s+ on one question).
                hop_t0 = time.monotonic()
                for hop_event, hop_payload in retriever.retrieve_streaming(question, patient, seed_result):
                    if hop_event == "hop":
                        hop_dt = round(time.monotonic() - hop_t0, 2)
                        hop_t0 = time.monotonic()
                        yield _sse({"event": "agent_progress", "agent": "traversal",
                                   "hop": hop_payload.hop, "max_depth": hop_payload.max_depth,
                                   "candidates": hop_payload.candidates,
                                   "relevant": hop_payload.relevant,
                                   "accumulated": hop_payload.accumulated,
                                   "duration_s": hop_dt})
                    else:
                        traversal = hop_payload
                _track(traversal.usage)
                yield _sse(_timed_done({"event": "agent_done", "agent": "traversal", **traversal.usage,
                           "depth": traversal.depth_reached, "stopped": traversal.stopped_reason,
                           "accumulated": len(traversal.accumulated)}, t0))

            verdict = None
            revised = False
            if not traversal.accumulated:
                reasoned = None
                answer_text = (
                    "No source in the library answers this question, so I have nothing to "
                    "base an answer on and will not guess.\n\n"
                    f"Seed search query: {search_query_repr!r} found nothing usable at "
                    f"grade ≥ {body.min_grade}. Either lower the grade threshold, or add a "
                    "source covering this topic to the library."
                )
            else:
                yield _sse({"event": "agent_start", "agent": "reasoner"})
                t0 = time.monotonic()
                reasoned = reasoner.answer(question, patient, traversal)
                _track(reasoned.usage)
                yield _sse(_timed_done({"event": "agent_done", "agent": "reasoner", **reasoned.usage}, t0))
                answer_text = reasoned.text
                if body.run_check:
                    # LLM-as-judge Checker (app/reasoning/llm_checker.py,
                    # specs/v6.3/02), not the local HHEM classifier
                    # (app/reasoning/checker.py) — switched back
                    # 2026-09-15: HHEM's re-measured 6-105s/call was tried
                    # and reverted again in favor of the LLM-judge's
                    # 1-4s/call. HHEM is untouched and still selectable by
                    # swapping this import back.
                    yield _sse({"event": "agent_start", "agent": "checker"})
                    t0 = time.monotonic()
                    verdict = llm_checker.check(question, reasoned, patient.as_query_text())
                    _track(verdict["usage"])
                    yield _sse(_timed_done({"event": "agent_done", "agent": "checker",
                               **verdict["usage"]}, t0))
                    # Bounded retry, hard-capped at one attempt, same pattern
                    # as the pre-existing Checker retry: a "weak" verdict
                    # gets one revision with the same accumulated context
                    # and the Checker's own unsupported-sentence list.
                    if verdict["verdict"] == "weak":
                        yield _sse({"event": "agent_start", "agent": "reasoner", "retry": True})
                        t0 = time.monotonic()
                        revised_reasoned = reasoner.answer(
                            question, patient, traversal, unsupported=verdict["unsupported"])
                        _track(revised_reasoned.usage)
                        yield _sse(_timed_done({"event": "agent_done", "agent": "reasoner",
                                   "retry": True, **revised_reasoned.usage}, t0))
                        yield _sse({"event": "agent_start", "agent": "checker", "retry": True})
                        t0 = time.monotonic()
                        revised_verdict = llm_checker.check(
                            question, revised_reasoned, patient.as_query_text())
                        _track(revised_verdict["usage"])
                        yield _sse(_timed_done({"event": "agent_done", "agent": "checker", "retry": True,
                                   **revised_verdict["usage"]}, t0))
                        if (revised_verdict["verdict"] == "pass"
                                or len(revised_verdict["unsupported"]) < len(verdict["unsupported"])):
                            answer_text, verdict, revised = revised_reasoned.text, revised_verdict, True
                    # Whatever's left unsupported after the retry above (or
                    # immediately, if the retry didn't help) gets cut from
                    # the answer rather than shipped alongside a warning —
                    # an unverified claim shouldn't stay in the answer text
                    # just because it's flagged elsewhere.
                    if verdict["unsupported"]:
                        answer_text = _strip_unsupported(answer_text, verdict["unsupported"])
        except openai.APIError:
            yield _sse({"event": "error",
                       "message": "The AI service is temporarily unavailable. Try again shortly."})
            return
        except Exception:
            # Anything else (a Neo4j error out of the traversal loop, for
            # instance) previously broke the generator with no `error` event
            # at all — the frontend just saw a dropped, incomplete stream
            # instead of a clear failure (specs/v4/04-known-issues.md#h12).
            logging.exception("consult stream failed for practitioner %s", practitioner_id)
            yield _sse({"event": "error",
                       "message": "Something went wrong while answering. Try again shortly."})
            return

        vault.log(
            practitioner_id, "practitioner", "question asked",
            f"{body.question[:120]} — {len(traversal.accumulated)} nodes accumulated, "
            f"traversal stopped: {traversal.stopped_reason}, grade ≥{body.min_grade}",
            body.client_id,
        )
        cited_k = {int(n) for n in re.findall(r"K(\d+)", answer_text)}
        result = {
            "event": "result",
            "session_id": session_id,
            "answer": answer_text,
            "matched": bool(traversal.accumulated),
            "min_grade": body.min_grade,
            "check": verdict,
            "revised": revised,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "step_times": step_times,
            "total_time_s": round(sum(step_times.values()), 2),
            "retrieval_mode": body.retrieval_mode,
            "seed_search": {
                "search_query": search_query_repr,
                "seed_count": (
                    len(seed_result.seed_chunk_ids) + len(seed_result.seed_entity_ids)
                    if body.retrieval_mode != "general_lookup" else len(traversal.accumulated)
                ),
            },
            "traversal": {"depth_reached": traversal.depth_reached,
                         "stopped_reason": traversal.stopped_reason,
                         # The full per-hop log — what was expanded, what was
                         # pruned and why — surfaced for the clinician, per
                         # this architecture's own "close to a requirement,
                         # not a debugging nice-to-have" logging spec.
                         "path": [
                             {"hop": e.hop, "id": e.candidate_id, "label": e.candidate_label,
                              "relevant": e.relevant, "reason": e.reason}
                             for e in traversal.path_log
                         ]},
            # Only nodes the answer actually cites — traversal.accumulated is
            # everything the pipeline retrieved and kept, not everything the
            # Reasoner ended up using. Listing the whole accumulated set as
            # "Sources" implied every one of them backed the answer, which
            # wasn't true and looked like padding (found live, 2026-09-14).
            # Extracted as bare K-numbers, not whole "[K1]" substrings — the
            # model sometimes groups several into one bracket ("[K1, K3]"),
            # which a literal "[K1]" substring check would miss entirely.
            "sources": [
                {
                    "label": f"K{i + 1}",
                    "id": node.get("id"),
                    # Only a chunk-kind source has one real document to open
                    # (specs/v6.8/02) — an entity-kind source's node has no
                    # document_id at all, so this is None for those, same as
                    # every other document-only field below already is.
                    "document_id": node.get("document_id"),
                    "title": node.get("document_title") or node.get("name") or node.get("id"),
                    "grade": node.get("grade"),
                    "snippet": node.get("text") or node.get("name") or "",
                    "kind": "chunk" if node.get("text") is not None else "entity",
                    "locator": _locator(node),
                }
                for i, node in enumerate(traversal.accumulated)
                if (i + 1) in cited_k
            ],
        }
        vault.add_turn(practitioner_id, session_id, body.question, answer_text,
                      {k: v for k, v in result.items()
                       if k not in ("event", "answer", "session_id")})
        yield _sse(result)

    return StreamingResponse(stream(), media_type="text/event-stream")


# --- Practitioner portal: client detail (consultations, reports, intake) --------

def _owned_session(practitioner_id: str, client_id: str, session_id: str) -> dict:
    """A session belongs to this practitioner's vault and to this client —
    the 404 stays the same whether the session id is wrong or just points at
    someone else's client, so a guess can't distinguish the two."""
    session = vault.get_session(practitioner_id, session_id)
    if session is None or session["client_id"] != client_id:
        raise HTTPException(404, "no such consultation")
    return session


@app.get("/api/me/sessions/recent")
def me_recent_sessions(session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    return vault.list_recent_sessions(session["id"])


@app.get("/api/me/clients/{client_id}/sessions")
def me_list_sessions(client_id: str,
                     session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    if vault.get_client(session["id"], client_id) is None:
        raise HTTPException(404, "no such client")
    return vault.list_sessions(session["id"], client_id)


@app.post("/api/me/clients/{client_id}/sessions/init")
def me_init_session(client_id: str,
                    session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    """Starts a new consultation session by generating an opening AI summary of the
    patient and all recorded histories strictly up until this consultation point."""
    practitioner_id = session["id"]
    if vault.get_client(practitioner_id, client_id) is None:
        raise HTTPException(404, "no such client")
    now_ts = vault._now()
    history_data = vault.get_patient_history_up_to(practitioner_id, client_id, now_ts)
    summary = reasoner.generate_consult_intake_summary(history_data, now_ts)
    session_row = vault.create_session(
        practitioner_id,
        client_id,
        "Consultation Session",
        initial_summary=summary,
        started_at=now_ts,
    )
    return {**session_row, "turns": []}


@app.get("/api/me/clients/{client_id}/sessions/{session_id}")
def me_get_session(client_id: str, session_id: str,
                   session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    s = _owned_session(practitioner_id, client_id, session_id)
    if not s.get("initial_summary"):
        consultation_point = s.get("started_at") or vault._now()
        history_data = vault.get_patient_history_up_to(practitioner_id, client_id, consultation_point)
        summary = reasoner.generate_consult_intake_summary(history_data, consultation_point)
        vault.update_session_initial_summary(practitioner_id, session_id, summary)
        s["initial_summary"] = summary
    return {
        **s,
        "documents": {
            kind: vault.get_document(practitioner_id, session_id, kind)
            for kind in vault.DOCUMENT_KINDS
        },
    }


class SessionStatusUpdate(BaseModel):
    status: str


@app.patch("/api/me/clients/{client_id}/sessions/{session_id}/status")
def me_set_session_status(client_id: str, session_id: str, body: SessionStatusUpdate,
                          session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    _owned_session(practitioner_id, client_id, session_id)
    try:
        return vault.set_session_status(practitioner_id, session_id, body.status)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


class DocumentIn(BaseModel):
    content: str
    status: str = "draft"


@app.put("/api/me/clients/{client_id}/sessions/{session_id}/documents/{kind}")
def me_save_document(client_id: str, session_id: str, kind: str, body: DocumentIn,
                     session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    _owned_session(practitioner_id, client_id, session_id)
    try:
        return vault.save_document(
            practitioner_id, session_id, client_id, kind, body.content, body.status)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/me/clients/{client_id}/sessions/{session_id}/summary")
def me_summarize_session(client_id: str, session_id: str,
                         session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    """Runs the Summariser (specs/v3/07-ai-team.md) — fully implemented since
    v1 but never reachable from a route until now."""
    practitioner_id = session["id"]
    _owned_session(practitioner_id, client_id, session_id)
    transcript = vault.session_transcript(practitioner_id, session_id)
    try:
        summary = reasoner.summarize_session(transcript)
    except openai.APIError as exc:
        raise HTTPException(
            502, "The AI service is temporarily unavailable. Try again shortly."
        ) from exc
    # Deterministic, not left to the Summariser's discretion: if any turn's
    # Checker verdict wasn't a clean 'pass', say so explicitly rather than
    # relying on the model to have carried it through from the transcript flag.
    if vault.session_has_flagged_turn(practitioner_id, session_id):
        summary += ("\n\n⚠ At least one answer in this consultation was flagged "
                    "by the internal accuracy check as not fully verified "
                    "against its sources. Review the consultation before "
                    "relying on this summary.")
    vault.add_entry(practitioner_id, client_id, "session_summary", summary,
                     session_id=session_id)
    return {"summary": summary}


@app.get("/api/me/clients/{client_id}/documents")
def me_list_documents(client_id: str,
                      session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    if vault.get_client(session["id"], client_id) is None:
        raise HTTPException(404, "no such client")
    return vault.list_documents(session["id"], client_id)


@app.get("/api/me/clients/{client_id}/intake")
def me_get_intake(client_id: str,
                  session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    if vault.get_client(practitioner_id, client_id) is None:
        raise HTTPException(404, "no such client")
    response = vault.get_questionnaire_response(practitioner_id, client_id)
    questionnaire = (
        core_store.get_questionnaire(response["questionnaire_id"]) if response else None
    )
    if response:
        vault.mark_intake_viewed(practitioner_id, client_id)
    return {
        "response": response,
        "questionnaire": questionnaire,
        "notes": vault.list_intake_notes(practitioner_id, client_id),
    }


class IntakeNoteIn(BaseModel):
    theme: str
    note: str


@app.put("/api/me/clients/{client_id}/intake/notes")
def me_save_intake_note(client_id: str, body: IntakeNoteIn,
                        session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    if vault.get_client(practitioner_id, client_id) is None:
        raise HTTPException(404, "no such client")
    return vault.upsert_intake_note(practitioner_id, client_id, body.theme, body.note)


# --- Client record entries (labs, conditions, medications, notes) -----------------
# The consult pipeline's patient context (app/patient/context.py) has read
# conditions/medications/labs since it was written, but nothing ever wrote
# them — vault.add_entry() was only ever called for session_summary. Found
# live, 2026-09-14: every real client's recent_labs was empty not because
# no labs existed, but because there was no way to record one.

# session_summary is written by me_summarize_session() only, not this
# endpoint — a practitioner shouldn't be able to author a "summary" entry
# by hand and have it silently treated the same as a real AI-written one.
_RECORD_ENTRY_KINDS = tuple(k for k in vault.KINDS if k != "session_summary")


class RecordEntryIn(BaseModel):
    kind: str
    content: str


@app.get("/api/me/clients/{client_id}/entries")
def me_list_entries(client_id: str,
                    session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    practitioner_id = session["id"]
    if vault.get_client(practitioner_id, client_id) is None:
        raise HTTPException(404, "no such client")
    return vault.list_entries(practitioner_id, client_id)


@app.post("/api/me/clients/{client_id}/entries")
def me_add_entry(client_id: str, body: RecordEntryIn,
                 session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    if vault.get_client(practitioner_id, client_id) is None:
        raise HTTPException(404, "no such client")
    if body.kind not in _RECORD_ENTRY_KINDS:
        raise HTTPException(400, f"kind must be one of {_RECORD_ENTRY_KINDS}")
    if not body.content.strip():
        raise HTTPException(400, "content is required")
    entry = vault.add_entry(practitioner_id, client_id, body.kind, body.content.strip())
    vault.log(practitioner_id, "practitioner", f"{body.kind} recorded",
              body.content[:120], client_id)
    return entry


@app.delete("/api/me/clients/{client_id}/entries/{entry_id}")
def me_delete_entry(client_id: str, entry_id: str,
                    session: dict = Depends(auth.require_pro_practitioner)) -> dict:
    practitioner_id = session["id"]
    if vault.get_client(practitioner_id, client_id) is None:
        raise HTTPException(404, "no such client")
    if not vault.delete_entry(practitioner_id, client_id, entry_id):
        raise HTTPException(404, "no such entry")
    return {"deleted": entry_id}


# A client can add to their own record too — self-reported labs/conditions/
# etc. are marked with this prefix so the practitioner-facing panel and the
# consult pipeline's context can tell them apart from what a practitioner
# entered themselves (self-reported data carries less clinical certainty).
# No schema change for this: record_entries has no author column, so the
# marker lives in the content string itself, same technique already used
# for legacy history/note entries (app/patient/context.py's "[kind] ..."
# prefix).
_PATIENT_REPORTED_PREFIX = "[patient-reported] "


@app.get("/api/me/entries")
def me_list_own_entries(session: dict = Depends(auth.require_client)) -> list[dict]:
    # Only the client's own self-reported entries — not a practitioner's
    # private clinical notes/conditions/medications about them. A SOAP-style
    # note isn't necessarily meant to be shown back to the patient verbatim,
    # so this is a real privacy boundary, not just a display filter.
    entries = vault.list_entries(session["practitioner_id"], session["id"])
    return [e for e in entries if e["content"].startswith(_PATIENT_REPORTED_PREFIX)]


@app.post("/api/me/entries")
def me_add_own_entry(body: RecordEntryIn, session: dict = Depends(auth.require_client)) -> dict:
    if body.kind not in _RECORD_ENTRY_KINDS:
        raise HTTPException(400, f"kind must be one of {_RECORD_ENTRY_KINDS}")
    if not body.content.strip():
        raise HTTPException(400, "content is required")
    practitioner_id, client_id = session["practitioner_id"], session["id"]
    entry = vault.add_entry(practitioner_id, client_id, body.kind,
                            _PATIENT_REPORTED_PREFIX + body.content.strip())
    vault.log(practitioner_id, "client", f"{body.kind} recorded by patient",
              body.content[:120], client_id)
    return entry


@app.delete("/api/me/entries/{entry_id}")
def me_delete_own_entry(entry_id: str, session: dict = Depends(auth.require_client)) -> dict:
    practitioner_id, client_id = session["practitioner_id"], session["id"]
    entries = vault.list_entries(practitioner_id, client_id)
    entry = next((e for e in entries if e["id"] == entry_id), None)
    if entry is None:
        raise HTTPException(404, "no such entry")
    # A client can only remove what they themselves added — not a
    # practitioner-authored entry, even one about them.
    if not entry["content"].startswith(_PATIENT_REPORTED_PREFIX):
        raise HTTPException(403, "only entries you added yourself can be removed")
    vault.delete_entry(practitioner_id, client_id, entry_id)
    return {"deleted": entry_id}


# --- Client portal -----------------------------------------------------------------

@app.get("/api/me/questionnaire")
def me_active_questionnaire(session: dict = Depends(auth.require_client)) -> dict | None:
    return core_store.get_active_questionnaire(session["practitioner_id"])


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


def _save_uploaded_file(
    practitioner_id: str, client_id: str, filename: str, content_type: str,
    content: bytes | Path,
) -> dict:
    """Shared by the direct-upload route and the chunked-upload complete
    step below — everything past receiving the bytes is identical."""
    file_id = str(uuid.uuid4())
    if isinstance(content, Path):
        saved = vault_files.save_from_path(practitioner_id, file_id, content, filename)
    else:
        saved = vault_files.save(practitioner_id, file_id, content, filename)
    if not saved:
        raise HTTPException(500, "could not store the uploaded file")
    return vault.save_uploaded_file(
        practitioner_id, client_id, filename,
        content_type or _media_type(filename),
        str(vault_files.path(practitioner_id, file_id, filename)),
    )


@app.post("/api/me/files")
async def me_upload_file(
    file: UploadFile, session: dict = Depends(auth.require_client),
) -> dict:
    """Upload a client file in one request. For anything that might exceed
    _MAX_CLIENT_FILE_BYTES, use the chunked routes below instead (POST
    /api/me/files/upload/init, .../chunk, .../complete), which accept up
    to cfg.max_upload_bytes (200 MB) without buffering the whole file in
    memory."""
    raw = await file.read()
    if len(raw) > _MAX_CLIENT_FILE_BYTES:
        raise HTTPException(
            400,
            f"File must be under {_MAX_CLIENT_FILE_BYTES // (1024 * 1024)} MB "
            "via direct upload — use the chunked upload for a larger file.")
    filename = file.filename or "upload"
    return _save_uploaded_file(
        session["practitioner_id"], session["id"], filename, file.content_type or "", raw)


class ClientFileUploadInit(BaseModel):
    filename: str
    total_size: int
    content_type: str = ""


@app.post("/api/me/files/upload/init")
def me_file_upload_init(body: ClientFileUploadInit,
                        session: dict = Depends(auth.require_client)) -> dict:
    return uploads.start(body.total_size, {
        "filename": body.filename, "content_type": body.content_type,
    })


@app.post("/api/me/files/upload/{upload_id}/chunk")
async def me_file_upload_chunk(upload_id: str, chunk: UploadFile,
                               session: dict = Depends(auth.require_client)) -> dict:
    return await uploads.append_chunk(upload_id, chunk)


@app.post("/api/me/files/upload/{upload_id}/complete")
def me_file_upload_complete(upload_id: str,
                            session: dict = Depends(auth.require_client)) -> dict:
    path, meta = uploads.finish(upload_id)
    try:
        return _save_uploaded_file(
            session["practitioner_id"], session["id"],
            meta["filename"], meta["content_type"], path)
    finally:
        uploads.cleanup(upload_id)


@app.get("/api/me/questionnaire/response")
def me_questionnaire_response(session: dict = Depends(auth.require_client)) -> dict | None:
    return vault.get_questionnaire_response(session["practitioner_id"], session["id"])


@app.get("/api/me/files")
def me_list_files(session: dict = Depends(auth.require_client)) -> list[dict]:
    # storage_path is an internal filesystem path, not the client's business.
    return [{k: v for k, v in f.items() if k != "storage_path"}
            for f in vault.list_uploaded_files(session["practitioner_id"], session["id"])]


def _serve_uploaded_file(practitioner_id: str, file_id: str, client_id: str | None) -> FileResponse:
    """Shared by the client's own download route and the practitioner's
    client-file route below — the upload path (POST /api/me/files) was fully
    wired, but nothing ever served the bytes back to either side
    (specs/v4/04-known-issues.md#h2)."""
    row = vault.get_uploaded_file(practitioner_id, file_id, client_id)
    if row is None:
        raise HTTPException(404, "no such file")
    path = Path(row["storage_path"])
    if not path.is_file():
        raise HTTPException(404, "the file is no longer on disk")
    safe = "".join(c for c in Path(row["original_name"]).name if c.isprintable() and c != '"')
    media_type = row.get("media_type") or _media_type(row["original_name"])
    # Same reasoning as GET /api/sources/{id}/original: only preview types
    # we control the rendering of; anything else downloads instead of
    # rendering inline, and nosniff stops the browser from second-guessing it.
    disposition = ("inline" if media_type in ("application/pdf", "text/plain")
                   else "attachment")
    return FileResponse(
        path, media_type=media_type,
        headers={"Content-Disposition": f'{disposition}; filename="{safe}"',
                 "X-Content-Type-Options": "nosniff"},
    )


@app.get("/api/me/files/{file_id}")
def me_download_file(file_id: str, session: dict = Depends(auth.require_client)) -> FileResponse:
    return _serve_uploaded_file(session["practitioner_id"], file_id, session["id"])


@app.get("/api/me/clients/{client_id}/files")
def me_list_client_files(client_id: str,
                         session: dict = Depends(auth.require_pro_practitioner)) -> list[dict]:
    if vault.get_client(session["id"], client_id) is None:
        raise HTTPException(404, "no such client")
    return [{k: v for k, v in f.items() if k != "storage_path"}
            for f in vault.list_uploaded_files(session["id"], client_id)]


@app.get("/api/me/clients/{client_id}/files/{file_id}")
def me_download_client_file(client_id: str, file_id: str,
                            session: dict = Depends(auth.require_pro_practitioner)) -> FileResponse:
    if vault.get_client(session["id"], client_id) is None:
        raise HTTPException(404, "no such client")
    return _serve_uploaded_file(session["id"], file_id, client_id)


# --- Frontend -----------------------------------------------------------------
#
# specs/v4: SvelteKit's adapter-static build (WEB_BUILD) replaces the old
# hand-written static/public|practitioner|client|admin pages. adapter-static
# writes a prerendered route "/a/b" as "a/b.html" (and "/" as "index.html");
# the auth-gated portals (client/practitioner/admin) are ssr:false, so any
# path under them isn't a file on disk at all — it falls through to
# app.html, the SPA shell, whose client-side router (and its own auth
# guards, specs/v4/01 §Information architecture) takes over from there.
# STATIC/the old pages stay on disk, unmounted from any page route now —
# the pre-cutover record, not a live fallback.

app.mount("/photos", StaticFiles(directory=cfg.photos_path), name="photos")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/_app", StaticFiles(directory=WEB_BUILD / "_app"), name="web-assets")
# web/static/images/* (e.g. the FHC homepage's hero/portrait/logo assets)
# adapter-static copies these into web-build/images alongside the page
# HTML, but nothing mounted that subdirectory — requests fell through to
# the catch-all SPA shell below and came back 200 with index.html instead
# of the image, i.e. every <img> on the homepage was silently broken.
app.mount("/images", StaticFiles(directory=WEB_BUILD / "images"), name="web-images")

# Legacy URL, kept as a redirect — the directory is the site root now.
_WEB_ROOT_FILES = {
    "robots.txt", "favicon.svg", "favicon.png", "favicon.ico",
    "sitemap.xml", "llms.txt", "og-image.png",
}


@app.get("/directory")
def directory_redirect() -> RedirectResponse:
    return RedirectResponse("/", status_code=301)


@app.get("/{full_path:path}")
def web_app(full_path: str) -> FileResponse:
    # Root-level files adapter-static writes alongside the page HTML
    # (robots.txt, a favicon) — served as-is.
    if full_path in _WEB_ROOT_FILES:
        candidate = WEB_BUILD / full_path
        if candidate.is_file():
            return FileResponse(candidate)

    clean = full_path.strip("/")
    html_path = WEB_BUILD / (f"{clean}.html" if clean else "index.html")
    if html_path.is_file():
        return FileResponse(html_path)

    # Not a prerendered file — an auth-gated portal route, a coach/{id}
    # approved after the last build, or anything else the SPA router owns.
    # 200 with the app shell, not 404: an unmatched path here might still
    # be a real client-side route, and a 404 on the shell itself would be
    # wrong for those; SvelteKit's own router shows a real not-found state
    # for paths that turn out not to exist.
    shell = WEB_BUILD / "app.html"
    if shell.is_file():
        return FileResponse(shell)
    raise HTTPException(404, "Not found")
