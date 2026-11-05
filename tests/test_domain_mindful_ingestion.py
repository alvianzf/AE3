import unittest
from unittest.mock import MagicMock, patch

from app.clients.llm_client import Role
from app.ingestion import pipeline


class DomainMindfulIngestionTests(unittest.TestCase):
    @patch("app.ingestion.pipeline.get_client")
    def test_read_source_marketing_strips_integrated_medicine_and_caps_grade(self, mock_get_client):
        mock_reader = MagicMock()
        mock_get_client.return_value = mock_reader

        # Simulated response where an LLM mistakenly tagged a marketing brochure with clinical tags
        mock_reader.chat_json.return_value = ({
            "title": "Spring Wellness & Clinic Packages",
            "summary": "Promotional brochure advertising integrated medicine packages and new membership pricing.",
            "topics": ["integrated medicine", "wellness", "promotions"],
            "suggested_grade": 8,
            "author": "Marketing Dept",
            "published": "2026",
            "reference": "",
            "suggested_folder": "Marketing",
            "doc_type": "marketing",
        }, {"total_tokens": 120})

        card = pipeline.read_source(
            text="Spring Wellness Special Offer! Save 20% on our health packages.",
            filename="clinic_marketing_brochure.pdf",
            kind="pdf",
            origin="upload",
            known_topics=["integrated medicine", "hypertension", "diabetes"],
            known_folders=["Marketing", "Protocols"],
        )

        self.assertEqual(card["doc_type"], "marketing")
        # Clinical umbrella tags should be stripped
        self.assertNotIn("integrated medicine", card["topics"])
        self.assertNotIn("wellness", card["topics"])
        # Marketing topic retained or added
        self.assertTrue(any(t in card["topics"] for t in ["marketing", "promotions"]))
        # Reliability grade for marketing must be capped at 3
        self.assertLessEqual(card["suggested_grade"], 3)

    @patch("app.ingestion.pipeline.get_client")
    def test_read_source_clinical_article_retains_valid_topics_and_grade(self, mock_get_client):
        mock_reader = MagicMock()
        mock_get_client.return_value = mock_reader

        mock_reader.chat_json.return_value = ({
            "title": "Management of Hypertension in Primary Care",
            "summary": "Clinical protocol outlining first-line pharmacotherapy for stage 2 hypertension.",
            "topics": ["hypertension", "cardiology", "ace inhibitors"],
            "suggested_grade": 9,
            "author": "Dr. Sarah Smith",
            "published": "2025",
            "reference": "J Clin Hypertens 2025;12:34",
            "suggested_folder": "Cardiology",
            "doc_type": "protocol",
        }, {"total_tokens": 150})

        card = pipeline.read_source(
            text="Stage 2 hypertension protocol with ACE inhibitors and calcium channel blockers.",
            filename="hypertension_protocol.pdf",
            kind="pdf",
            origin="upload",
            known_topics=["hypertension", "cardiology"],
            known_folders=["Cardiology"],
        )

        self.assertEqual(card["doc_type"], "protocol")
        self.assertIn("hypertension", card["topics"])
        self.assertIn("cardiology", card["topics"])
        self.assertEqual(card["suggested_grade"], 9)

    @patch("app.ingestion.pipeline.get_client")
    def test_extract_graph_filters_generic_entities_and_dangling_relationships(self, mock_get_client):
        mock_kg_builder = MagicMock()
        mock_get_client.return_value = mock_kg_builder

        # Simulated response where model extracted generic buzzwords alongside real clinical entities
        mock_kg_builder.chat_json.return_value = ({
            "entities": [
                {"name": "Integrated Medicine", "type": "Procedure"},
                {"name": "Wellness", "type": "Condition"},
                {"name": "Metformin", "type": "Medication"},
                {"name": "Type 2 Diabetes", "type": "Condition"},
                {"name": "Clinic", "type": "Organization"},
            ],
            "relationships": [
                {"head": "Integrated Medicine", "rel_type": "TREATS", "tail": "Wellness"},
                {"head": "Metformin", "rel_type": "TREATS", "tail": "Type 2 Diabetes"},
                {"head": "Clinic", "rel_type": "PROVIDES", "tail": "Integrated Medicine"},
            ],
        }, {"total_tokens": 200})

        result = pipeline.extract_graph("Our clinic offers integrated medicine and metformin for type 2 diabetes.")

        entity_names = [e["name"].lower() for e in result["entities"]]
        self.assertNotIn("integrated medicine", entity_names)
        self.assertNotIn("wellness", entity_names)
        self.assertNotIn("clinic", entity_names)
        self.assertIn("metformin", entity_names)
        self.assertIn("type 2 diabetes", entity_names)

        # Only relationships between surviving entities should remain
        self.assertEqual(len(result["relationships"]), 1)
        rel = result["relationships"][0]
        self.assertEqual(rel["head"], "Metformin")
        self.assertEqual(rel["rel_type"], "TREATS")
        self.assertEqual(rel["tail"], "Type 2 Diabetes")

    @patch("app.ingestion.pipeline.get_client")
    def test_extract_graph_non_clinical_empty_result(self, mock_get_client):
        mock_kg_builder = MagicMock()
        mock_get_client.return_value = mock_kg_builder

        mock_kg_builder.chat_json.return_value = ({
            "entities": [],
            "relationships": [],
        }, {"total_tokens": 50})

        result = pipeline.extract_graph("Call now to book your discovery consultation with our front desk staff!")
        self.assertEqual(result["entities"], [])
        self.assertEqual(result["relationships"], [])
