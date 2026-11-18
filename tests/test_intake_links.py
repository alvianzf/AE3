import unittest
import uuid

from fastapi.testclient import TestClient

from app import auth, core_store, vault
from app.main import app


class QuestionnaireKindTests(unittest.TestCase):
    def setUp(self):
        core_store.ensure_schema()
        # questionnaires.practitioner_id is a real foreign key
        # (REFERENCES practitioners(id)) — a fabricated id 404s on insert,
        # so this needs an actual practitioner row, not just a vault schema.
        practitioner = core_store.create_practitioner_pending(
            email=f"prac_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="fakehash", name="Dr. Test",
        )
        self.practitioner_id = practitioner["id"]
        vault.ensure_schema(self.practitioner_id)

    def test_initial_questionnaire_requires_name_and_email_mapping(self):
        with self.assertRaises(ValueError):
            core_store.create_questionnaire(
                "Intake", [{"prompt": "Your name", "input_type": "text"}],
                self.practitioner_id, practitioner_id=self.practitioner_id, kind="initial",
            )

    def test_initial_questionnaire_with_mapping_succeeds(self):
        q = core_store.create_questionnaire(
            "Intake",
            [
                {"prompt": "Your name", "input_type": "text", "maps_to": "client_name"},
                {"prompt": "Your email", "input_type": "text", "maps_to": "client_email"},
            ],
            self.practitioner_id, practitioner_id=self.practitioner_id, kind="initial",
        )
        self.assertEqual(q["kind"], "initial")
        self.assertEqual(q["questions"][0]["maps_to"], "client_name")

    def test_choice_with_allow_other_round_trips(self):
        q = core_store.create_questionnaire(
            "Diet",
            [{"prompt": "Diet", "input_type": "multi_choice",
              "options": ["vegan", "vegetarian"], "allow_other": True}],
            self.practitioner_id, practitioner_id=self.practitioner_id,
        )
        question = q["questions"][0]
        self.assertEqual(question["options"], ["vegan", "vegetarian"])
        self.assertTrue(question["allow_other"])

    def test_repeater_columns_and_fixed_rows_round_trip(self):
        q = core_store.create_questionnaire(
            "Meds",
            [{"prompt": "Medications", "input_type": "repeater",
              "columns": ["Name", "Dose"], "fixed_rows": None}],
            self.practitioner_id, practitioner_id=self.practitioner_id,
        )
        question = q["questions"][0]
        self.assertEqual(question["columns"], ["Name", "Dose"])
        self.assertIsNone(question["fixed_rows"])


