from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from pere_blaise.file_ingress import open_download, save_attachment
from pere_blaise.router import parse_message
from pere_blaise.slack_gateway import Slack, SlackGateway
from pere_blaise.telegram_gateway import Gateway


class FileIngressTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in ('Downloads', 'Documents', 'Backups', 'state'):
            (self.root / name).mkdir()
        self.downloads = self.root / 'Downloads'
        self.config = {
            'database': str(self.root / 'state' / 'plans.sqlite3'),
            'runtime_dir': str(self.root / 'state'),
            'downloads': str(self.downloads), 'documents': str(self.root / 'Documents'),
            'backups': str(self.root / 'Backups'), 'sha256_max_bytes': 1000,
            'send_max_bytes': 1000, 'receive_max_bytes': 1000,
            'telegram_allowed_user_ids': ['1', '2'], 'telegram_receive_user_id': '1',
            'slack_allowed_user_ids': ['U1', 'U2'], 'slack_receive_user_id': 'U1',
            'slack_bot_user_id': 'UBOT',
            'identity_map': {'telegram:1': 'person:clement', 'slack:U1': 'person:clement'},
        }

    def test_exact_command_and_bounded_safe_file(self):
        self.assertEqual(parse_message('tiens').name, 'receive')
        self.assertIsNone(parse_message('tiens fichier'))
        pdf = b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n'
        self.assertEqual(save_attachment(self.downloads, 'rapport.pdf', len(pdf), io.BytesIO(pdf), 1000), 'rapport.pdf')
        self.assertEqual((self.downloads / 'rapport.pdf').read_bytes(), pdf)
        with self.assertRaisesRegex(ValueError, 'PB-RECEIVE-COLLISION'):
            save_attachment(self.downloads, 'RAPPORT.PDF', len(pdf), io.BytesIO(pdf), 1000)
        self.assertEqual(sorted(p.name for p in self.downloads.iterdir()), ['rapport.pdf'])

    def test_rejects_executable_disguise_and_incomplete_stream(self):
        cases = [('run.sh', b'#!/bin/sh\n'), ('run.sh.txt', b'notes'),
                 ('notes.txt', b'#!/bin/sh\nrm -rf x'), ('notes.txt', b'\x7fELFbinary'),
                 ('page.html', b'<html>'), ('notes.pdf', b'MZfake'),
                 ('../outside.pdf', b'%PDF-1.4\n%%EOF')]
        for name, data in cases:
            with self.subTest(name=name, data=data), self.assertRaises(ValueError):
                save_attachment(self.downloads, name, len(data), io.BytesIO(data), 1000)
        with self.assertRaisesRegex(ValueError, 'PB-RECEIVE-LIMIT'):
            save_attachment(self.downloads, 'safe.txt', 1001, io.BytesIO(b'x'), 1000)
        with self.assertRaisesRegex(ValueError, 'PB-RECEIVE-FAILED'):
            save_attachment(self.downloads, 'safe.txt', 4, io.BytesIO(b'abc'), 1000)
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_rejects_macro_archive_and_symlinked_root(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            archive.writestr('word/document.xml', '<document/>')
            archive.writestr('word/vbaProject.bin', b'macro')
        data = stream.getvalue()
        with self.assertRaisesRegex(ValueError, 'PB-RECEIVE-TYPE'):
            save_attachment(self.downloads, 'document.docx', len(data), io.BytesIO(data), 1000)
        external = io.BytesIO()
        with zipfile.ZipFile(external, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            archive.writestr('word/document.xml', '<document/>')
            archive.writestr('word/_rels/document.xml.rels', "<Relationship TargetMode='External' Target='https://example.test'/>")
        data = external.getvalue()
        with self.assertRaisesRegex(ValueError, 'PB-RECEIVE-TYPE'):
            save_attachment(self.downloads, 'linked.docx', len(data), io.BytesIO(data), 1000)
        active_pdf = b'%PDF-1.4\n/JavaScript (alert)\n%%EOF\n'
        with self.assertRaisesRegex(ValueError, 'PB-RECEIVE-TYPE'):
            save_attachment(self.downloads, 'active.pdf', len(active_pdf), io.BytesIO(active_pdf), 1000)
        outside = self.root / 'outside'; outside.mkdir()
        link = self.root / 'link'; link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            save_attachment(link, 'safe.txt', 4, io.BytesIO(b'safe'), 1000)
        self.assertEqual(list(outside.iterdir()), [])

    def test_telegram_owner_and_caption(self):
        class FakeTelegram:
            def __init__(self): self.messages = []; self.downloads = 0
            def message(self, chat, text): self.messages.append((chat, text))
            def download(self, _file_id, _size):
                self.downloads += 1
                return io.BytesIO(b'safe')
        bot = FakeTelegram()
        gateway = Gateway(self.config, bot, self.root, self.root / 'unused.env')
        def message(sender, caption='tiens', name='safe.txt'):
            return {'from': {'id': sender}, 'chat': {'id': sender, 'type': 'private'},
                    'caption': caption, 'document': {'file_id': 'file1', 'file_name': name, 'file_size': 4}}
        gateway.handle(message(2))
        self.assertEqual(bot.downloads, 0)
        self.assertEqual(list(self.downloads.iterdir()), [])
        gateway.handle(message(1, name='run.py'))
        self.assertEqual(bot.downloads, 0)
        gateway.handle(message(1))
        self.assertEqual(bot.downloads, 1)
        self.assertEqual((self.downloads / 'safe.txt').read_bytes(), b'safe')
        self.assertIn('Downloads', bot.messages[-1][1])

    def test_telegram_two_message_intent_is_owner_only_short_and_single_use(self):
        class FakeTelegram:
            def __init__(self): self.messages = []; self.downloads = 0
            def message(self, chat, text): self.messages.append((chat, text))
            def download(self, _file_id, _size):
                self.downloads += 1
                return io.BytesIO(b'safe')
        bot = FakeTelegram()
        gateway = Gateway(self.config, bot, self.root, self.root / 'unused.env')
        def text(sender, value='tiens'):
            return {'from': {'id': sender}, 'chat': {'id': sender, 'type': 'private'}, 'text': value}
        def document(sender, name='safe.txt'):
            return {'from': {'id': sender}, 'chat': {'id': sender, 'type': 'private'},
                    'document': {'file_id': 'file1', 'file_name': name, 'file_size': 4}}
        gateway.handle(document(1))
        gateway.handle(text(2))
        gateway.handle(document(2))
        self.assertEqual(bot.downloads, 0)
        gateway.handle(text(1))
        self.assertIn('5 minutes', bot.messages[-1][1])
        gateway.handle(document(1))
        self.assertEqual(bot.downloads, 1)
        self.assertEqual((self.downloads / 'safe.txt').read_bytes(), b'safe')
        gateway.handle(document(1, 'next.txt'))
        self.assertEqual(bot.downloads, 1)
        with patch('pere_blaise.telegram_gateway.time.monotonic', side_effect=[100.0, 401.0]):
            gateway.handle(text(1))
            gateway.handle(document(1, 'expired.txt'))
        self.assertEqual(bot.downloads, 1)
        gateway.handle(text(1))
        gateway.handle(text(1, 'analyse inconnu'))
        gateway.handle(document(1, 'cancelled.txt'))
        self.assertEqual(bot.downloads, 1)

    def test_slack_owner_channel_thread_and_duplicate_events(self):
        class FakeSlack:
            def __init__(self): self.replies = []; self.downloads = 0
            def reply(self, channel, thread, text): self.replies.append((channel, thread, text))
            def download(self, _file_id, _sender, _size, _filename):
                self.downloads += 1
                return io.BytesIO(b'safe')
        slack = FakeSlack()
        gateway = SlackGateway(self.config, slack, self.root, self.root / 'unused.env', 'C1', {'U1', 'U2'})
        def envelope(sender='U1', channel='C1', typ='message', event_id='e1', subtype=None,
                     text='<@UBOT> tiens'):
            return {'type': 'events_api', 'payload': {'event_id': event_id,
                'event': {'type': typ, 'subtype': subtype,
                          'channel': channel, 'user': sender, 'ts': '123.4',
                          'text': text, 'files': [{'id': 'F1', 'name': 'safe.txt', 'size': 4}]}}}
        gateway.handle_envelope(envelope(sender='U2'))
        gateway.handle_envelope(envelope(channel='C2'))
        self.assertEqual(slack.downloads, 0)
        gateway.handle_envelope(envelope(text='<@UBOT|Hermes - Pere Blaise> tiens'))
        gateway.handle_envelope(envelope(event_id='e3', subtype='file_share'))
        gateway.handle_envelope(envelope(typ='app_mention', event_id='e2'))
        self.assertEqual(slack.downloads, 1)
        self.assertEqual((self.downloads / 'safe.txt').read_bytes(), b'safe')
        self.assertEqual(slack.replies[-1][:2], ('C1', '123.4'))

    def test_slack_download_rejects_remote_and_foreign_hosts(self):
        slack = Slack('fixture-token', 'fixture-app')
        slack.call = lambda *_args, **_kwargs: {'file': {'id': 'F1', 'user': 'U1', 'name': 'safe.txt',
            'size': 4, 'is_external': True, 'mode': 'external', 'url_private_download': 'https://evil.test/file'}}
        with self.assertRaisesRegex(ValueError, 'PB-RECEIVE-FAILED'):
            slack.download('F1', 'U1', 4, 'safe.txt')
        with self.assertRaisesRegex(ValueError, 'PB-RECEIVE-FAILED'):
            open_download('https://files.slack.com.evil.test/file', 'files.slack.com',
                          {'Authorization': 'Bearer fixture-token'})

    def test_slack_file_info_uses_supported_form_encoding(self):
        slack = Slack('fixture-token', 'fixture-app')
        with patch('pere_blaise.slack_gateway.urlopen', return_value=io.BytesIO(b'{"ok":true,"file":{}}')) as api:
            slack.call('files.info', {'file': 'F123'})
            request = api.call_args.args[0]
        self.assertEqual(request.get_header('Content-type'), 'application/x-www-form-urlencoded')
        self.assertEqual(parse_qs(request.data.decode()), {'file': ['F123']})

    def test_private_config_requires_same_verified_owner(self):
        private = self.root / 'private'; private.mkdir(mode=0o700)
        config = dict(self.config)
        config.update(downloads='/downloads', documents='/documents', backups='/backups',
                      database='/state/plans.sqlite3', runtime_dir='/state',
                      max_files=100, max_directories=100, analysis_timeout_sec=120,
                      slack_allowed_channel_id='C1')
        for name, content in {'telegram.token': 'fixture', 'slack-bot.token': 'fixture',
                              'slack-app.token': 'fixture', 'planner.env': 'PERE_BLAISE_API_KEY=abcdefgh12345678ABCDEFGH87654321',
                              'planner-api.env': 'API_SERVER_KEY=abcdefgh12345678ABCDEFGH87654321'}.items():
            path = private / name; path.write_text(content); path.chmod(0o600)
        config_path = private / 'broker.json'
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'validate-private.py'
        def validate():
            config_path.write_text(json.dumps(config)); config_path.chmod(0o600)
            return subprocess.run([sys.executable, str(script), str(private)], capture_output=True, text=True)
        self.assertEqual(validate().returncode, 0)
        config['identity_map']['slack:U1'] = 'person:other'
        self.assertNotEqual(validate().returncode, 0)
        config['identity_map']['slack:U1'] = 'person:clement'
        config['slack_receive_user_id'] = 'U2'
        self.assertNotEqual(validate().returncode, 0)


if __name__ == '__main__':
    unittest.main()
