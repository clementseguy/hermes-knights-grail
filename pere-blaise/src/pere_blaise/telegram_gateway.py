"""Single-bot Telegram ingress, deliberately limited to the Hermes file workflow.

This is a host process.  It has no terminal, browser, code tool, Docker socket or
model-controlled command execution.  The only privileged broker request is an
owner-bound plan ID received after strict parsing.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import stat
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .file_delivery import search_documents
from .hermes_client import planner_request
from .router import Command, parse_message
from .socket_client import request as broker_request
from .workflow import analyse
from .broker import Broker
from .store import PlanStore


def _env_value(path: Path, key: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            value = line.split("=", 1)[1]
            if value:
                return value
    raise ValueError("missing " + key)


class Telegram:
    def __init__(self, token: str) -> None:
        self.base = "https://api.telegram.org/bot" + token + "/"

    def call(self, method: str, fields: dict[str, Any] | None = None) -> Any:
        data = urlencode(fields or {}).encode("utf-8")
        request = Request(self.base + method, data=data, method="POST")
        with urlopen(request, timeout=90) as response:  # nosec: fixed Telegram API origin
            payload = json.load(response)
        if not isinstance(payload, dict) or not payload.get("ok"):
            raise ValueError("Telegram API rejected request")
        return payload.get("result")

    def message(self, chat_id: str, text: str) -> None:
        while text:
            end = min(len(text), 4000)
            if end < len(text):
                newline = text.rfind("\n", 0, end)
                if newline > 0:
                    end = newline + 1
            self.call("sendMessage", {"chat_id": chat_id, "text": text[:end]})
            text = text[end:]

    def document(self, chat_id: str, path: Path) -> None:
        """Upload the exact regular file selected by the read-only lookup.

        Open by descriptor with O_NOFOLLOW so replacing a path with a symlink after
        the search cannot cause another file to be exfiltrated.
        """
        initial = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(initial.st_mode) or initial.st_size > 50 * 1024 * 1024:
            raise ValueError("document is not eligible for delivery")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (initial.st_dev, initial.st_ino):
                raise ValueError("document changed before delivery")
            with os.fdopen(descriptor, "rb", closefd=False) as source:
                content = source.read()
        finally:
            os.close(descriptor)
        boundary = "----hermes-" + uuid.uuid4().hex
        filename = path.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        prefix = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        suffix = f"\r\n--{boundary}--\r\n".encode("utf-8")
        body = prefix + content + suffix
        request = Request(self.base + "sendDocument", data=body,
                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
        with urlopen(request, timeout=180) as response:  # nosec: fixed Telegram API origin
            payload = json.load(response)
        if not isinstance(payload, dict) or not payload.get("ok"):
            raise ValueError("Telegram refused the document")


def _error_code(exc: Exception) -> str:
    """Classify local failures for logs without echoing user-controlled data."""
    if not isinstance(exc, ValueError):
        return "internal_failure"
    message = str(exc)
    if message == "planner did not return one JSON proposal":
        return "planner_invalid_json"
    if message == "proposal is not an object":
        return "planner_not_object"
    if message == "proposal is missing actions":
        return "planner_missing_actions"
    if message == "proposal actions is not a list":
        return "planner_actions_not_list"
    if message == "proposal actions is empty":
        return "planner_empty_actions"
    if message == "no eligible downloads visible to this process":
        return "no_eligible_downloads_visible"
    if message.startswith("proposal action"):
        return "planner_invalid_schema"
    if message == "proposal contains unknown source or duplicate destination":
        return "planner_unknown_source_or_duplicate_destination"
    if ("must remain below its allowed root" in message or "control or invisible formatting" in message
            or message.endswith("must be a non-empty relative path")):
        return "planner_unsafe_path"
    if message == "no proposed action passed destination preflight":
        return "all_destinations_rejected"
    if message == "unknown plan":
        return "plan_unknown"
    if message == "plan has expired":
        return "plan_expired"
    if message == "plan is no longer applicable":
        return "plan_already_used"
    if message.startswith("document") or message == "Telegram refused the document":
        return "document_delivery_rejected"
    if message.startswith("missing "):
        return "local_configuration_missing"
    return "local_validation_rejected"


def _user_error(exc: Exception) -> str:
    code = _error_code(exc)
    messages = {
        "planner_invalid_json": "Le planificateur a répondu dans un format invalide. Réessaie l’analyse.",
        "planner_not_object": "Le planificateur n’a pas renvoyé un objet de plan.",
        "planner_missing_actions": "Le planificateur n’a fourni aucune liste d’actions.",
        "planner_actions_not_list": "La liste d’actions du planificateur est invalide.",
        "planner_empty_actions": "Le planificateur n’a proposé aucune action.",
        "no_eligible_downloads_visible": "Le service ne voit aucun téléchargement éligible. Vérifie les autorisations macOS de Python/launchd.",
        "planner_invalid_schema": "Le planificateur a proposé un plan incomplet. Réessaie l’analyse.",
        "planner_unknown_source_or_duplicate_destination": "Le plan proposé ne correspond plus à l’inventaire local. Réessaie l’analyse.",
        "planner_unsafe_path": "Le plan contient un nom ou chemin non sûr ; il a été refusé.",
        "all_destinations_rejected": "Toutes les destinations proposées existent déjà ou sont non sûres.",
        "plan_unknown": "Cet identifiant de plan est introuvable.",
        "plan_expired": "Ce plan a expiré : lance une nouvelle analyse.",
        "plan_already_used": "Ce plan a déjà été appliqué ou consommé.",
        "document_delivery_rejected": "Le fichier a changé, est trop grand ou Telegram a refusé l’envoi.",
        "local_configuration_missing": "La configuration locale requise est incomplète.",
        "local_validation_rejected": "La validation locale a refusé cette action.",
        "internal_failure": "Erreur locale inattendue ; aucun fichier n’a été déplacé.",
    }
    return f"E-{code.upper().replace('_', '-')} — {messages[code]}"


class Gateway:
    def __init__(self, config: dict[str, Any], telegram: Telegram | None, project: Path, planner_env: Path) -> None:
        self.config, self.telegram, self.project, self.planner_env = config, telegram, project, planner_env
        self.allowed = set(map(str, config["telegram_allowed_user_ids"]))
        self.pending: dict[str, list[Path]] = {}

    def _analyse(self, owner: str) -> str:
        prompt = (self.project / "prompts" / "organizer-planner.md").read_text(encoding="utf-8")
        api_key = _env_value(self.planner_env, "PERE_BLAISE_API_KEY")
        broker = Broker(PlanStore(Path(self.config["database"]), sha256_max_bytes=int(self.config["sha256_max_bytes"])),
                        Path(self.config["executor"]), Path(self.config["runtime_dir"]),
                        plan_ttl_hours=int(self.config["plan_ttl_hours"]))
        plan = analyse(owner, Path.home(), broker,
                       lambda context: planner_request("http://127.0.0.1:8643", api_key, "hermes-agent", prompt, context),
                       int(self.config["sha256_max_bytes"]))
        details = plan["details"]
        actions = details["actions"]
        excerpt = "\n".join(f"• {item['source']} → {item['destination']}" for item in actions[:8])
        more = f"\n… et {len(actions) - 8} autre(s)." if len(actions) > 8 else ""
        return (f"Plan {plan['id']} — confiance {details['confidence']} — {len(actions)} action(s).\n"
                f"{excerpt}{more}\nExpire à {plan['expires_at']}.\n"
                f"Détail : détail {plan['id']}\nApplication : range {plan['id']}")

    def _detail(self, owner: str, plan_id: str) -> str:
        plan = broker_request(Path(self.config["socket"]), {"operation": "detail", "owner": owner, "plan_id": plan_id})
        details = plan["details"]
        lines = [f"Plan {plan_id} — {plan['state']} — confiance {details['confidence']}."]
        lines.extend(f"• {item['source']} → {item['destination']}" for item in details["actions"])
        if details["ambiguities"]:
            lines.append(f"Ambiguïtés : {len(details['ambiguities'])} vers a_trier.")
        if details["excluded"]:
            lines.append(f"Éléments exclus : {len(details['excluded'])}.")
        for item in details.get("organization_review", []):
            lines.append(f"Organisation — {item['title']} : {item['recommendation']}")
        return "\n".join(lines)

    def _learning(self, owner: str) -> str:
        status = broker_request(Path(self.config["socket"]), {"operation": "learning", "owner": owner})
        lines = [f"Apprentissages : {status['examples']} exemple(s) actif(s) sur 3 mois.",
                 f"En attente dans a_trier : {status['pending']} fichier(s)."]
        for event in status["events"]:
            if event["type"] == "learned":
                lines.append(f"• Retenu : {event['source']} → {event['destination']}")
            else:
                lines.append(f"• Oublié : {event['source']} (sorti de Documents ou supprimé)")
        return "\n".join(lines)

    def _apply(self, owner: str, plan_id: str) -> str:
        result = broker_request(Path(self.config["socket"]), {"operation": "apply", "owner": owner, "plan_id": plan_id})
        actions = result.get("actions", [])
        applied = sum(item.get("status") == "applied" for item in actions)
        failed = len(actions) - applied
        return f"Plan {plan_id} traité : {applied} classé(s), {applied} original(aux) en quarantaine, {failed} ignoré(s) ou en erreur."

    def _send(self, owner: str, chat_id: str, query: str) -> str:
        if self.telegram is None:
            raise ValueError("document delivery is unavailable on this channel")
        matches = search_documents(Path.home() / "Documents", query)
        if not matches:
            return "Aucun fichier correspondant dans Documents."
        if len(matches) == 1:
            self.telegram.document(chat_id, matches[0])
            return f"Fichier envoyé : {matches[0].name}"
        self.pending[owner] = matches
        choices = "\n".join(f"{index}. {path.relative_to(Path.home() / 'Documents')}" for index, path in enumerate(matches, 1))
        return "Plusieurs fichiers correspondent. Réponds avec le numéro :\n" + choices

    def handle(self, message: dict[str, Any]) -> None:
        if self.telegram is None:
            raise RuntimeError("Telegram transport is required")
        sender = str(message.get("from", {}).get("id", ""))
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        if sender not in self.allowed or chat.get("type") != "private" or chat_id != sender:
            return
        text = message.get("text")
        if not isinstance(text, str):
            self.telegram.message(chat_id, "Texte attendu : analyse, apprentissages, détail <id>, range <id> ou envoie <fichier>.")
            return
        normalized = " ".join(text.strip().split())
        if normalized.isdigit() and sender in self.pending:
            options = self.pending.pop(sender)
            index = int(normalized) - 1
            if 0 <= index < len(options):
                self.telegram.document(chat_id, options[index])
                self.telegram.message(chat_id, f"Fichier envoyé : {options[index].name}")
                return
        command = parse_message(text)
        if command is None:
            self.telegram.message(chat_id, "Commandes : analyse · apprentissages · détail <id> · range <id> · envoie <fichier>.")
            return
        try:
            response = self._dispatch(command, sender, chat_id)
        except Exception as exc:
            # Telegram must not receive local paths, planner output or secrets.  Keep
            # the operational diagnosis local and deliberately metadata-only.
            print(f"telegram command rejected: command={command.name} error_type={type(exc).__name__} "
                  f"error_code={_error_code(exc)}", file=sys.stderr,
                  flush=True)
            response = _user_error(exc)
        self.telegram.message(chat_id, response)

    def _dispatch(self, command: Command, owner: str, chat_id: str) -> str:
        if command.name == "analyse":
            return self._analyse(owner)
        if command.name == "learning":
            return self._learning(owner)
        if command.name == "detail":
            return self._detail(owner, command.argument)
        if command.name == "range":
            return self._apply(owner, command.argument)
        if command.name == "send":
            return self._send(owner, chat_id, command.argument)
        raise ValueError("unsupported command")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-config", type=Path, required=True)
    parser.add_argument("--telegram-env", type=Path, required=True)
    parser.add_argument("--planner-env", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--poll-timeout", type=int, default=30)
    parser.add_argument("--discard-pending", action="store_true",
                        help="record and skip pending Telegram updates, then exit")
    args = parser.parse_args()
    config = json.loads(args.broker_config.read_text(encoding="utf-8"))
    gateway = Gateway(config, Telegram(_env_value(args.telegram_env, "TELEGRAM_BOT_TOKEN")),
                      Path(__file__).resolve().parents[2], args.planner_env)
    offset = int(args.state.read_text(encoding="utf-8")) if args.state.exists() else 0
    args.state.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if args.discard_pending:
        discarded = 0
        while True:
            updates = gateway.telegram.call("getUpdates", {"offset": offset, "timeout": 0,
                                                            "allowed_updates": json.dumps(["message"])})
            if not isinstance(updates, list) or not updates:
                break
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = max(offset, update_id + 1)
                    discarded += 1
            args.state.write_text(str(offset), encoding="utf-8")
            args.state.chmod(0o600)
        print(f"Ignored {discarded} pending Telegram update(s).")
        return 0
    while True:
        try:
            updates = gateway.telegram.call("getUpdates", {"offset": offset, "timeout": args.poll_timeout,
                                                               "allowed_updates": json.dumps(["message"])})
            for update in updates if isinstance(updates, list) else []:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                    args.state.write_text(str(offset), encoding="utf-8")
                    args.state.chmod(0o600)
                message = update.get("message")
                if isinstance(message, dict):
                    gateway.handle(message)
        except KeyboardInterrupt:
            return 0
        except Exception:
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
