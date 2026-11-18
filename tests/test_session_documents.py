import json
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import vault
from app.main import app


class SessionDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.practitioner_id = f"test_prac_{uuid.uuid4().hex[:8]}"
        vault.ensure_schema(self.practitioner_id)
        self.client_rec = vault.create_client(
            self.practitioner_id,
            name="Mária Šemberová",
            email=f"maria_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            dob="1975-08-28",
            country="SK",
        )
        self.client_id = self.client_rec["id"]
        self.session = vault.create_session(
            self.practitioner_id, self.client_id, "DUTCH Plus review",
            started_at="2026-02-08T10:40:00",
        )
        self.session_id = self.session["id"]

    def test_save_and_get_document_round_trip(self):
        saved = vault.save_document(
            self.practitioner_id, self.session_id, self.client_id,
            "clinician_note", "<p>Subjective: fatigue.</p>", "draft",
        )
        self.assertEqual(saved["status"], "draft")
        fetched = vault.get_document(self.practitioner_id, self.session_id, "clinician_note")
        self.assertEqual(fetched["content"], "<p>Subjective: fatigue.</p>")

    def test_save_document_upserts_on_same_kind(self):
        vault.save_document(
            self.practitioner_id, self.session_id, self.client_id,
            "clinician_note", "<p>first</p>", "draft",
        )
        vault.save_document(
            self.practitioner_id, self.session_id, self.client_id,
            "clinician_note", "<p>second</p>", "final",
        )
        fetched = vault.get_document(self.practitioner_id, self.session_id, "clinician_note")
        self.assertEqual(fetched["content"], "<p>second</p>")
        self.assertEqual(fetched["status"], "final")

    def test_save_document_rejects_unknown_kind_or_status(self):
        with self.assertRaises(ValueError):
            vault.save_document(
                self.practitioner_id, self.session_id, self.client_id,
                "not_a_kind", "<p>x</p>",
            )
        with self.assertRaises(ValueError):
            vault.save_document(
                self.practitioner_id, self.session_id, self.client_id,
                "clinician_note", "<p>x</p>", status="not_a_status",
            )

    def test_list_documents_across_sessions(self):
        vault.save_document(
            self.practitioner_id, self.session_id, self.client_id,
            "client_report", "<p>report</p>", "draft",
        )
        rows = vault.list_documents(self.practitioner_id, self.client_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "client_report")
        self.assertEqual(rows[0]["session_title"], "DUTCH Plus review")

    def test_save_and_get_asset(self):
        asset = vault.save_asset(
            self.practitioner_id, self.session_id, self.client_id,
            "asset-1", "asset.png",
        )
        self.assertEqual(asset["id"], "asset-1")
        fetched = vault.get_asset(self.practitioner_id, self.session_id, "asset-1")
        self.assertEqual(fetched["filename"], "asset.png")


