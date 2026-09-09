"""Chunked upload staging — shared by the two large-upload paths (admin
source ingest, client file upload).

Nothing here knows about sources, clients, or auth — it just accepts a
declared-size file as a sequence of chunks and writes each one straight to
disk as it arrives, so this process never holds more than one chunk's
worth of a 200 MB upload in memory at once. `clinic.service` caps this
process at 500 MB total (DEPLOY.md) on a box where Neo4j's JVM already
takes most of what's free — `raw = await file.read()` on a 200 MB upload,
the previous approach, would risk an OOM kill under real load.

Not resumable across a server restart or process crash — the staging file
would simply be orphaned and swept later. A client that loses its upload
mid-transfer restarts it; full resumability (persisting per-chunk state
somewhere the client can reattach to after a reload) is real added
complexity for a PoC-scale, single-admin-at-a-time upload pattern, not
built here.

`upload_id` is a UUID4 and that's the only access control at this layer —
whoever holds it can append chunks or complete it. The routes in main.py
still gate *starting* an upload behind require_admin/require_client, but
don't check that the same session owns a given upload_id on later calls,
same trust boundary (opaque UUID, no separate per-owner check) this app
already uses for session_id/source_id/client_id elsewhere. Worth revisiting
if uploads ever need to be safe against a hostile *authenticated* peer
guessing another user's upload_id, not just an unauthenticated one.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .config import get_config

cfg = get_config()

_READ_CHUNK_BYTES = 1024 * 1024  # bounds memory use while writing one chunk
_STALE_AFTER_SECONDS = 24 * 60 * 60


def _staging_dir() -> Path:
    p = Path(cfg.upload_staging_path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _part_path(upload_id: str) -> Path:
    return _staging_dir() / f"{upload_id}.part"


def _meta_path(upload_id: str) -> Path:
    return _staging_dir() / f"{upload_id}.json"


def _read_meta(upload_id: str) -> dict:
    try:
        return json.loads(_meta_path(upload_id).read_text())
    except FileNotFoundError:
        raise HTTPException(404, "no such upload") from None


def sweep_stale(max_age_seconds: int = _STALE_AFTER_SECONDS) -> int:
    """Remove abandoned uploads (crashed client, closed tab mid-transfer).
    Called opportunistically from start(), not on a schedule — fine at
    this scale, there is no long-running worker to hang this off of."""
    now = time.time()
    removed = 0
    for meta_file in _staging_dir().glob("*.json"):
        try:
            if now - meta_file.stat().st_mtime > max_age_seconds:
                upload_id = meta_file.stem
                _part_path(upload_id).unlink(missing_ok=True)
                meta_file.unlink(missing_ok=True)
                removed += 1
        except OSError as exc:
            logging.warning("could not sweep stale upload %s: %s", meta_file, exc)
    return removed


def start(total_size: int, meta: dict) -> dict:
    """Declare a new upload. `meta` is caller-defined (filename, content
    type, whatever the domain needs at complete() time) and round-tripped
    verbatim — this module never inspects it."""
    if total_size <= 0 or total_size > cfg.max_upload_bytes:
        raise HTTPException(
            400,
            f"File must be under {cfg.max_upload_bytes // (1024 * 1024)} MB.",
        )
    sweep_stale()
    upload_id = str(uuid.uuid4())
    _part_path(upload_id).touch()
    _meta_path(upload_id).write_text(json.dumps({"total_size": total_size, **meta}))
    return {"upload_id": upload_id, "total_size": total_size}


async def append_chunk(upload_id: str, chunk: UploadFile) -> dict:
    """Streams one chunk onto the staging file. Bounded-memory regardless
    of chunk size: reads and writes _READ_CHUNK_BYTES at a time rather
    than materializing the whole chunk as one `bytes` object."""
    part = _part_path(upload_id)
    if not part.exists():
        raise HTTPException(404, "no such upload")
    meta = _read_meta(upload_id)
    with part.open("ab") as f:
        while True:
            data = await chunk.read(_READ_CHUNK_BYTES)
            if not data:
                break
            f.write(data)
    received = part.stat().st_size
    if received > meta["total_size"]:
        cleanup(upload_id)
        raise HTTPException(400, "received more bytes than declared at init")
    return {"received": received, "total_size": meta["total_size"]}


def finish(upload_id: str) -> tuple[Path, dict]:
    """Verifies the upload is actually complete and hands back the staged
    file's path plus its meta dict. Caller owns the file after this —
    move or copy it out, then call cleanup()."""
    meta = _read_meta(upload_id)
    part = _part_path(upload_id)
    if not part.exists() or part.stat().st_size != meta["total_size"]:
        raise HTTPException(
            400,
            f"Upload incomplete: {part.stat().st_size if part.exists() else 0} of "
            f"{meta['total_size']} bytes received.",
        )
    return part, meta


def cleanup(upload_id: str) -> None:
    _part_path(upload_id).unlink(missing_ok=True)
    _meta_path(upload_id).unlink(missing_ok=True)
