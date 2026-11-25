import unittest
import uuid
from unittest.mock import patch

from app import vault
from app.reasoning import clinical_state
from app.reasoning.reasoner import format_deterministic_consult_summary


class ClinicalStateTests(unittest.TestCase):
    def setUp(self):
        self.practitioner_id = f"test_prac_{uuid.uuid4().hex[:8]}"
        vault.ensure_schema(self.practitioner_id)
        self.client_rec = vault.create_client(
            self.practitioner_id, name="Test Patient",
            email=f"patient_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="fakehash", dob="1990-01-01", country="US",
        )
        self.client_id = self.client_rec["id"]
        self.entry = vault.add_entry(
            self.practitioner_id, self.client_id, "lab", "Ferritin 17.7 ug/L (ref 10-291)")

    def test_upsert_sets_prior_row_valid_to_and_computes_trend(self):
        first = vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="Ferritin", value="17.7",
            unit="ug/L", reference_range="10-291", flag="low",
            source_entry_id=self.entry["id"],
        )
        self.assertIsNone(first["trend"])
        self.assertIsNone(first["valid_to"])

        second_entry = vault.add_entry(
            self.practitioner_id, self.client_id, "lab", "Ferritin 8.1 ug/L (ref 10-291)")
        second = vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="Ferritin", value="8.1",
            unit="ug/L", reference_range="10-291", flag="low",
            source_entry_id=second_entry["id"],
        )
        self.assertEqual(second["trend"], "falling")

        current = vault.get_clinical_state(self.practitioner_id, self.client_id)
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["value"], "8.1")

    def test_trend_stable_within_tolerance(self):
        vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="TSH", value="2.24",
            unit="mIU/l", reference_range="0.35-5.10", flag="in_range",
            source_entry_id=self.entry["id"],
        )
        updated = vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="TSH", value="2.26",
            unit="mIU/l", reference_range="0.35-5.10", flag="in_range",
            source_entry_id=self.entry["id"],
        )
        self.assertEqual(updated["trend"], "stable")

    def test_label_normalization_tracks_same_marker_across_wording(self):
        vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="Serum Ferritin", value="17.7",
            unit="ug/L", reference_range="10-291", flag="low",
            source_entry_id=self.entry["id"],
        )
        vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="Ferritin", value="8.1",
            unit="ug/L", reference_range="10-291", flag="low",
            source_entry_id=self.entry["id"],
        )
        current = vault.get_clinical_state(self.practitioner_id, self.client_id)
        self.assertEqual(len(current), 1, "differently-worded labels for the same "
                         "marker must resolve to one tracked row, not two")

    def test_get_clinical_state_excludes_superseded_rows(self):
        vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="Ferritin", value="17.7",
            unit="ug/L", reference_range="10-291", flag="low",
            source_entry_id=self.entry["id"],
        )
        vault.upsert_clinical_state_marker(
            self.practitioner_id, self.client_id, label="Ferritin", value="8.1",
            unit="ug/L", reference_range="10-291", flag="low",
            source_entry_id=self.entry["id"],
        )
        current = vault.get_clinical_state(self.practitioner_id, self.client_id)
        values = {m["value"] for m in current}
        self.assertEqual(values, {"8.1"})

    def test_update_lab_state_writes_one_row_per_extracted_marker(self):
        with patch("app.reasoning.clinical_state.extract_lab_markers") as mocked:
            mocked.return_value = ([
                {"label": "Ferritin", "value": "17.7", "unit": "ug/L",
                 "reference_range": "10-291", "flag": "low"},
                {"label": "TSH", "value": "2.24", "unit": "mIU/l",
                 "reference_range": "0.35-5.10", "flag": "in_range"},
            ], {"input_tokens": 10, "output_tokens": 5})
            clinical_state.update_lab_state(self.practitioner_id, self.client_id, self.entry)

        current = vault.get_clinical_state(self.practitioner_id, self.client_id)
        self.assertEqual({m["label"] for m in current}, {"ferritin", "thyroid stimulating hormone"})

    def test_update_lab_state_swallows_extraction_failure(self):
        with patch("app.reasoning.clinical_state.extract_lab_markers",
                   side_effect=RuntimeError("provider down")):
            clinical_state.update_lab_state(self.practitioner_id, self.client_id, self.entry)
        # Must not raise, and must leave no partial state behind.
        self.assertEqual(vault.get_clinical_state(self.practitioner_id, self.client_id), [])

    def test_summary_includes_lab_state_section_when_present(self):
        history_data = {
            "client": {"name": "Test Patient"}, "entries": [], "intake_notes": [],
            "questionnaire": None, "prior_sessions": [],
            "lab_state": [{"display_label": "Ferritin", "value": "8.1", "unit": "ug/L",
                          "flag": "low", "trend": "falling"}],
        }
        summary = format_deterministic_consult_summary(history_data, "2026-11-25T00:00:00")
        self.assertIn("Tracked Lab Marker Trends", summary)
        self.assertIn("Ferritin: 8.1 ug/L [LOW], trending falling", summary)

    def test_summary_omits_lab_state_section_when_absent(self):
        history_data = {
            "client": {"name": "Test Patient"}, "entries": [], "intake_notes": [],
            "questionnaire": None, "prior_sessions": [], "lab_state": [],
        }
        summary = format_deterministic_consult_summary(history_data, "2026-11-25T00:00:00")
        self.assertNotIn("Tracked Lab Marker Trends", summary)


if __name__ == "__main__":
    unittest.main()