class SessionDocumentsApiTests(unittest.TestCase):
    def setUp(self):
        self.practitioner_id = f"test_prac_{uuid.uuid4().hex[:8]}"
        vault.ensure_schema(self.practitioner_id)
        self.client_rec = vault.create_client(
            self.practitioner_id,
            name="Mária Šemberová",
            email=f"maria_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
        )
        self.client_id = self.client_rec["id"]
        self.test_client = TestClient(app)

        from app import auth
        self.mock_session = {
            "id": self.practitioner_id, "role": "practitioner", "tier": "pro",
            "email": "practitioner@example.com", "name": "Dr. Kreetta Ryödi",
        }
        self.auth = auth
        app.dependency_overrides[auth.require_pro_practitioner] = lambda: self.mock_session

    def tearDown(self):
        app.dependency_overrides.pop(self.auth.require_pro_practitioner, None)

    def test_save_then_get_session_returns_document(self):
        init = self.test_client.post(f"/api/me/clients/{self.client_id}/sessions/init")
        self.assertEqual(init.status_code, 200, init.text)
        session_id = init.json()["id"]

        put_resp = self.test_client.put(
            f"/api/me/clients/{self.client_id}/sessions/{session_id}/documents/clinician_note",
            json={"content": "<p>Plan: progesterone 100mg.</p>", "status": "draft"},
        )
        self.assertEqual(put_resp.status_code, 200, put_resp.text)

        get_resp = self.test_client.get(f"/api/me/clients/{self.client_id}/sessions/{session_id}")
        self.assertEqual(get_resp.status_code, 200)
        documents = get_resp.json()["documents"]
        self.assertEqual(documents["clinician_note"]["content"], "<p>Plan: progesterone 100mg.</p>")
        self.assertIsNone(documents["client_report"])

    def test_save_document_rejects_unknown_kind(self):
        init = self.test_client.post(f"/api/me/clients/{self.client_id}/sessions/init")
        session_id = init.json()["id"]
        resp = self.test_client.put(
            f"/api/me/clients/{self.client_id}/sessions/{session_id}/documents/not_a_kind",
            json={"content": "<p>x</p>"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_draft_endpoint_streams_result_from_mocked_reasoner(self):
        init = self.test_client.post(f"/api/me/clients/{self.client_id}/sessions/init")
        session_id = init.json()["id"]

        with patch("app.reasoning.reasoner.generate_session_document") as mocked, \
                patch("app.reasoning.llm_checker.check") as mocked_check:
            mocked.return_value = (
                "## Subjective\nPatient reports fatigue. [K1]",
                {"input_tokens": 10, "output_tokens": 5},
                [{"document_id": "doc-1", "title": "Lab Report", "snippet": "fatigue noted",
                  "locator": "p.1", "kind": "chunk"}],
            )
            mocked_check.return_value = {
                "verdict": "pass", "unsupported": [], "note": "Everything checked out.",
                "usage": {"input_tokens": 3, "output_tokens": 2},
            }
            with self.test_client.stream(
                "POST",
                f"/api/me/clients/{self.client_id}/sessions/{session_id}/documents/clinician_note/draft",
                json={},
            ) as resp:
                self.assertEqual(resp.status_code, 200)
                body = "".join(resp.iter_text())
        self.assertIn('"event": "result"', body)
        self.assertIn("Patient reports fatigue", body)

        # Deliberately not persisted by this endpoint — see its docstring:
        # the client resolves citations to HTML first, then saves through
        # the normal PUT endpoint, same as any manual edit.
        saved = vault.get_document(self.practitioner_id, session_id, "clinician_note")
        self.assertIsNone(saved)

    def test_draft_endpoint_strips_sentences_the_checker_flags(self):
        init = self.test_client.post(f"/api/me/clients/{self.client_id}/sessions/init")
        session_id = init.json()["id"]

        with patch("app.reasoning.reasoner.generate_session_document") as mocked, \
                patch("app.reasoning.llm_checker.check") as mocked_check:
            mocked.return_value = (
                "## Plan\nStart progesterone 100mg daily. Patient has three cats.",
                {"input_tokens": 10, "output_tokens": 5}, [],
            )
            mocked_check.return_value = {
                "verdict": "weak", "unsupported": ["Patient has three cats."],
                "note": "1 sentence not supported.", "usage": {"input_tokens": 3, "output_tokens": 2},
            }
            with self.test_client.stream(
                "POST",
                f"/api/me/clients/{self.client_id}/sessions/{session_id}/documents/clinician_note/draft",
                json={},
            ) as resp:
                body = "".join(resp.iter_text())
        # The "result" frame's own `text` field is what actually lands in
        # the editor — assert against that specifically, not the whole raw
        # SSE body, since `check.unsupported` in that same frame legitimately
        # echoes the stripped sentence back (that's what powers the
        # frontend's "N sentences removed" toast, not a leftover bug).
        result_line = next(line for line in body.splitlines() if '"event": "result"' in line)
        result = json.loads(result_line[len("data: "):])
        self.assertIn("Start progesterone 100mg daily.", result["text"])
        self.assertNotIn("three cats", result["text"])
        self.assertIn("Patient has three cats.", result["check"]["unsupported"])


if __name__ == "__main__":
    unittest.main()
