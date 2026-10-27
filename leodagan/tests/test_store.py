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
APPROVAL = {"verdict": "approve", "required_changes": [],
            **{role: {"finding": "contrôle satisfaisant", "severity": "ok"}
               for role in ("dsi", "cto", "rssi", "ceo", "source_check", "voice_check")}}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "editorial.sqlite3"
        self.s = Store(self.path)

    def tearDown(self):
        self.s.db.close()
        self.tmp.cleanup()

    def approved(self, post="post", sources=SOURCE):
        review = self.s.prepare_review("cafe-geant", post, "Illustration 16:9", "raisonnement", sources)
        self.s.complete_review(review["review_id"], APPROVAL, "openai-codex", "gpt-5.6-terra")
        return review["review_id"]

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
        with self.assertRaises(ValueError):
            self.s.save("cafe-geant", 999)
        self.assertEqual(self.s.save("cafe-geant", self.approved("a" * 3000))["char_count"], 3000)
        with self.assertRaises(ValueError):
            self.s.prepare_review("cafe-geant", "a" * 2999 + "😀", "Illustration 16:9", "raisonnement", SOURCE)
        with self.assertRaises(ValueError):
            self.s.save("cafe-geant", 1)
        self.assertEqual(self.s.save("cafe-geant", self.approved("révisé"))["version"], 2)
        self.s.db.close()
        self.s = Store(self.path)
        self.assertEqual([v["version"] for v in self.s.get("CAFÉ-GÉANT")["versions"]], [1, 2])
        self.assertEqual([r["status"] for r in self.s.get("CAFÉ-GÉANT")["reviews"]], ["APPROVED", "APPROVED"])

    def test_new_source_redirect_and_review_gate(self):
        self.s.create("Sujet", ["https://example.org/article"], "slack", "thread", "msg", "café-géant")
        new_url = "https://news.example.org/short"
        self.assertTrue(self.s.add_source("cafe-geant", new_url)["added"])
        self.assertFalse(self.s.add_source("cafe-geant", new_url)["added"])
        with self.assertRaises(ValueError):
            self.s.prepare_review("cafe-geant", "post", "Image 16:9", "raisonnement", SOURCE)
        sources = SOURCE + [{**SOURCE[0], "url": new_url, "final_url": "https://news.example.org/article"}]
        review = self.s.prepare_review("cafe-geant", "post", "Image 16:9", "raisonnement", sources)
        blocked = {**APPROVAL, "verdict": "revise", "required_changes": ["Citer la limite"]}
        self.assertEqual(self.s.complete_review(review["review_id"], blocked, "openai-codex", "gpt-5.6-terra")["status"], "CHANGES_REQUIRED")
        with self.assertRaises(ValueError):
            self.s.save("cafe-geant", review["review_id"])
        approved = self.approved("post corrigé", sources)
        self.assertEqual(self.s.save("cafe-geant", approved)["version"], 1)
        self.assertEqual(len(self.s.get("cafe-geant")["source_events"]), 2)
        self.assertEqual(self.s.get("cafe-geant")["versions"][0]["sources"][1]["final_url"], "https://news.example.org/article")

    def test_stale_review_cannot_save_after_other_version(self):
        self.s.create("Sujet", ["https://example.org/article"], "slack", "thread", "msg", "café-géant")
        first = self.approved("premier")
        stale = self.approved("périmé")
        self.s.save("cafe-geant", first)
        with self.assertRaises(ValueError):
            self.s.save("cafe-geant", stale)

    def test_voice_review_is_required_and_can_block_delivery(self):
        self.s.create("Sujet", ["https://example.org/article"], "slack", "thread", "msg", "café-géant")
        missing = {k: v for k, v in APPROVAL.items() if k != "voice_check"}
        review = self.s.prepare_review("cafe-geant", "Un post", "Image 16:9", "raisonnement", SOURCE)
        with self.assertRaisesRegex(ValueError, "incomplet"):
            self.s.complete_review(review["review_id"], missing, "openai-codex", "gpt-5.6-terra")
        blocked = {**APPROVAL, "voice_check": {"finding": "Résumé générique sans arbitrage", "severity": "blocking"}}
        self.assertEqual(self.s.complete_review(review["review_id"], blocked, "openai-codex", "gpt-5.6-terra")["status"], "CHANGES_REQUIRED")
        with self.assertRaises(ValueError):
            self.s.save("cafe-geant", review["review_id"])

    def test_existing_v1_draft_migrates_without_losing_sources(self):
        self.s.db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,?,?)",
                          ("café-géant", "cafe-geant", "Sujet", "slack", "thread", "slack:thread:msg", "SAVED", "2026-10-15T20:00:00+00:00"))
        self.s.db.execute("INSERT INTO requested_sources VALUES(?,?)", ("café-géant", SOURCE[0]["url"]))
        self.s.db.execute("DELETE FROM source_events")
        self.s.db.execute("PRAGMA user_version=1")
        self.s.db.close()
        self.s = Store(self.path)
        draft = self.s.get("cafe-geant")
        self.assertEqual(draft["source_events"][0]["url"], SOURCE[0]["url"])
        self.assertEqual(self.s.db.execute("PRAGMA user_version").fetchone()[0], 2)

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
            self.s.prepare_review("café-géant", "post", "Image 16:9", "raisonnement", [{"url": "https://example.org/article", "access_status": "inaccessible"}])
        self.assertEqual(self.s.get("café-géant")["versions"], [])
        self.assertEqual(self.s.get("café-géant")["requested_urls"], ["https://example.org/article"])


if __name__ == "__main__":
    unittest.main()
