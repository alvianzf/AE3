"""A small in-process concurrency-limiting queue for backgrounded
ingestion jobs (app/main.py's staged-promotion flow).

Found live, 2026-11-03: a single large PDF's own Reader/embed/8-way-
concurrent-graph-extraction memory footprint was already enough to
OOM-kill the whole app at the time's MemoryMax (DEPLOY.md). FastAPI's
`BackgroundTasks` has no queue-depth or concurrency limit of its own —
it just runs whatever's handed to it in its thread pool — so a second
ingest started while a first is still running runs fully alongside it,
with no backpressure at all. N simultaneous ingests multiply that same
per-ingest memory risk by N.

Durability lives in the existing `ingestion_jobs` Postgres row, not
here — a page refresh or a login from a different device just re-polls
`GET /api/ingestion-jobs/{id}` / `.../active`, same as before this
module existed. This module only decides *when* a queued job's actual
work starts, via a bounded worker pool (`cfg.ingestion_concurrency`)
consuming an in-process `asyncio.Queue`.

Not crash-safe across a server restart: a job still `status='queued'`
(not yet picked up by a worker) when the process dies is not re-queued
on the next boot — `core_store.fail_orphaned_ingestion_jobs()` marks it
a clear, retryable error instead, the same outcome an already-'running'
job already gets (DEPLOY.md's own stated acceptance for this: "nothing
is ever silently lost, only interrupted and reported as such"). Fully
surviving a crash mid-queue would mean persisting every job's ingest
arguments (pages, kind, origin, replaces, the original file) on the
Postgres row itself, not just its status — a real future upgrade if
queue depths ever get large enough for this to matter, not built
preemptively here.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from ..config import get_config

cfg = get_config()

_queue: asyncio.Queue | None = None
_workers: list[asyncio.Task] = []


def _get_queue() -> asyncio.Queue:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def _worker(name: str) -> None:
    queue = _get_queue()
    while True:
        job_id, fn, args, kwargs = await queue.get()
        try:
            # Check if job was cancelled while waiting in queue
            from .. import core_store
            job = core_store.get_ingestion_job(job_id)
            if job and job.get("status") == "error":
                logging.info("ingestion queue worker %s: job %s was cancelled before pickup", name, job_id)
                continue

            # _run_staged_ingest_job (app/main.py) is a plain synchronous
            # function — to_thread() is the same thread-pool execution
            # BackgroundTasks itself used, just with this queue's worker
            # count as a hard cap in front of it instead of unlimited.
            await asyncio.to_thread(fn, *args, **kwargs)
        except Exception:
            logging.exception("ingestion queue worker %s: job %s raised", name, job_id)
        finally:
            queue.task_done()


def start_workers() -> None:
    """Called once from app/main.py's lifespan startup. Idempotent — a
    second call (there shouldn't be one, but the app/main.py lifespan
    pattern elsewhere in this file tolerates being careful about it) is
    a no-op rather than doubling the worker pool."""
    if _workers:
        return
    for i in range(max(1, cfg.ingestion_concurrency)):
        _workers.append(asyncio.create_task(_worker(f"ingest-{i}")))


def enqueue(job_id: str, fn: Callable, *args, **kwargs) -> None:
    """Hands a backgrounded ingest job to the queue instead of FastAPI's
    BackgroundTasks.add_task() — same deferred/threaded execution, just
    gated by the worker pool's concurrency cap rather than running
    immediately and unconditionally."""
    _get_queue().put_nowait((job_id, fn, args, kwargs))
