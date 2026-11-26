import unittest
from unittest.mock import MagicMock, patch

from app.patient.context import PatientContext
from app.reasoning import llm_checker, turbo
from app.reasoning.reasoner import ReasonedAnswer


def _patient() -> PatientContext:
    return PatientContext(client_id="c1", name="Test Client", dob=None, country=None)


class ListAccessibleTitlesTests(unittest.TestCase):
    def test_filters_private_documents_without_a_grant(self):
        cards = [
            {"id": "doc-public", "title": "Public Guide", "is_private": False, "folder_path": "", "topics": []},
            {"id": "doc-private-granted", "title": "Granted Private Doc", "is_private": True,
             "folder_path": "", "topics": []},
            {"id": "doc-private-ungranted", "title": "Someone Else's Private Doc", "is_private": True,
             "folder_path": "", "topics": []},
        ]
        with patch("app.reasoning.turbo.store.catalogue", return_value=cards):
            titles = turbo.list_accessible_titles(
                "prac1", min_grade=1, accessible_private_ids={"doc-private-granted"})
        self.assertEqual(set(titles), {"Public Guide", "Granted Private Doc"})

    def test_filters_by_folder_scope(self):
        cards = [
            {"id": "a", "title": "In Scope", "is_private": False, "folder_path": "labs", "topics": []},
            {"id": "b", "title": "Out of Scope", "is_private": False, "folder_path": "imaging", "topics": []},
        ]
        with patch("app.reasoning.turbo.store.catalogue", return_value=cards):
            titles = turbo.list_accessible_titles(
                "prac1", min_grade=1, accessible_private_ids=set(), folder="labs")
        self.assertEqual(titles, ["In Scope"])

    def test_no_titles_returns_empty_list_not_an_error(self):
        with patch("app.reasoning.turbo.store.catalogue", return_value=[]):
            titles = turbo.list_accessible_titles("prac1", min_grade=1, accessible_private_ids=set())
        self.assertEqual(titles, [])


class DraftAnswerStreamingTests(unittest.TestCase):
    def test_forwards_deltas_and_assembles_final_text_and_usage(self):
        fake_client = MagicMock()
        fake_client.chat_text_stream.return_value = iter([
            ("delta", "Ferritin "), ("delta", "looks low."),
            ("done", {"input_tokens": 42, "output_tokens": 7}),
        ])
        with patch("app.reasoning.turbo.get_client", return_value=fake_client):
            events = list(turbo.draft_answer_streaming(
                "What does low ferritin mean?", _patient(), ["Some Library Title"]))

        deltas = [payload for kind, payload in events if kind == "delta"]
        self.assertEqual(deltas, ["Ferritin ", "looks low."])
        final_kind, (text, usage) = events[-1]
        self.assertEqual(final_kind, "done")
        self.assertEqual(text, "Ferritin looks low.")
        self.assertEqual(usage, {"input_tokens": 42, "output_tokens": 7})

    def test_prompt_never_claims_to_have_read_the_titles(self):
        # Not a model-output test (no real call happens) — just confirms
        # the system prompt actually tells the model it hasn't read the
        # titles, the one guarantee this whole feature's safety rests on.
        self.assertIn("have NOT read", turbo.TURBO_DRAFT_SYSTEM)
        self.assertIn("citation markers", turbo.TURBO_DRAFT_SYSTEM)


class TurboVerificationIntegrationTests(unittest.TestCase):
    """Confirms the core integration premise this feature relies on:
    llm_checker.check() (reused completely unmodified) correctly judges a
    turbo-mode draft's sentences against freshly-retrieved evidence, even
    though the draft itself carries no [N] citation markers."""

    def test_unsupported_sentence_is_flagged_even_with_no_citation_markers(self):
        draft = ("Ferritin reflects the body's iron stores. The client should "
                 "immediately start 500mg of a fictional iron compound.")
        citations = [{"text": "Ferritin is a protein that reflects the body's stored iron.",
                     "document_title": "Iron Metabolism Guide", "grade": 8}]
        reasoned = ReasonedAnswer(text=draft, usage={"input_tokens": 1, "output_tokens": 1},
                                  citations=citations)
        with patch("app.reasoning.llm_checker.get_client") as mocked_get_client:
            mocked_get_client.return_value.chat_json.return_value = (
                {"judgments": [
                    {"sentence_index": 0, "supporting_evidence_indices": [0]},
                    {"sentence_index": 1, "supporting_evidence_indices": []},
                ]},
                {"input_tokens": 5, "output_tokens": 5},
            )
            verdict = llm_checker.check("What is ferritin?", reasoned, "Client context: none recorded.")

        self.assertEqual(verdict["verdict"], "weak")
        self.assertIn("The client should immediately start 500mg of a fictional iron compound.",
                      verdict["unsupported"])
        self.assertNotIn("Ferritin reflects the body's iron stores.", verdict["unsupported"])


if __name__ == "__main__":
    unittest.main()
