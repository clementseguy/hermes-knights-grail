"""Telegram ingress for the isolated broker; commands remain deterministic."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import stat
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .file_delivery import search_documents
from .file_ingress import open_download, safe_filename, save_attachment
from .hermes_client import planner_request
from .router import Command, parse_message
from .workflow import analyse
from .broker import Broker
from .ingress_ledger import IngressLedger
from .store import PlanStore

HELP = ("Commandes : analyse, détaille <ID>, range <ID>, envoie <nom>. "
        "Pour déposer dans Downloads : écrivez « tiens », puis envoyez un seul document dans ce chat privé. "
        "Vous pouvez aussi mettre « tiens » dans la légende du document.")
RECEIVE_WINDOW_SEC = 5 * 60


def _env_value(path: Path, key: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            value = line.split("=", 1)[1]
            if value:
                return value
    raise ValueError("missing " + key)


class Telegram:
    def __init__(self, token: str) -> None:
        self.token = token
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

    def document(self, chat_id: str, path: Path, content: bytes) -> None:
        """Upload bytes read and identity-checked by the local broker."""
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

    def download(self, file_id: str, declared_size: int):
        if not isinstance(file_id, str) or not file_id or len(file_id) > 512:
            raise ValueError('PB-RECEIVE-FAILED')
        details = self.call('getFile', {'file_id': file_id})
        if not isinstance(details, dict) or (details.get('file_size') is not None and details['file_size'] != declared_size):
            raise ValueError('PB-RECEIVE-FAILED')
        path = details.get('file_path')
        if (not isinstance(path, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', path) or
                path.startswith('/') or any(part in ('.', '..') for part in path.split('/'))):
            raise ValueError('PB-RECEIVE-FAILED')
        return open_download('https://api.telegram.org/file/bot' + self.token + '/' + path,
                             'api.telegram.org')


def _user_error(exc: Exception, *, stage: str = 'command') -> str:
    from .errors import classify, user_message
    return user_message(classify(exc, stage=stage), stage=stage, exc=exc)


class Gateway:
    def __init__(self, config: dict[str, Any], telegram: Telegram | None, project: Path, planner_env: Path) -> None:
        self.config, self.telegram, self.project, self.planner_env = config, telegram, project, planner_env
        self.allowed = set(map(str, config.get('telegram_allowed_user_ids', [])))
        self.pending: dict[tuple[str, str], list[tuple[Path, tuple[int, int, int, int]]]] = {}
        # A short, process-local intent prevents an unrelated attachment from
        # becoming a command. It is lost on restart, so no stale grant survives.
        self.receive_pending_until: dict[str, float] = {}
        self.broker = Broker(PlanStore(Path(config['database']), sha256_max_bytes=int(config['sha256_max_bytes'])),
                             runtime_dir=Path(config['runtime_dir']), downloads=Path(config['downloads']),
                             documents=Path(config['documents']), backups=Path(config['backups']),
                             max_files=int(config.get('max_files', 1000)),
                             max_directories=int(config.get('max_directories', 500)))

    def owner(self, platform: str, user_id: str) -> str:
        principal = f'{platform}:{user_id}'
        return self.config.get('identity_map', {}).get(principal, principal)

    def _analyse(self, owner: str) -> str:
        prompt = (self.project / 'prompts' / 'organizer-planner.md').read_text(encoding='utf-8')
        api_key = _env_value(self.planner_env, 'PERE_BLAISE_API_KEY')
        endpoint = self.config.get('planner_endpoint', 'http://pere-blaise:8642')
        if endpoint != 'http://pere-blaise:8642':
            raise ValueError('PB-PLAN-INVALID')
        deadline = time.monotonic() + int(self.config.get('analysis_timeout_sec', 120))
        def propose(context):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('PB-MODEL-UNAVAILABLE')
            return planner_request(endpoint, api_key, self.config.get('planner_model', 'hermes-agent'),
                                   prompt, context, timeout=max(1, int(remaining)))
        plan = analyse(owner, Path(self.config['downloads']).parent, self.broker,
                       propose,
                       int(self.config['sha256_max_bytes']))
        return (f"Je propose le plan {plan['id']} pour {len(plan['manifest']['actions'])} fichiers ; "
                f"confiance {plan['details']['confidence']}. Validité jusqu'à {plan['expires_at']}. "
                f"Commandes : détaille {plan['id']} ; range {plan['id']}.")

    def _detail(self, owner: str, plan_id: str) -> str:
        plan = self.broker.detail(owner, plan_id)
        d = plan['details']
        lines = [f"Plan {plan_id} — confiance {d['confidence']} ; {d['a_trier_count']}/{len(d['actions'])} vers a_trier ({d['a_trier_percent']:.2f} %)."]
        lines += [f"• Downloads/{a['source']} → Documents/{a['destination']} — {a['reason']} ({a['certainty']})" for a in d['actions']]
        lines.append(f"Expire : {plan['expires_at']}. Accord final : range {plan_id}.")
        return '\n'.join(lines)

    def _apply(self, owner: str, plan_id: str) -> str:
        result = self.broker.apply(owner, plan_id)
        state = result['state']
        if state == 'APPLIED':
            return f"Plan {plan_id} appliqué : {len(result['actions'])} fichier(s) classé(s), backups conservés."
        code = result.get('code') or ('PB-ROLLBACK-BLOCKED' if state == 'BLOCKED_RECOVERY' else 'PB-APPLY-FAILED')
        return f"{code} — Plan {plan_id} : {state} ; incident {result['incident']}."

    def _send(self, owner: str, query: str, deliver, context: str = '') -> str:
        from .file_delivery import identity, validate_selection, read_document_bytes
        documents = Path(self.config['documents'])
        matches = search_documents(documents, query)
        if not matches:
            from .errors import user_message
            return user_message('PB-SEND-NOTFOUND', stage='send')
        if len(matches) > 1:
            self.pending[(owner, context)] = [(p, identity(p)) for p in matches]
            from .errors import incident
            identifier = incident('PB-SEND-AMBIGUOUS', stage='send')
            return f'PB-SEND-AMBIGUOUS — Choisir un numéro ; incident {identifier} :\n' + '\n'.join(
                f'{i}. {p.relative_to(documents)}' for i, p in enumerate(matches, 1))
        expected = identity(matches[0])
        p = validate_selection(documents, matches[0], expected, int(self.config['send_max_bytes']))
        content = read_document_bytes(documents, p, int(self.config['send_max_bytes']), expected)
        try:
            deliver(p, content)
        except (TimeoutError, OSError) as exc:
            raise ValueError('PB-SEND-UNCERTAIN') from exc
        return f'Fichier envoyé : {p.name}'

    def select(self, owner: str, number: str, deliver, context: str = '') -> str:
        from .file_delivery import validate_selection, read_document_bytes
        pending = self.pending.get((owner, context))
        if pending is None or not number.isdecimal() or not 1 <= int(number) <= len(pending):
            raise ValueError('PB-SEND-AMBIGUOUS')
        path, expected = pending[int(number) - 1]
        del self.pending[(owner, context)]
        path = validate_selection(Path(self.config['documents']), path, expected, int(self.config['send_max_bytes']))
        content = read_document_bytes(Path(self.config['documents']), path, int(self.config['send_max_bytes']), expected)
        try:
            deliver(path, content)
        except (TimeoutError, OSError) as exc:
            raise ValueError('PB-SEND-UNCERTAIN') from exc
        return f'Fichier envoyé : {path.name}'

    def dispatch(self, command: Command, owner: str, deliver=None, context: str = '') -> str:
        if command.name == 'analyse': return self._analyse(owner)
        if command.name == 'detail': return self._detail(owner, command.argument)
        if command.name == 'range': return self._apply(owner, command.argument)
        if command.name == 'send': return self._send(owner, command.argument, deliver, context)
        if command.name == 'receive': raise ValueError('PB-RECEIVE-FILE')
        raise ValueError('PB-PLAN-INVALID')

    def receive_file(self, platform: str, sender: str, filename: object, size: object, stream) -> str:
        authorized = str(self.config.get(platform + '_receive_user_id', ''))
        allowed = (self.allowed if platform == 'telegram' else
                   set(map(str, self.config.get('slack_allowed_user_ids', []))))
        if not authorized or sender != authorized or sender not in allowed:
            raise PermissionError('receive owner mismatch')
        limit = int(self.config.get('receive_max_bytes', 10 * 1024 * 1024))
        with self.broker.operation_lock():
            name = save_attachment(Path(self.config['downloads']), filename, size, stream, limit)
        return f'Fichier déposé dans Downloads : {name}'

    def handle(self, message: dict[str, Any]) -> None:
        sender = str(message.get('from', {}).get('id', ''))
        chat = message.get('chat', {})
        chat_id = str(chat.get('id', ''))
        if self.telegram is None or sender not in self.allowed or chat.get('type') != 'private' or chat_id != sender:
            return
        owner = self.owner('telegram', sender)
        attachment = message.get('document')
        value = str(message.get('caption' if attachment is not None else 'text', '')).strip()
        receive_owner = sender == str(self.config.get('telegram_receive_user_id', ''))
        try:
            if attachment is not None:
                pending_until = self.receive_pending_until.pop(sender, 0)
                requested = value.casefold() == 'tiens' or (not value and pending_until > time.monotonic())
                if not receive_owner:
                    return
                if not requested:
                    raise ValueError('PB-RECEIVE-FILE')
                if not isinstance(attachment, dict):
                    raise ValueError('PB-RECEIVE-FILE')
                size, filename = attachment.get('file_size'), attachment.get('file_name')
                safe_filename(filename)
                if not isinstance(size, int) or size < 0 or size > int(self.config.get('receive_max_bytes', 10 * 1024 * 1024)):
                    raise ValueError('PB-RECEIVE-LIMIT')
                with self.telegram.download(attachment.get('file_id'), size) as stream:
                    response = self.receive_file('telegram', sender, filename, size, stream)
            elif value.casefold() == 'tiens':
                if not receive_owner:
                    return
                self.receive_pending_until[sender] = time.monotonic() + RECEIVE_WINDOW_SEC
                response = 'Réception préparée : envoyez maintenant un seul document dans ce chat privé, sous 5 minutes.'
            elif value.isdecimal():
                self.receive_pending_until.pop(sender, None)
                response = self.select(owner, value, lambda path, content: self.telegram.document(chat_id, path, content), 'telegram:' + chat_id)
            else:
                self.receive_pending_until.pop(sender, None)
                command = parse_message(value)
                if command and command.name in ('analyse', 'range', 'send'):
                    self.telegram.message(chat_id, 'Opération en cours ; résultat à suivre dans ce chat.')
                response = self.dispatch(command, owner, lambda path, content: self.telegram.document(chat_id, path, content), 'telegram:' + chat_id) if command else HELP
        except Exception as exc:
            response = _user_error(exc, stage='receive' if value.casefold() == 'tiens' else command.name if 'command' in locals() and command else 'command')
        self.telegram.message(chat_id, response)


def process_updates(updates: Any, gateway: Gateway, ledger: IngressLedger, offset: int) -> int:
    """Mark before dispatch; a crashed delivery is never replayed automatically."""
    for update in updates if isinstance(updates, list) else []:
        event_id = update.get('update_id') if isinstance(update, dict) else None
        if not isinstance(event_id, int):
            continue
        if ledger.begin('telegram', str(event_id)):
            try:
                if isinstance(update.get('message'), dict):
                    gateway.handle(update['message'])
                ledger.complete('telegram', str(event_id))
            except Exception as exc:
                from .errors import incident
                incident('PB-CHANNEL-FAILED', stage='telegram-ingress', exc=exc)
        offset = max(offset, event_id + 1)
    return offset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--broker-config', type=Path, required=True)
    parser.add_argument('--telegram-env', type=Path, required=True)
    parser.add_argument('--planner-env', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.broker_config.read_text())
    telegram = Telegram(_env_value(args.telegram_env, 'TELEGRAM_BOT_TOKEN'))
    gateway = Gateway(config, telegram, Path(__file__).resolve().parents[2], args.planner_env)
    state = Path(config['runtime_dir'])
    ledger = IngressLedger(state, int(config.get('retention_days', 30)))
    legacy_offset = state / 'telegram-offset'
    offset = int(legacy_offset.read_text()) if legacy_offset.exists() else 0
    while True:
        try:
            updates = telegram.call('getUpdates', {'offset': offset, 'timeout': 30, 'allowed_updates': json.dumps(['message'])})
            offset = process_updates(updates, gateway, ledger, offset)
        except KeyboardInterrupt:
            return 0
        except Exception:
            time.sleep(5)

if __name__ == '__main__':
    raise SystemExit(main())
