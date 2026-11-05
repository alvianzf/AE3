import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import vault
from app.main import app
from app.reasoning import reasoner


class ConsultAiSummaryTests(unittest.TestCase):
    def setUp(self):
        self.practitioner_id = f"test_prac_{uuid.uuid4().hex[:8]}"
        vault.ensure_schema(self.practitioner_id)
        # Create a client
        self.client = vault.create_client(
            self.practitioner_id,
            name="Jane Doe",
            email=f"jane_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
            dob="1985-04-12",
            country="US",
        )
        self.client_id = self.client["id"]

    def test_patient_history_up_to_respects_consultation_point(self):
        t1 = "2026-01-01T10:00:00"
        t2 = "2026-02-01T10:00:00"  # consultation point
        t3 = "2026-03-01T10:00:00"  # after consultation point

        # Add condition at t1
        with vault.vault_connection(self.practitioner_id) as conn:
            conn.execute(
                "INSERT INTO record_entries (id, client_id, kind, content, created_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), self.client_id, "condition", "Hypertension", t1),
            )
            # Add medication at t3 (future)
            conn.execute(
                "INSERT INTO record_entries (id, client_id, kind, content, created_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), self.client_id, "medication", "Lisinopril 10mg", t3),
            )

        # Prior session at t1
        session_1 = vault.create_session(
            self.practitioner_id, self.client_id, "First Consult", started_at=t1
        )
        # Session after t2
        session_future = vault.create_session(
            self.practitioner_id, self.client_id, "Future Consult", started_at=t3
        )

        history_at_t2 = vault.get_patient_history_up_to(
            self.practitioner_id, self.client_id, t2
        )

        self.assertEqual(history_at_t2["client"]["name"], "Jane Doe")
        # Entries up to t2 should have Hypertension, but NOT Lisinopril
        kinds = [e["kind"] for e in history_at_t2["entries"]]
        contents = [e["content"] for e in history_at_t2["entries"]]
        self.assertIn("Hypertension", contents)
        self.assertNotIn("Lisinopril 10mg", contents)

        # Prior sessions should include session_1, but NOT session_future
        prior_ids = [s["id"] for s in history_at_t2["prior_sessions"]]
        self.assertIn(session_1["id"], prior_ids)
        self.assertNotIn(session_future["id"], prior_ids)

    def test_deterministic_consult_intake_summary(self):
        t_now = "2026-05-10T14:30:00"
        with vault.vault_connection(self.practitioner_id) as conn:
            conn.execute(
                "INSERT INTO record_entries (id, client_id, kind, content, created_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), self.client_id, "condition", "Type 2 Diabetes", "2026-01-01T10:00:00"),
            )
            conn.execute(
                "INSERT INTO record_entries (id, client_id, kind, content, created_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), self.client_id, "medication", "Metformin 500mg BID", "2026-01-01T10:00:00"),
            )

        history_data = vault.get_patient_history_up_to(
            self.practitioner_id, self.client_id, t_now
        )
        summary = reasoner.generate_consult_intake_summary(history_data, t_now)

        self.assertIn("## Patient Overview", summary)
        self.assertIn("Jane Doe", summary)
        self.assertIn("## Active Clinical Profile", summary)
        self.assertIn("Type 2 Diabetes", summary)
        self.assertIn("Metformin 500mg BID", summary)
        self.assertIn("## Prior Consultations & Clinical Trajectory", summary)
        self.assertIn("## Consultation Focus & Recommendations", summary)

    def test_api_session_init_and_get(self):
        from app import auth
        test_client = TestClient(app)

        # Mock practitioner auth via FastAPI dependency_overrides
        mock_session = {
            "id": self.practitioner_id,
            "role": "practitioner",
            "tier": "pro",
            "email": "practitioner@example.com",
            "name": "Dr. Smith",
        }

        app.dependency_overrides[auth.require_pro_practitioner] = lambda: mock_session
        try:
            # 1. Initialize session
            resp = test_client.post(
                f"/api/me/clients/{self.client_id}/sessions/init",
            )
            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            session_id = data["id"]
            self.assertIn("initial_summary", data)
            self.assertTrue(len(data["initial_summary"]) > 0)
            self.assertEqual(data["turns"], [])

            # 2. Get session
            get_resp = test_client.get(
                f"/api/me/clients/{self.client_id}/sessions/{session_id}",
            )
            self.assertEqual(get_resp.status_code, 200)
            get_data = get_resp.json()
            self.assertEqual(get_data["id"], session_id)
            self.assertEqual(get_data["initial_summary"], data["initial_summary"])

            # 3. List sessions contains initial_summary
            list_resp = test_client.get(
                f"/api/me/clients/{self.client_id}/sessions",
            )
            self.assertEqual(list_resp.status_code, 200)
            items = list_resp.json()
            found = [s for s in items if s["id"] == session_id]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["initial_summary"], data["initial_summary"])
        finally:
            app.dependency_overrides.pop(auth.require_pro_practitioner, None)


if __name__ == "__main__":
    unittest.main()