class IntakeLinkApiTests(unittest.TestCase):
    def setUp(self):
        core_store.ensure_schema()
        practitioner = core_store.create_practitioner_pending(
            email=f"prac_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="fakehash", name="Dr. Kreetta Ryödi",
        )
        self.practitioner_id = practitioner["id"]
        vault.ensure_schema(self.practitioner_id)
        self.test_client = TestClient(app)
        self.mock_session = {
            "id": self.practitioner_id, "role": "practitioner", "tier": "pro",
            "email": "practitioner@example.com", "name": "Dr. Kreetta Ryödi",
        }
        app.dependency_overrides[auth.require_pro_practitioner] = lambda: self.mock_session

    def tearDown(self):
        app.dependency_overrides.pop(auth.require_pro_practitioner, None)

    def _create_initial_questionnaire(self):
        resp = self.test_client.post(
            "/api/me/questionnaires",
            json={
                "title": "New client intake",
                "kind": "initial",
                "questions": [
                    {"prompt": "Full name", "input_type": "text", "maps_to": "client_name"},
                    {"prompt": "Email", "input_type": "text", "maps_to": "client_email"},
                    {"prompt": "How are you feeling?", "input_type": "text"},
                ],
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def test_initial_link_full_lifecycle(self):
        questionnaire = self._create_initial_questionnaire()
        name_q, email_q, feel_q = questionnaire["questions"]

        link_resp = self.test_client.post(
            f"/api/me/questionnaires/{questionnaire['id']}/links", json={})
        self.assertEqual(link_resp.status_code, 200, link_resp.text)
        token = link_resp.json()["token"]

        # No auth needed for the public side.
        get_resp = self.test_client.get(f"/api/intake/{token}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["questionnaire"]["id"], questionnaire["id"])

        put_resp = self.test_client.put(
            f"/api/intake/{token}", json={"answers": {feel_q["id"]: "a bit tired"}})
        self.assertEqual(put_resp.status_code, 200)

        resumed = self.test_client.get(f"/api/intake/{token}").json()
        self.assertEqual(resumed["draft_answers"][feel_q["id"]], "a bit tired")

        submit_resp = self.test_client.post(
            f"/api/intake/{token}/submit",
            json={"answers": {
                name_q["id"]: "Mária Šemberová",
                email_q["id"]: f"maria_{uuid.uuid4().hex[:6]}@example.com",
                feel_q["id"]: "a bit tired",
            }},
        )
        self.assertEqual(submit_resp.status_code, 200, submit_resp.text)
        client_id = submit_resp.json()["client_id"]
        self.assertTrue(client_id)

        client = vault.get_client(self.practitioner_id, client_id)
        self.assertEqual(client["name"], "Mária Šemberová")
        self.assertFalse(client["password_set"])

        # The link is one-time: it's gone now, not just re-submittable.
        after_submit = self.test_client.get(f"/api/intake/{token}")
        self.assertEqual(after_submit.status_code, 410)
        resubmit = self.test_client.post(f"/api/intake/{token}/submit", json={"answers": {}})
        self.assertEqual(resubmit.status_code, 410)

    def test_followup_link_requires_existing_client(self):
        q_resp = self.test_client.post(
            "/api/me/questionnaires",
            json={"title": "Check-in", "kind": "followup",
                  "questions": [{"prompt": "How's it going?", "input_type": "text"}]},
        )
        questionnaire = q_resp.json()
        missing = self.test_client.post(
            f"/api/me/questionnaires/{questionnaire['id']}/links", json={})
        self.assertEqual(missing.status_code, 400)

        client = vault.create_client(
            self.practitioner_id, "Jana Kováčová", f"jana_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
        )
        link_resp = self.test_client.post(
            f"/api/me/questionnaires/{questionnaire['id']}/links",
            json={"client_id": client["id"]},
        )
        self.assertEqual(link_resp.status_code, 200, link_resp.text)
        token = link_resp.json()["token"]
        q = self.test_client.get(f"/api/intake/{token}").json()["questionnaire"]
        feel_q = q["questions"][0]

        submit = self.test_client.post(
            f"/api/intake/{token}/submit", json={"answers": {feel_q["id"]: "good"}})
        self.assertEqual(submit.status_code, 200)
        self.assertEqual(submit.json()["client_id"], client["id"])

        response = vault.get_questionnaire_response(self.practitioner_id, client["id"])
        self.assertEqual(response["answers"][feel_q["id"]], "good")

    def test_unknown_token_is_404(self):
        resp = self.test_client.get("/api/intake/not-a-real-token")
        self.assertEqual(resp.status_code, 404)

    def test_upload_link_lifecycle(self):
        client = vault.create_client(
            self.practitioner_id, "Eva Horváthová", f"eva_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash",
        )
        link_resp = self.test_client.post(f"/api/me/clients/{client['id']}/upload-links")
        self.assertEqual(link_resp.status_code, 200, link_resp.text)
        token = link_resp.json()["token"]

        upload_resp = self.test_client.post(
            f"/api/intake/{token}/upload",
            files={"file": ("labs.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")},
        )
        self.assertEqual(upload_resp.status_code, 200, upload_resp.text)

        files = vault.list_uploaded_files(self.practitioner_id, client["id"])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["original_name"], "labs.pdf")

        done_resp = self.test_client.post(f"/api/intake/{token}/submit", json={})
        self.assertEqual(done_resp.status_code, 200)
        self.assertEqual(self.test_client.get(f"/api/intake/{token}").status_code, 410)


if __name__ == "__main__":
    unittest.main()
