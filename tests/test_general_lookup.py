import unittest
from unittest.mock import patch

from app.patient.context import PatientContext
from app.retrieval import general_lookup


def _patient() -> PatientContext:
    return PatientContext(client_id="c1", name="Test Client", dob=None, country=None)


class GeneralLookupTests(unittest.TestCase):
    """Found live, 2026-11-27: embedding a short/vague question directly
    (the original design) returned chunks from completely unrelated
    documents — not just "less thorough" than deep_research, but useless.
    general_lookup now forms a real search query first (the same cheap
    call deep_research's seed stage already pays for), same as
    seed_search.seed() already does."""

    def test_forms_a_search_query_before_embedding(self):
        with patch("app.retrieval.general_lookup.form_search_query",
                  return_value=("athletic performance sports medicine data",
                               {"input_tokens": 10, "output_tokens": 5})) as mocked_form_query, \
            patch("app.retrieval.general_lookup.get_client") as mocked_get_client, \
            patch("app.retrieval.general_lookup.search", return_value=[]) as mocked_search:
            mocked_get_client.return_value.embed.return_value = [[0.1, 0.2, 0.3]]

            result = general_lookup.lookup("data for athletes", _patient(), min_grade=1)

        mocked_form_query.assert_called_once()
        called_question = mocked_form_query.call_args[0][0]
        self.assertEqual(called_question, "data for athletes")
        # The formed query, not the raw question, is what gets embedded.
        embed_input = mocked_get_client.return_value.embed.call_args[0][0][0]
        self.assertIn("athletic performance sports medicine data", embed_input)
        self.assertEqual(result.usage, {"input_tokens": 10, "output_tokens": 5})
        mocked_search.assert_called_once()

    def test_accumulated_results_sorted_by_grade_descending(self):
        rows = [
            {"id": "a", "text": "low", "document_title": "D1", "document_id": "d1",
             "grade": 3, "page_start": 1, "page_end": 1},
            {"id": "b", "text": "high", "document_title": "D2", "document_id": "d2",
             "grade": 9, "page_start": 1, "page_end": 1},
        ]
        with patch("app.retrieval.general_lookup.form_search_query",
                  return_value=("q", {"input_tokens": 0, "output_tokens": 0})), \
            patch("app.retrieval.general_lookup.get_client") as mocked_get_client, \
            patch("app.retrieval.general_lookup.search", return_value=rows):
            mocked_get_client.return_value.embed.return_value = [[0.1]]

            result = general_lookup.lookup("q", _patient(), min_grade=1)

        self.assertEqual([c["grade"] for c in result.accumulated], [9, 3])


if __name__ == "__main__":
    unittest.main()
