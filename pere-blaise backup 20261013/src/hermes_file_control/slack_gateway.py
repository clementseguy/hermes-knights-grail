"""Socket Mode ingress for the dedicated, allowlisted Père Blaise Slack app.

The process acknowledges Slack envelopes before doing work, then accepts only an
``app_mention`` from the configured private channel and configured owner IDs.
It has no shell, filesystem path or Docker capability: privileged work remains
behind the same local Unix-socket broker as Telegram.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.request import Request, urlopen

from .router import parse_message
from .telegram_gateway import Gateway, _env_value, _error_code, _user_error


HELP = "Commandes : analyse · apprentissages · détail <id> · range <id>."
SLACK_SEND_UNAVAILABLE = "L’envoi de fichiers reste disponible sur Telegram uniquement."


def _csv(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}


class Slack:
    """Minimal fixed-origin Slack Web API client; API errors are never echoed."""

    def __init__(self, bot_token: str, app_token: str) -> None:
        self.bot_token, self.app_token = bot_token, app_token

    def call(self, method: str, payload: dict[str, Any], *, app_token: bool = False) -> dict[str, Any]:
        token = self.app_token if app_token else self.bot_token
        request = Request(
            "https://slack.com/api/" + method,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:  # nosec: fixed Slack API origin
            result = json.load(response)
        if not isinstance(result, dict) or not result.get("ok"):
            raise ValueError("Slack API rejected request")
        return result

    def socket_url(self) -> str:
        value = self.call("apps.connections.open", {}, app_token=True).get("url")
        if not isinstance(value, str) or not value.startswith("wss://"):
            raise ValueError("Slack API returned invalid socket URL")
        return value

    def reply(self, channel: str, thread_ts: str, text: str) -> None:
        while text:
            part, text = text[:3900], text[3900:]
            self.call("chat.postMessage", {"channel": channel, "thread_ts": thread_ts, "text": part})


class SlackGateway:
    def __init__(self, config: dict[str, Any], slack: Slack, project: Path, planner_env: Path, channel: str, users: set[str]) -> None:
        if not channel or not users:
            raise ValueError("Slack allowlists are required")
        self.gateway = Gateway(config, None, project, planner_env)
        self.slack, self.channel, self.users = slack, channel, users
        self._event_ids: set[str] = set()
        self._event_order: deque[str] = deque(maxlen=2048)

    def _seen(self, event_id: object) -> bool:
        if not isinstance(event_id, str) or not event_id:
            return False
        if event_id in self._event_ids:
            return True
        if len(self._event_order) == self._event_order.maxlen:
            self._event_ids.discard(self._event_order.popleft())
        self._event_order.append(event_id)
        self._event_ids.add(event_id)
        return False

    @staticmethod
    def _command_text(text: object) -> str | None:
        if not isinstance(text, str):
            return None
        match = re.fullmatch(r"<@[^>]+>\s*(.*)", text.strip(), flags=re.DOTALL)
        if match is None:
            return None
        # Slack clients may append presentation metadata after the first line;
        # commands themselves are deliberately single-line and exact.
        return match.group(1).splitlines()[0].strip()

    def handle_envelope(self, envelope: dict[str, Any]) -> None:
        """Process one already-acknowledged Socket Mode envelope."""
        if envelope.get("type") != "events_api":
            return
        payload = envelope.get("payload")
        if not isinstance(payload, dict) or self._seen(payload.get("event_id")):
            return
        event = payload.get("event")
        if not isinstance(event, dict) or event.get("type") != "app_mention":
            return
        channel, sender, timestamp = event.get("channel"), event.get("user"), event.get("ts")
        if channel != self.channel or not isinstance(sender, str) or sender not in self.users or not isinstance(timestamp, str):
            return
        text = self._command_text(event.get("text"))
        thread_ts = event.get("thread_ts")
        reply_thread = thread_ts if isinstance(thread_ts, str) else timestamp
        if text is None:
            return
        command = parse_message(text)
        if command is None:
            self.slack.reply(channel, reply_thread, HELP)
            return
        try:
            response = SLACK_SEND_UNAVAILABLE if command.name == "send" else self.gateway._dispatch(command, sender, "")
        except Exception as exc:
            print(f"slack command rejected: command={command.name} error_type={type(exc).__name__} "
                  f"error_code={_error_code(exc)}", file=sys.stderr, flush=True)
            response = _user_error(exc)
        self.slack.reply(channel, reply_thread, response)


def run(gateway: SlackGateway, socket_factory: Any) -> int:
    """Keep one Socket Mode connection alive; reconnecting never widens authority."""
    delay = 1
    while True:
        connection = None
        try:
            connection = socket_factory(gateway.slack.socket_url(), timeout=45)
            delay = 1
            while True:
                raw = connection.recv()
                if not isinstance(raw, str):
                    continue
                envelope = json.loads(raw)
                if not isinstance(envelope, dict):
                    continue
                envelope_id = envelope.get("envelope_id")
                if isinstance(envelope_id, str):
                    connection.send(json.dumps({"envelope_id": envelope_id}))
                gateway.handle_envelope(envelope)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f"slack socket reconnect: error_type={type(exc).__name__} error_code={_error_code(exc)}", file=sys.stderr, flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 30)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-config", type=Path, required=True)
    parser.add_argument("--slack-env", type=Path, required=True)
    parser.add_argument("--planner-env", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.broker_config.read_text(encoding="utf-8"))
    slack = Slack(_env_value(args.slack_env, "SLACK_BOT_TOKEN"), _env_value(args.slack_env, "SLACK_APP_TOKEN"))
    gateway = SlackGateway(config, slack, Path(__file__).resolve().parents[2], args.planner_env,
                           _env_value(args.slack_env, "SLACK_ALLOWED_CHANNEL_ID"),
                           _csv(_env_value(args.slack_env, "SLACK_ALLOWED_USER_IDS")))
    try:
        import websocket
    except ImportError as exc:
        raise SystemExit("websocket-client is not installed; rebuild the Père Blaise virtual environment") from exc
    return run(gateway, websocket.create_connection)


if __name__ == "__main__":
    raise SystemExit(main())
