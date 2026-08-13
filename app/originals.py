"""The original file store: uploaded documents kept byte-for-byte.

Ingestion is lossy in ways that are invisible afterwards — chunking splits the
text and overlaps the seams, and PDF extraction drops tables, figures, layout and
anything in a scanned page. `body` is only what pypdf could read. A clinician who
distrusts a citation needs the document, not our reading of it.

Files are named by source id, never by the uploaded filename: two uploads called
`guidelines.pdf` must not collide, and a filename off the wire must never become
a path.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .config import get_config

cfg = get_config()


def _dir() -> Path:
    path = Path(cfg.originals_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save(source_id: str, raw: bytes, filename: str) -> bool:
    """Archive the uploaded bytes. Returns False if it could not be written.

    The caller ingests anyway on failure: losing a whole source because its
    archive copy could not be saved is the worse outcome. The source then simply
    has no original, exactly like one ingested before this store existed.
    """
    try:
        (_dir() / f"{source_id}{Path(filename).suffix}").write_bytes(raw)
        return True
    except OSError as exc:
        logging.warning("could not archive original for %s: %s", source_id, exc)
        return False


def path(source_id: str, filename: str) -> Path | None:
    """The stored file, or None if it is not there."""
    p = Path(cfg.originals_path) / f"{source_id}{Path(filename).suffix}"
    return p if p.is_file() else None


def delete(source_id: str) -> None:
    """Best-effort removal, so a file cannot outlive its source node.

    Globbed rather than reconstructed: the node — which carries the extension —
    may already be gone by the time we are called. Ids are UUIDs, so the prefix
    cannot match another source's file.
    """
    for p in Path(cfg.originals_path).glob(f"{source_id}*"):
        try:
            p.unlink()
        except OSError as exc:
            logging.warning("could not remove original %s: %s", p, exc)
