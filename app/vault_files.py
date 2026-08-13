"""A practitioner's client-uploaded files, kept byte-for-byte.

Same id-not-filename pattern as app/originals.py, parameterized by
practitioner_id so each Pro practitioner's client files live in their own
subdirectory rather than one shared store.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .config import get_config

cfg = get_config()


def _dir(practitioner_id: str) -> Path:
    path = Path(cfg.vault_files_path) / practitioner_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save(practitioner_id: str, file_id: str, raw: bytes, filename: str) -> bool:
    """Archive the uploaded bytes. Returns False if it could not be written."""
    try:
        (_dir(practitioner_id) / f"{file_id}{Path(filename).suffix}").write_bytes(raw)
        return True
    except OSError as exc:
        logging.warning(
            "could not archive vault file for %s/%s: %s",
            practitioner_id, file_id, exc)
        return False


def path(practitioner_id: str, file_id: str, filename: str) -> Path | None:
    """The stored file, or None if it is not there."""
    p = Path(cfg.vault_files_path) / practitioner_id / f"{file_id}{Path(filename).suffix}"
    return p if p.is_file() else None


def delete(practitioner_id: str, file_id: str) -> None:
    """Best-effort removal, so a file cannot outlive its record.

    Globbed rather than reconstructed: the record — which carries the
    extension — may already be gone by the time we are called. Ids are
    UUIDs, so the prefix cannot match another file's.
    """
    for p in _dir(practitioner_id).glob(f"{file_id}*"):
        try:
            p.unlink()
        except OSError as exc:
            logging.warning("could not remove vault file %s: %s", p, exc)
