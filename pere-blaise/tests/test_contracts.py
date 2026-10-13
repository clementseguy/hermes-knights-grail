from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pere_blaise.contracts import canonical_plan_id, fingerprint, parse_manifest
from pere_blaise.scanner import scan
from pere_blaise.service import LocalService
from pere_blaise.router import Command, parse_message
from pere_blaise.planning import manifest_from_proposal, planner_context
from pere_blaise.workflow import analyse
from pere_blaise.store import PlanStore
from pere_blaise.file_delivery import search_documents
from pere_blaise.telegram_gateway import _error_code, _user_error
from pere_blaise.slack_gateway import SlackGateway


def manifest_for(path: Path, destination: str = "À_trier/example.txt") -> dict:
    expected = fingerprint(path)
    return {"version": 2, "actions": [{"source": "example.txt", "destination": destination,
            "expected": expected.as_dict()}]}


class ContractTests(unittest.TestCase):
    def test_manifest_rejects_parent_escape(self) -> None:
        raw = {"version": 2, "actions": [{"source": "../x", "destination": "y", "expected": {"device": 1, "inode": 1, "size": 1, "mtime_ns": 1, "sha256": "a" * 64}}]}
        with self.assertRaises(ValueError):
            parse_manifest(raw)

    def test_manifest_rejects_hidden_paths(self) -> None:
        raw = {"version": 2, "actions": [{"source": ".DS_Store", "destination": "x",
               "expected": {"device": 1, "inode": 1, "size": 1, "mtime_ns": 1, "sha256": "a" * 64}}]}
        with self.assertRaises(ValueError):
            parse_manifest(raw)

    def test_store_claim_is_owner_bound_and_single_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "example.txt"
            source.write_text("safe")
            store = PlanStore(Path(directory) / "plans.sqlite3")
            plan = store.create(owner="123", manifest=manifest_for(source), details={"confidence": "low"})
            self.assertEqual(len(plan["id"].split("-")), 2)
            with self.assertRaises(PermissionError):
                store.claim(plan["id"], "456")
            store.claim(plan["id"], "123")
            with self.assertRaises(ValueError):
                store.claim(plan["id"], "123")

    def test_store_refuses_plan_over_sha256_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "example.txt"
            source.write_text("safe")
            manifest = manifest_for(source)
            manifest["actions"][0]["expected"]["size"] = 11
            store = PlanStore(Path(directory) / "plans.sqlite3", sha256_max_bytes=10)
            with self.assertRaises(ValueError):
                store.create(owner="123", manifest=manifest, details={})

    def test_executor_refuses_changed_source(self) -> None:
        spec = importlib.util.spec_from_file_location("executor", ROOT / "scripts" / "apply-organize-plan-v2.py")
        assert spec and spec.loader
        executor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(executor)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads, documents, quarantine = root / "Downloads", root / "Documents", root / "Quarantine"
            downloads.mkdir(); documents.mkdir()
            source = downloads / "example.txt"; source.write_text("original")
            action = parse_manifest(manifest_for(source))[0]
            source.write_text("changed")
            result = executor._apply_one(action, downloads, documents, quarantine)
            self.assertTrue(result["status"].startswith("failed:"))
            self.assertTrue(source.exists())
            self.assertFalse((documents / "À_trier/example.txt").exists())

    def test_executor_copies_then_quarantines_verified_source(self) -> None:
        spec = importlib.util.spec_from_file_location("executor", ROOT / "scripts" / "apply-organize-plan-v2.py")
        assert spec and spec.loader
        executor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(executor)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads, documents, quarantine = root / "Downloads", root / "Documents", root / "Quarantine"
            downloads.mkdir(); documents.mkdir()
            source = downloads / "example.txt"; source.write_text("original")
            action = parse_manifest(manifest_for(source))[0]
            result = executor._apply_one(action, downloads, documents, quarantine)
            self.assertEqual(result["status"], "applied")
            self.assertEqual((documents / "À_trier/example.txt").read_text(), "original")
            self.assertFalse(source.exists())
            self.assertTrue((quarantine / "example.txt").exists())
            self.assertIn("destination_identity", result)

    def test_scanner_excludes_file_above_hash_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "large.bin").write_bytes(b"01234567890")
            result = scan(root, hash_files=True, sha256_max_bytes=10)
            self.assertEqual(result["files"], [])
            self.assertEqual(result["excluded"][0]["reason"], "sha256_size_ceiling")

    def test_scanner_ignores_hidden_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "visible.pdf").write_text("visible")
            (root / ".DS_Store").write_text("hidden")
            (root / ".localized").write_text("hidden")
            (root / ".private").mkdir()
            (root / ".private" / "nested.pdf").write_text("hidden")
            result = scan(root, hash_files=True, sha256_max_bytes=1024)
            self.assertEqual([item["path"] for item in result["files"]], ["visible.pdf"])

    def test_scanner_excludes_invisible_filename_without_echoing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unsafe = "report\u200c.pdf"
            (root / unsafe).write_text("metadata must not cross the boundary")
            result = scan(root, hash_files=True, sha256_max_bytes=1024)
            self.assertEqual(result["files"], [])
            self.assertEqual(result["excluded"], [{"reason": "unsafe_filename"}])
            with self.assertRaises(ValueError):
                parse_manifest({"version": 2, "actions": [{"source": unsafe, "destination": "x.pdf",
                                "expected": {"device": 1, "inode": 1, "size": 1, "mtime_ns": 1,
                                             "sha256": "a" * 64}}]})

    def test_service_rejects_unlisted_owner_before_plan_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PlanStore(Path(directory) / "plans.sqlite3")
            from pere_blaise.broker import Broker
            service = LocalService(Broker(store, Path("/not-used"), Path(directory) / "run"), {"123"})
            with self.assertRaises(PermissionError):
                service.dispatch({"operation": "create", "owner": "999", "manifest": {}, "details": {}})

    def test_router_accepts_only_exact_privileged_commands(self) -> None:
        self.assertEqual(parse_message("range P-ABC234"), Command("range", "P-ABC234"))
        self.assertEqual(parse_message("range P-ABCDEFG234"), Command("range", "P-ABCDEFG234"))
        self.assertEqual(parse_message("détail p-abcdefg234"), Command("detail", "P-ABCDEFG234"))
        self.assertEqual(parse_message("detail Azuré-Héron"), Command("detail", "azuré-héron"))
        self.assertEqual(parse_message("analyse"), Command("analyse"))
        self.assertEqual(parse_message("apprentissages"), Command("learning"))
        self.assertEqual(parse_message("envoie une attestation"), Command("send", "une attestation"))
        self.assertIsNone(parse_message("envoie-moi une attestation"))
        self.assertIsNone(parse_message("range P-ABCDEFG234; rm -rf /"))
        self.assertIsNone(parse_message("range dernier plan"))

    def test_plan_id_accepts_unicode_normalization_for_two_french_words(self) -> None:
        self.assertEqual(canonical_plan_id("azur\u0065\u0301-he\u0301ron"), "azuré-héron")

    def test_planner_never_receives_document_names_or_hashes(self) -> None:
        inventory = {"downloads": {"files": [{"path": "x.pdf", "size": 2, "extension": ".pdf", "expected": {"sha256": "a" * 64}}]},
                     "documents": {"root": "/Documents", "files": [{"path": "secret/client.pdf"}, {"path": "A/file.pdf"}]}}
        context = planner_context(inventory)
        self.assertNotIn("expected", context["untrusted_downloads"][0])
        self.assertNotIn("secret/client.pdf", str(context))
        manifest = manifest_from_proposal({"actions": [{"source": "x.pdf", "destination": "À_trier/x.pdf"}]}, inventory)
        self.assertEqual(manifest["actions"][0]["expected"]["sha256"], "a" * 64)

    def test_planner_explanatory_fields_are_discarded_before_manifest_creation(self) -> None:
        inventory = {"downloads": {"files": [{"path": "x.pdf", "expected": {
            "device": 1, "inode": 1, "size": 1, "mtime_ns": 1, "sha256": "a" * 64}}]}}
        manifest = manifest_from_proposal({"confidence": "low", "actions": [{
            "source": "x.pdf", "destination": "À_trier/x.pdf", "explanation": "untrusted",
        }]}, inventory)
        self.assertEqual(manifest, {"version": 2, "actions": [{"source": "x.pdf", "destination": "À_trier/x.pdf",
                         "expected": {"device": 1, "inode": 1, "size": 1, "mtime_ns": 1, "sha256": "a" * 64}}]})

    def test_analysis_creates_only_a_proposed_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); (home / "Downloads").mkdir(); (home / "Documents").mkdir()
            (home / "Downloads" / "invoice.pdf").write_text("invoice")
            store = PlanStore(home / "plans.sqlite3")
            broker = __import__("pere_blaise.broker", fromlist=["Broker"]).Broker(store, Path("/not-used"), home / "runtime")
            plan = analyse("123", home, broker,
                           lambda context: {"actions": [{"source": "invoice.pdf", "destination": "À_trier/invoice.pdf"}]},
                           1024)
            self.assertEqual(plan["state"], "proposed")
            self.assertTrue((home / "Downloads" / "invoice.pdf").exists())

    def test_broker_uses_configured_plan_ttl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source.pdf"; source.write_text("x")
            store = PlanStore(root / "plans.sqlite3")
            from pere_blaise.broker import Broker
            broker = Broker(store, Path("/not-used"), root / "run", plan_ttl_hours=1)
            plan = broker.create_plan("123", manifest_for(source), {})
            self.assertIn("+00:00", plan["expires_at"])

    def test_manual_move_from_a_trier_becomes_private_learning_hint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); downloads = home / "Downloads"; documents = home / "Documents"
            downloads.mkdir(); documents.mkdir()
            source = downloads / "facture edf janvier.pdf"; source.write_text("invoice")
            store = PlanStore(home / "plans.sqlite3")
            manifest = manifest_for(source, "a_trier/facture edf janvier.pdf")
            plan = store.create(owner="123", manifest=manifest, details={})
            store.claim(plan["id"], "123")
            staged = documents / "a_trier" / source.name; staged.parent.mkdir(); staged.write_text("invoice")
            info = staged.stat()
            store.finish(plan["id"], {"actions": [{"source": source.name, "destination": "a_trier/" + source.name,
                "status": "applied", "destination_identity": {"device": info.st_dev, "inode": info.st_ino,
                "mtime_ns": info.st_mtime_ns}}]})
            target = documents / "Administratif" / source.name; target.parent.mkdir(); staged.rename(target)
            inventory = {"root": str(documents), "files": scan(documents, hash_files=False, sha256_max_bytes=1024)["files"]}
            result = store.reconcile_a_trier(inventory, documents, 1024)
            self.assertEqual(result, {"learned": 1, "missing": []})
            hints = store.learning_hints([{"path": "facture edf fevrier.pdf", "extension": ".pdf"}])
            self.assertEqual(hints, [{"source": "facture edf fevrier.pdf", "suggested_directory": "Administratif", "evidence_count": 1}])

    def test_missing_a_trier_file_is_reported_then_forgotten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); documents = home / "Documents"; documents.mkdir()
            store = PlanStore(home / "plans.sqlite3")
            with store._connect() as connection:
                connection.execute("""INSERT INTO a_trier_tracking
                    (source_path, source_extension, source_size, source_mtime_ns, source_sha256, a_trier_path, device, inode, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("orphan.pdf", ".pdf", 1, 1, "a" * 64, "a_trier/orphan.pdf", 1, 1, "now"))
            inventory = {"root": str(documents), "files": []}
            self.assertEqual(store.reconcile_a_trier(inventory, documents, 1024),
                             {"learned": 0, "missing": ["a_trier/orphan.pdf"]})
            self.assertEqual(store.reconcile_a_trier(inventory, documents, 1024), {"learned": 0, "missing": []})

    def test_learning_status_is_separate_from_plan_detail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PlanStore(Path(directory) / "plans.sqlite3")
            with store._connect() as connection:
                connection.execute("INSERT INTO learning_events (event_type, source_path, destination, created_at, expires_at) "
                                   "VALUES (?, ?, ?, ?, ?)",
                                   ("learned", "invoice.pdf", "Administratif", "now", "9999-01-01T00:00:00+00:00"))
            status = store.learning_status()
            self.assertEqual(status["pending"], 0)
            self.assertEqual(status["examples"], 0)
            self.assertEqual(status["events"][0]["destination"], "Administratif")

    def test_learning_hints_do_not_expose_historic_document_names(self) -> None:
        inventory = {"downloads": {"files": [{"path": "facture edf.pdf", "size": 2, "extension": ".pdf"}]},
                     "documents": {"root": "/Documents", "files": [], "directories": ["Administratif"]}}
        context = planner_context(inventory, learning_hints=[{"source": "facture edf.pdf",
            "suggested_directory": "Administratif", "evidence_count": 2}])
        self.assertEqual(context["learning_hints"][0]["suggested_directory"], "Administratif")
        self.assertNotIn("ancien document prive.pdf", str(context))

    def test_analysis_refuses_to_call_planner_when_no_download_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); (home / "Downloads").mkdir(); (home / "Documents").mkdir()
            store = PlanStore(home / "plans.sqlite3")
            broker = __import__("pere_blaise.broker", fromlist=["Broker"]).Broker(store, Path("/not-used"), home / "runtime")
            with self.assertRaisesRegex(ValueError, "no eligible downloads"):
                analyse("123", home, broker, lambda context: self.fail("planner must not be called"), 1024)

    def test_analysis_retries_one_invalid_planner_reply_before_creating_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); (home / "Downloads").mkdir(); (home / "Documents").mkdir()
            (home / "Downloads" / "invoice.pdf").write_text("invoice")
            store = PlanStore(home / "plans.sqlite3")
            broker = __import__("pere_blaise.broker", fromlist=["Broker"]).Broker(store, Path("/not-used"), home / "runtime")
            replies = iter([{"confidence": "low"}, {"actions": [{"source": "invoice.pdf", "destination": "À_trier/invoice.pdf"}]}])
            contexts = []
            def planner(context):
                contexts.append(context)
                return next(replies)
            plan = analyse("123", home, broker, planner, 1024)
            self.assertEqual(plan["state"], "proposed")
            self.assertIn("planner_retry_requirement", contexts[1])

    def test_analysis_excludes_existing_destination_before_storing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); (home / "Downloads").mkdir(); (home / "Documents").mkdir()
            (home / "Downloads" / "keep.pdf").write_text("keep")
            (home / "Downloads" / "collision.pdf").write_text("collision")
            (home / "Documents" / "collision.pdf").write_text("already here")
            store = PlanStore(home / "plans.sqlite3")
            broker = __import__("pere_blaise.broker", fromlist=["Broker"]).Broker(store, Path("/not-used"), home / "runtime")
            plan = analyse("123", home, broker, lambda context: {"actions": [
                {"source": "keep.pdf", "destination": "a_trier/keep.pdf"},
                {"source": "collision.pdf", "destination": "collision.pdf"},
            ]}, 1024)
            self.assertEqual([item["source"] for item in plan["manifest"]["actions"]], ["keep.pdf"])
            self.assertEqual(plan["details"]["confidence"], "low")
            self.assertEqual(plan["details"]["excluded"][0]["reason"], "destination_already_exists")

    def test_analysis_excludes_symlinked_destination_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); (home / "Downloads").mkdir(); (home / "Documents").mkdir()
            outside = home / "outside"; outside.mkdir()
            os.symlink(outside, home / "Documents" / "linked")
            (home / "Downloads" / "example.pdf").write_text("content")
            store = PlanStore(home / "plans.sqlite3")
            broker = __import__("pere_blaise.broker", fromlist=["Broker"]).Broker(store, Path("/not-used"), home / "runtime")
            with self.assertRaisesRegex(ValueError, "no proposed action"):
                analyse("123", home, broker, lambda context: {"actions": [
                    {"source": "example.pdf", "destination": "linked/example.pdf"},
                ]}, 1024)

    def test_delivery_search_is_metadata_only_and_skips_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            documents = Path(directory) / "Documents"; documents.mkdir()
            (documents / "Rapport client.pdf").write_text("not read by search")
            outside = Path(directory) / "outside.pdf"; outside.write_text("private")
            os.symlink(outside, documents / "Rapport lien.pdf")
            matches = search_documents(documents, "rapport client")
            self.assertEqual([path.name for path in matches], ["Rapport client.pdf"])

    def test_delivery_search_ignores_french_stop_words(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            documents = Path(directory) / "Documents"; documents.mkdir()
            (documents / "FFTir").mkdir()
            (documents / "FFTir" / "attestation club.pdf").write_text("not read by search")
            matches = search_documents(documents, "une attestation")
            self.assertEqual([path.name for path in matches], ["attestation club.pdf"])

    def test_telegram_log_error_codes_do_not_echo_untrusted_paths(self) -> None:
        self.assertEqual(_error_code(ValueError("source contains control or invisible formatting characters")),
                         "planner_unsafe_path")
        self.assertEqual(_error_code(ValueError("proposal contains unknown source or duplicate destination")),
                         "planner_unknown_source_or_duplicate_destination")
        self.assertEqual(_error_code(ValueError("destination must be a non-empty relative path")),
                         "planner_unsafe_path")
        self.assertEqual(_error_code(ValueError("proposal actions is empty")), "planner_empty_actions")
        self.assertEqual(_user_error(ValueError("plan has expired")),
                         "E-PLAN-EXPIRED — Ce plan a expiré : lance une nouvelle analyse.")

    def test_launchd_renderer_schedules_weekly_analysis_on_sunday_at_18(self) -> None:
        spec = importlib.util.spec_from_file_location("launchd_renderer", ROOT / "scripts" / "render-launchd-plists.py")
        assert spec and spec.loader
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); control = root / "control"; control.mkdir()
            (control / "broker.json").write_text(json.dumps({"telegram_allowed_user_ids": ["123"]}))
            project = root / "project"
            venv_python = project / ".venv/bin/python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("")
            rendered = renderer.render(project, control)
            self.assertNotIn("com.local.pere-blaise-weekly-analysis", rendered)
            rendered = renderer.render(project, control, include_weekly=True)
            weekly = rendered["com.local.pere-blaise-weekly-analysis"]
            self.assertEqual(weekly["StartCalendarInterval"], {"Weekday": 0, "Hour": 18, "Minute": 0})
            self.assertNotIn("--apply", weekly["ProgramArguments"])
            self.assertEqual(weekly["ProgramArguments"][0], str(venv_python))
            self.assertNotIn("com.local.pere-blaise-slack", rendered)
            (control / "slack.env").write_text("SLACK_APP_TOKEN=xapp-test\n")
            with_slack = renderer.render(project, control)
            self.assertEqual(with_slack["com.local.pere-blaise-slack"]["ProgramArguments"][2],
                             "pere_blaise.slack_gateway")

    def test_deployed_compose_keeps_planner_capability_limited(self) -> None:
        compose = (ROOT / "infra/docker/docker-compose.planner.yml").read_text(encoding="utf-8")
        for required in ("container_name: hermes-pere-blaise", "127.0.0.1:8643:8642", ":/opt/data/config.yaml:ro",
                         "external: true", "pids_limit: 128", "cpus: 1.0", "mem_limit: 1536m",
                         "no-new-privileges:true"):
            self.assertIn(required, compose)
        self.assertNotIn("cap_drop:", compose)
        for forbidden in ("/var/run/docker.sock", ":/Users/", ":/home/", ":/root/", "/opt/data/auth.json:ro"):
            self.assertNotIn(forbidden, compose)

    def test_slack_accepts_only_allowlisted_mentions_and_replies_in_thread(self) -> None:
        class FakeSlack:
            def __init__(self): self.replies = []
            def reply(self, channel, thread_ts, text): self.replies.append((channel, thread_ts, text))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); planner = root / "planner.env"; planner.write_text("PERE_BLAISE_API_KEY=x\n")
            config = {"telegram_allowed_user_ids": ["telegram-owner"], "slack_allowed_user_ids": ["U-owner"],
                      "database": str(root / "plans.sqlite3"), "sha256_max_bytes": 1024,
                      "executor": "/not-used", "runtime_dir": str(root / "run"), "socket": str(root / "broker.sock")}
            slack = FakeSlack()
            gateway = SlackGateway(config, slack, ROOT, planner, "C-allowed", {"U-owner"})
            gateway.gateway._learning = lambda owner: "apprentissages pour " + owner
            event = {"type": "events_api", "payload": {"event_id": "Ev-1", "event": {
                "type": "app_mention", "channel": "C-allowed", "user": "U-owner", "ts": "100.1",
                "thread_ts": "100.0", "text": "<@B-bot> apprentissages"}}}
            gateway.handle_envelope(event)
            self.assertEqual(slack.replies, [("C-allowed", "100.0", "apprentissages pour U-owner")])
            gateway.handle_envelope(event)
            gateway.handle_envelope({"type": "events_api", "payload": {"event_id": "Ev-2", "event": {
                "type": "app_mention", "channel": "C-other", "user": "U-owner", "ts": "200.1", "text": "<@B-bot> apprentissages"}}})
            gateway.handle_envelope({"type": "events_api", "payload": {"event_id": "Ev-3", "event": {
                "type": "app_mention", "channel": "C-allowed", "user": "U-other", "ts": "300.1", "text": "<@B-bot> apprentissages"}}})
            self.assertEqual(len(slack.replies), 1)
