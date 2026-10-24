import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/telegram-identity.py"
SPEC = importlib.util.spec_from_file_location("telegram_identity", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TelegramIdentityTest(unittest.TestCase):
    def test_exact_private_challenge_only_and_token_redacted(self):
        with tempfile.TemporaryDirectory() as home:
            directory = Path(home) / "Library/Application Support/HermesLeodagan"
            directory.mkdir(parents=True)
            token_file = directory / "telegram-leodagan-bot.token"
            token = "123456789:" + "A" * 35
            token_file.write_text(token)
            token_file.chmod(0o600)
            payload = {"ok": True, "result": [
                {"message": {"text": "phrase-unique", "from": {"id": 42}, "chat": {"id": 42, "type": "private"}}},
                {"message": {"text": "phrase-unique", "from": {"id": 99}, "chat": {"id": -99, "type": "group"}}},
                {"message": {"text": "autre texte", "from": {"id": 77}, "chat": {"id": 77, "type": "private"}}},
            ]}
            output = io.StringIO()
            with patch.dict(os.environ, {"HOME": home}), patch.object(sys, "argv", [str(SCRIPT), "phrase-unique"]), patch.object(MODULE, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())), redirect_stdout(output):
                self.assertEqual(MODULE.main(), 0)
            self.assertEqual(output.getvalue(), "TELEGRAM_ALLOWED_USERS=42\n")
            self.assertNotIn(token, output.getvalue())


if __name__ == "__main__":
    unittest.main()
