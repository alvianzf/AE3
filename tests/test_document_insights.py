import json
import unittest
import uuid
from unittest.mock import patch

from app import vault
from app.reasoning import document_insights


class DocumentInsightsTests(unittest.TestCase):
    def setUp(self):
        self.practitioner_id = f"test_prac_{uuid.uuid4().hex[:8]}"
        vault.ensure_schema(self.practitioner_id)
        self.client_rec = vault.create_client(
            self.practitioner_id, name="Test Client",
            email=f"client_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash", dob="1990-01-01", country="US",
        )
        self.client_id = self.client_rec["id"]
        self.file_row = vault.save_uploaded_file(
            self.practitioner_id, self.client_id, "referral.pdf", "application/pdf",
            "/tmp/does-not-matter.pdf", extracted_text="Referral to endocrinology for thyroid nodule.",
            extraction_status="done", category="document",
        )

    def test_classify_document_writes_insights(self):
        with patch("app.reasoning.document_insights.get_client") as mocked_get_client:
            mocked_get_client.return_value.chat_json.return_value = (
                {
                    "doc_type": "referral",
                    "summary": "A referral to endocrinology for a thyroid nodule.",
                    "highlights": [{"text": "Thyroid nodule noted", "severity": "flag"}],
                },
                {"input_tokens": 10, "output_tokens": 5},
            )
            document_insights.classify_document(
                self.practitioner_id, self.client_id, self.file_row["id"],
                "Referral to endocrinology for thyroid nodule.", "referral.pdf",
            )

        updated = vault.get_uploaded_file(self.practitioner_id, self.file_row["id"])
        self.assertEqual(updated["ai_doc_type"], "referral")
        self.assertEqual(updated["ai_summary"], "A referral to endocrinology for a thyroid nodule.")
        self.assertEqual(json.loads(updated["ai_highlights_json"]),
                         [{"text": "Thyroid nodule noted", "severity": "flag"}])
        self.assertIsNotNone(updated["ai_classified_at"])

    def test_classify_document_swallows_failure(self):
        with patch("app.reasoning.document_insights.get_client",
                   side_effect=RuntimeError("provider down")):
            document_insights.classify_document(
                self.practitioner_id, self.client_id, self.file_row["id"],
                "Referral to endocrinology for thyroid nodule.", "referral.pdf",
            )
        # Must not raise, and must leave the file's AI fields untouched (NULL).
        updated = vault.get_uploaded_file(self.practitioner_id, self.file_row["id"])
        self.assertIsNone(updated["ai_doc_type"])


class ClientRecordTests(unittest.TestCase):
    def setUp(self):
        self.practitioner_id = f"test_prac_{uuid.uuid4().hex[:8]}"
        vault.ensure_schema(self.practitioner_id)
        self.client_rec = vault.create_client(
            self.practitioner_id, name="Test Client",
            email=f"client_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash", dob="1990-01-01", country="US",
        )
        self.client_id = self.client_rec["id"]

    def test_document_entry_links_to_file_with_ai_insights(self):
        file_row = vault.save_uploaded_file(
            self.practitioner_id, self.client_id, "labs.pdf", "application/pdf",
            "/tmp/does-not-matter.pdf", extracted_text="Ferritin 8.1 ug/L",
            extraction_status="done", category="document",
        )
        doc_entry = vault.add_entry(self.practitioner_id, self.client_id, "document",
                                    "labs.pdf: Ferritin 8.1 ug/L")
        vault.link_uploaded_file_to_entry(self.practitioner_id, file_row["id"], doc_entry["id"])
        vault.save_document_insights(
            self.practitioner_id, file_row["id"], doc_type="lab_result",
            summary="A ferritin result.", highlights=[{"text": "Low ferritin", "severity": "flag"}],
        )

        record = vault.get_client_record(self.practitioner_id, self.client_id)
        self.assertEqual(len(record["entries"]), 1)
        entry = record["entries"][0]
        self.assertEqual(entry["kind"], "document")
        self.assertEqual(entry["file"]["ai_doc_type"], "lab_result")
        self.assertEqual(entry["file"]["ai_summary"], "A ferritin result.")
        self.assertEqual(entry["file"]["ai_highlights"], [{"text": "Low ferritin", "severity": "flag"}])

    def test_manual_entry_has_no_file(self):
        vault.add_entry(self.practitioner_id, self.client_id, "condition", "Hypothyroidism")
        record = vault.get_client_record(self.practitioner_id, self.client_id)
        self.assertEqual(len(record["entries"]), 1)
        self.assertNotIn("file", record["entries"][0])

    def test_record_includes_current_clinical_state(self):
        entry = vault.add_entry(self.practitioner_id, self.client_id, "lab", "Ferritin 8.1 ug/L")
        vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="Ferritin", value="8.1",
            unit="ug/L", reference_range="10-291", flag="low", source_entry_id=entry["id"],
        )
        record = vault.get_client_record(self.practitioner_id, self.client_id)
        self.assertEqual(len(record["clinical_state"]), 1)
        self.assertEqual(record["clinical_state"][0]["label"], "ferritin")

    def test_deleting_document_entry_deletes_the_file(self):
        file_row = vault.save_uploaded_file(
            self.practitioner_id, self.client_id, "note.pdf", "application/pdf",
            "/tmp/does-not-matter.pdf", extracted_text="Some clinical note.",
            extraction_status="done", category="document",
        )
        doc_entry = vault.add_entry(self.practitioner_id, self.client_id, "document", "note.pdf: Some clinical note.")
        vault.link_uploaded_file_to_entry(self.practitioner_id, file_row["id"], doc_entry["id"])

        self.assertTrue(vault.delete_entry(self.practitioner_id, self.client_id, doc_entry["id"]))
        self.assertIsNone(vault.get_uploaded_file(self.practitioner_id, file_row["id"]))


if __name__ == "__main__":
    unittest.main()
