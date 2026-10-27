import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace


root = Path(__file__).parents[1] / "plugins/leodagan-editorial"
spec = importlib.util.spec_from_file_location("review", root / "review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class FakeLLM:
    def __init__(self):
        self.kwargs = None

    def complete(self, **kwargs):
        self.kwargs = kwargs
        report = {"verdict": "approve", "required_changes": [],
                  **{role: {"finding": "ok", "severity": "ok"}
                     for role in ("dsi", "cto", "rssi", "ceo", "source_check", "voice_check")}}
        return SimpleNamespace(text=json.dumps(report), provider="openai-codex", model="gpt-5.6-terra")


class ReviewTests(unittest.TestCase):
    def test_fresh_context_and_pinned_provider(self):
        llm = FakeLLM()
        report, provider, model = review.review_candidate(llm, {"post": "Un texte", "sources": []})
        self.assertEqual((provider, model), ("openai-codex", "gpt-5.6-terra"))
        self.assertEqual(report["verdict"], "approve")
        self.assertEqual([m["role"] for m in llm.kwargs["messages"]], ["system", "user"])
        self.assertEqual(llm.kwargs["provider"], "openai-codex")
        self.assertEqual(llm.kwargs["model"], "gpt-5.6-terra")
        self.assertIn("RSSI", llm.kwargs["messages"][0]["content"])
        self.assertIn("voice_check", llm.kwargs["messages"][0]["content"])

    def test_rejects_unexpected_provider(self):
        class Other(FakeLLM):
            def complete(self, **kwargs):
                result = super().complete(**kwargs)
                result.provider = "other"
                return result
        with self.assertRaises(RuntimeError):
            review.review_candidate(Other(), {"post": "Un texte", "sources": []})


if __name__ == "__main__":
    unittest.main()
