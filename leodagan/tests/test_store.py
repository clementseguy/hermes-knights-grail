import importlib.util
import tempfile
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location("store", Path(__file__).parents[1] / "plugins/leodagan-editorial/store.py")
store_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store_mod)
Store = store_mod.Store


SOURCE = [{"url": "https://example.org/article", "access_status": "user", "accessed_at": "2026-10-15T20:00:00+00:00",
           "critical_review": {"thesis": "promesse", "evidence": "texte fourni",
               "limits": "non recoupé", "cto_objection": "coût d'exploitation",
               "executive_impact": "valider la réversibilité"}}]


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "editorial.sqlite3"
        self.s = Store(self.path)

    def tearDown(self):
        self.s.db.close()
        self.tmp.cleanup()

    def test_identifier_and_idempotence(self):
        created = self.s.create("Sujet", ["https://example.org/article"], "telegram", "123", "msg1", "café-géant")
        self.assertEqual(created["id"], "café-géant")
        self.assertEqual(self.s.get("CAFE-GEANT")["id"], "café-géant")
        self.assertEqual(self.s.get("cafe\u0301-ge\u0301ant")["id"], "café-géant")
        self.assertTrue(self.s.create("Sujet", ["https://example.org/article"], "telegram", "123", "msg1")["replayed"])
        with self.assertRaises(Exception):
            self.s.create("Sujet", ["https://example.org/article"], "slack", "123", "msg2", "cafe-geant")

    def test_length_versions_atomicity_and_restart(self):
        self.s.create("Sujet", ["https://example.org/article"], "slack", "thread", "msg", "café-géant")
        prompt = "Illustration 16:9, palette froide"
        self.assertEqual(self.s.save("cafe-geant", "a" * 3000, prompt, "raisonnement", SOURCE)["char_count"], 3000)
        with self.assertRaises(ValueError):
            self.s.save("cafe-geant", "a" * 2999 + "😀", prompt, "raisonnement", SOURCE)
        self.assertEqual(self.s.save("cafe-geant", "révisé", prompt, "raisonnement", SOURCE)["version"], 2)
        self.s.db.close()
        self.s = Store(self.path)
        self.assertEqual([v["version"] for v in self.s.get("CAFÉ-GÉANT")["versions"]], [1, 2])

    def test_feedback_rules_and_metrics(self):
        self.s.create("Sujet", ["https://example.org/article"], "slack", "thread", "msg", "café-géant")
        self.s.feedback("cafe-geant", "Publié", "user", "Accroche modifiée",
                        "Préférer une accroche concrète", metrics=[{"type": "REACTION", "value": 5, "origin": "Clément"}])
        self.assertEqual(self.s.get("café-géant")["metrics"][0]["value"], 5)
        self.assertEqual(len(self.s.rules()), 1)
        self.assertTrue(self.s.update_rule(self.s.rules()[0]["id"], "Préférer une accroche vérifiable"))
        self.assertEqual(self.s.rules()[0]["text"], "Préférer une accroche vérifiable")
        self.assertTrue(self.s.revoke_rule(self.s.rules()[0]["id"]))
        self.assertEqual(self.s.rules(), [])
        with self.assertRaises(ValueError):
            self.s.feedback("café-géant", "Publié", "user", "compare", metrics=[{"type": "LIKE", "value": 1, "origin": "x"}])

    def test_incomplete_request_and_source_fail_closed(self):
        for intent, urls in (("", ["https://example.org"]), ("Sujet", []), ("Sujet", ["file:///tmp/private"]),
                             ("Sujet", ["https://127.0.0.1/private"]), ("Sujet", ["https://localhost/private"])):
            with self.assertRaises(ValueError):
                self.s.create(intent, urls, "slack", "thread", "key")
        self.assertEqual(self.s.db.execute("SELECT count(*) FROM drafts").fetchone()[0], 0)
        self.s.create("Sujet", ["https://example.org/article"], "slack", "thread", "key", "café-géant")
        with self.assertRaises(ValueError):
            self.s.save("café-géant", "post", "Image 16:9", "raisonnement", [{"url": "https://example.org/article", "access_status": "inaccessible"}])
        self.assertEqual(self.s.get("café-géant")["versions"], [])
        self.assertEqual(self.s.get("café-géant")["requested_urls"], ["https://example.org/article"])


if __name__ == "__main__":
    unittest.main()
