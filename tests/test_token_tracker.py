import unittest
from app import token_tracker
from app.clients.llm_client import Role


class TokenTrackerTests(unittest.TestCase):
    def test_record_and_get_models_and_tokens(self):
        token_tracker.record_tokens(Role.REASONER, 500, 150, "test-opus-model")
        token_tracker.record_tokens("reader", 200, 50, "test-sonnet-model")

        data = token_tracker.get_agent_models_and_tokens()
        self.assertIn("agents", data)
        self.assertIn("totals", data)
        self.assertEqual(len(data["agents"]), 6)

        agents_by_role = {a["role"]: a for a in data["agents"]}
        self.assertIn("reasoner", agents_by_role)
        self.assertIn("reader", agents_by_role)
        self.assertIn("graph_builder", agents_by_role)
        self.assertIn("embedder", agents_by_role)
        self.assertIn("answer_engine", agents_by_role)
        self.assertIn("checker_llm", agents_by_role)

        reasoner = agents_by_role["reasoner"]
        self.assertGreater(reasoner["input_tokens"], 0)
        self.assertGreater(reasoner["output_tokens"], 0)
        self.assertGreater(reasoner["total_tokens"], 0)
        self.assertGreater(reasoner["calls"], 0)
        self.assertIn("model", reasoner)
        self.assertIn("provider", reasoner)
        self.assertIn("job", reasoner)

    def test_snapshot_window_and_reset(self):
        token_tracker.record_tokens("reader", 100, 25)
        window = token_tracker.snapshot_window_and_reset()
        self.assertIn("reader", window)
        self.assertGreaterEqual(window["reader"]["input_tokens"], 100)

        # After reset, next window should be empty until new tokens recorded
        empty_window = token_tracker.snapshot_window_and_reset()
        self.assertEqual(empty_window["reader"]["input_tokens"], 0)

    def test_baseline_history_generation(self):
        samples = token_tracker.generate_baseline_history(n_samples=20, interval_s=60)
        self.assertEqual(len(samples), 20)
        s0 = samples[0]
        self.assertIn("ts", s0)
        self.assertIn("load1", s0)
        self.assertIn("mem_used_mb", s0)
        self.assertIn("tokens", s0)
        self.assertIn("total_tokens", s0)
        self.assertIn("reader", s0["tokens"])


if __name__ == "__main__":
    unittest.main()
