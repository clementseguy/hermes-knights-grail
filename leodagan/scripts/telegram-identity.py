#!/usr/bin/env python3
"""Find the Telegram numeric user ID from a private, exact challenge message.

Run before enabling Telegram in Hermes, so this is the only getUpdates client.
No token or message content is printed.
"""

import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print("Usage: telegram-identity.py 'phrase exacte envoyée au bot'", file=sys.stderr)
        return 2
    token_file = Path.home() / "Library/Application Support/HermesLeodagan/telegram-leodagan-bot.token"
    if token_file.is_symlink() or not token_file.is_file() or token_file.stat().st_mode & 0o077:
        print("Fichier Telegram absent ou permissions trop larges (mode 600 requis).", file=sys.stderr)
        return 1
    token = token_file.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{30,}", token):
        print("Format du jeton Telegram invalide.", file=sys.stderr)
        return 1
    try:
        with urlopen(f"https://api.telegram.org/bot{token}/getUpdates?limit=100&timeout=0", timeout=15) as response:
            payload = json.load(response)
    except Exception:
        print("Lecture des mises à jour Telegram impossible ; vérifier le réseau et le jeton.", file=sys.stderr)
        return 1
    if payload.get("ok") is not True:
        print("Telegram a refusé getUpdates ; vérifier le jeton et l'absence d'un autre consommateur.", file=sys.stderr)
        return 1
    ids = set()
    for update in payload.get("result", []):
        message = update.get("message", {})
        sender = message.get("from", {})
        chat = message.get("chat", {})
        if (message.get("text") == sys.argv[1] and chat.get("type") == "private"
                and sender.get("id") == chat.get("id") and not sender.get("is_bot")):
            ids.add(sender["id"])
    if len(ids) != 1:
        print("Aucun ID unique trouvé. Envoyer la phrase exacte en DM au bot, puis réessayer.", file=sys.stderr)
        return 1
    print(f"TELEGRAM_ALLOWED_USERS={ids.pop()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
