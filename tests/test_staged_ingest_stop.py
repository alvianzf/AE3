import unittest
import uuid
from unittest.mock import patch

from app import core_store
from app.main import app, _cancelled_job_ids, _is_job_cancelled


class StagedIngestStopTests(unittest.TestCase):
    def setUp(self):
        staged = core_store.create_staged_source(
            kind="text",
            filename="sample.txt",
            media_type="text/plain",
            pages=[(1, "Hello world text content.")],
            created_by="admin_test",
        )
        self.staged_id = staged["id"]
        self.owner = None

    def tearDown(self):
        core_store.delete_staged_source(self.staged_id)

    def test_cancel_active_jobs_for_staged(self):
        job = core_store.create_ingestion_job(self.staged_id, None, "sample.txt")
        self.assertEqual(job["status"], "queued")

        cancelled = core_store.cancel_active_jobs_for_staged(self.staged_id, "Stopped by user.")
        self.assertIn(job["id"], cancelled)

        updated_job = core_store.get_ingestion_job(job["id"])
        self.assertEqual(updated_job["status"], "error")
        self.assertEqual(updated_job["error_message"], "Stopped by user.")

    def test_is_job_cancelled_checks_set_and_db(self):
        job = core_store.create_ingestion_job(self.staged_id, None, "sample.txt")
        self.assertFalse(_is_job_cancelled(job["id"], self.staged_id, None))

        _cancelled_job_ids.add(job["id"])
        self.assertTrue(_is_job_cancelled(job["id"], self.staged_id, None))
        _cancelled_job_ids.discard(job["id"])

        # When staged source is deleted, _is_job_cancelled returns True
        core_store.delete_staged_source(self.staged_id)
        self.assertTrue(_is_job_cancelled(job["id"], self.staged_id, None))
