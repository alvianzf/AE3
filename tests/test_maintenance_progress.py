import json
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app import auth
from app.main import app, _current_maintenance


class MaintenanceProgressTests(unittest.TestCase):
    def setUp(self):
        # Override auth dependency to simulate superadmin caller
        app.dependency_overrides[auth.require_admin] = lambda: {
            "id": "admin_test",
            "role": "admin",
            "admin_role": "superadmin",
            "username": "superadmin_test",
        }
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_maintenance_status_empty(self):
        res = self.client.get("/api/maintenance/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data.get("active"))

    @patch("app.main.store")
    @patch("app.main.ingestion_pipeline")
    def test_relink_stream(self, mock_pipeline, mock_store):
        mock_store.unlinked_documents.return_value = [
            {"id": "doc1", "title": "Doc 1"},
            {"id": "doc2", "title": "Doc 2"},
        ]
        mock_store.document_text.side_effect = lambda doc_id: {
            "id": doc_id,
            "passages": [{"text": "Sample passage for extraction"}]
        }
        mock_store.graph_stats.return_value = {"entities": 10, "relationships": 15}
        mock_store.link_document.return_value = 3
        mock_pipeline.extract_graph.return_value = {
            "entities": [{"name": "Metformin", "type": "Medication"}],
            "relationships": []
        }

        res = self.client.post("/api/relink?stream=true")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers.get("content-type", ""))

        # Parse SSE stream frames
        lines = res.text.strip().split("\n\n")
        events = []
        for frame in lines:
            if not frame.strip():
                continue
            line = [l for l in frame.split("\n") if l.startswith("data: ")][0]
            events.append(json.loads(line[6:]))

        self.assertGreaterEqual(len(events), 3)
        self.assertEqual(events[0]["event"], "start")
        self.assertEqual(events[0]["kind"], "relink")

        # Check that progress events were emitted with percentages
        progress_events = [e for e in events if e.get("event") == "progress"]
        self.assertGreaterEqual(len(progress_events), 1)
        for pe in progress_events:
            self.assertIn("percentage", pe)
            self.assertIn("detail", pe)

        # Check final done event
        done_event = events[-1]
        self.assertEqual(done_event["event"], "done")
        self.assertEqual(done_event["percentage"], 100)
        self.assertEqual(len(done_event["result"]["linked"]), 2)

    @patch("app.main.store")
    @patch("app.main.ingestion_pipeline")
    def test_relink_sync_fallback(self, mock_pipeline, mock_store):
        mock_store.unlinked_documents.return_value = [
            {"id": "doc1", "title": "Doc 1"}
        ]
        mock_store.document_text.return_value = {
            "id": "doc1",
            "passages": [{"text": "Sample text"}]
        }
        mock_store.graph_stats.return_value = {"entities": 5, "relationships": 8}
        mock_store.link_document.return_value = 2
        mock_pipeline.extract_graph.return_value = {
            "entities": [],
            "relationships": []
        }

        res = self.client.post("/api/relink")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("linked", data)
        self.assertEqual(len(data["linked"]), 1)
        self.assertEqual(data["linked"][0]["title"], "Doc 1")

    @patch("app.main.store")
    @patch("app.main.ingestion_pipeline")
    def test_consolidate_stream(self, mock_pipeline, mock_store):
        mock_store.all_entities.return_value = [
            {"name": "Diabetes"},
            {"name": "Type 2 Diabetes"},
            {"name": "Metformin"},
        ]
        mock_store.graph_stats.return_value = {"entities": 2, "relationships": 4}
        mock_store.merge_entities.return_value = 1
        mock_pipeline.suggest_entity_merges.return_value = [
            {"canonical": "type 2 diabetes", "aliases": ["diabetes"]}
        ]

        res = self.client.post("/api/consolidate?stream=true")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers.get("content-type", ""))

        lines = res.text.strip().split("\n\n")
        events = [json.loads([l for l in frame.split("\n") if l.startswith("data: ")][0][6:]) for frame in lines if frame.strip()]

        self.assertGreaterEqual(len(events), 4)
        self.assertEqual(events[0]["event"], "start")
        self.assertEqual(events[-1]["event"], "done")
        self.assertEqual(events[-1]["result"]["entity"]["absorbed"], 1)

    def test_stop_maintenance(self):
        res = self.client.post("/api/maintenance/stop")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "stopping"})
