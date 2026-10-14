from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pere_blaise.broker import Broker
from pere_blaise.contracts import fingerprint
from pere_blaise.executor import Executor, TransactionError
from pere_blaise.file_delivery import identity, search_documents, validate_selection
from pere_blaise.planning import manifest_from_proposal, planner_context
from pere_blaise.scanner import scan
from pere_blaise.scheduler import WeeklyScheduler, run_once
from pere_blaise.telegram_gateway import Gateway, process_updates
from pere_blaise.slack_gateway import Slack, SlackGateway
from pere_blaise.store import PlanStore
from pere_blaise.workflow import analyse
from pere_blaise.router import parse_message
from pere_blaise.errors import CATALOG, classify, user_message
from pere_blaise.ingress_ledger import IngressLedger


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.d = self.root / 'Downloads'; self.o = self.root / 'Documents'; self.b = self.root / 'Backups'; self.s = self.root / 'state'
        for p in (self.d, self.o, self.b, self.s): p.mkdir()
        (self.o / 'Factures').mkdir()
        self.store = PlanStore(self.s / 'plans.sqlite3')
        self.broker = Broker(self.store, runtime_dir=self.s, downloads=self.d, documents=self.o, backups=self.b)

    def source(self, name='facture.txt', data=b'data'):
        p = self.d / name; p.write_bytes(data); return p

    def planner(self, context):
        return {'actions': [{'source_relative': x['source_relative'], 'destination_relative': 'Factures/' + x['source_relative'],
                             'reason': 'Le nom indique une facture', 'certainty': 'clear'} for x in context['untrusted_downloads']]}

    def test_analysis_minimizes_data_and_does_not_move(self):
        self.source(); (self.o / 'Factures' / 'ancien-secret.txt').write_text('secret')
        seen = []
        plan = analyse('telegram:1', self.root, self.broker, lambda c: (seen.append(json.dumps(c)) or self.planner(c)), 1000)
        self.assertEqual(plan['details']['confidence'], 'High')
        self.assertTrue((self.d / 'facture.txt').exists())
        self.assertNotIn('ancien-secret', seen[0]); self.assertNotIn('sha256', seen[0])
        self.assertNotIn('inode', seen[0]); self.assertNotIn('secret', seen[0])
        self.assertNotIn('learning', seen[0])

    def test_apply_backups_and_owner(self):
        self.source()
        plan = analyse('telegram:1', self.root, self.broker, self.planner, 1000)
        with self.assertRaises(PermissionError): self.broker.apply('slack:1', plan['id'])
        result = self.broker.apply('telegram:1', plan['id'])
        self.assertEqual(result['state'], 'APPLIED')
        self.assertFalse((self.d / 'facture.txt').exists())
        self.assertEqual((self.o / 'Factures' / 'facture.txt').read_bytes(), b'data')
        self.assertEqual((self.b / plan['id'] / 'facture.txt').read_bytes(), b'data')
        with self.assertRaises(ValueError): self.broker.apply('telegram:1', plan['id'])

    def test_rollback_after_first_move(self):
        a = self.source('a.txt', b'a'); z = self.source('z.txt', b'z')
        manifest = {'version': 2, 'actions': [
            {'source': p.name, 'destination': 'Factures/' + p.name, 'expected': fingerprint(p).as_dict()} for p in (a, z)]}
        result = self.broker.executor.apply('calme-arbre', manifest, fault_after=1)
        self.assertEqual(result['state'], 'ROLLED_BACK')
        self.assertTrue(a.exists() and z.exists())
        self.assertFalse((self.o / 'Factures' / 'a.txt').exists())
        self.assertTrue((self.b / 'calme-arbre' / 'a.txt').exists())

    def test_recovery_after_interrupted_move(self):
        p = self.source(); manifest = {'version': 2, 'actions': [{'source': p.name, 'destination': 'Factures/' + p.name,
                                                                   'expected': fingerprint(p).as_dict()}]}
        ident = 'calme-arbre'; backup = self.b / ident; backup.mkdir(); (backup / p.name).write_bytes(p.read_bytes())
        dest = self.o / 'Factures' / p.name; dest.write_bytes(p.read_bytes()); p.unlink()
        journal = {'plan_id': ident, 'state': 'APPLYING', 'manifest': manifest, 'moved': [], 'incident': 'test',
                   'created': {'Factures/facture.txt': {'device': dest.stat().st_dev, 'inode': dest.stat().st_ino}}}
        (self.s / (ident + '.journal.json')).write_text(json.dumps(journal))
        results = self.broker.executor.recover()
        self.assertEqual(results[0]['state'], 'ROLLED_BACK')
        self.assertTrue(p.exists()); self.assertFalse(dest.exists())

    def test_recovery_before_first_movement_keeps_sources(self):
        p = self.source(); manifest = {'version': 2, 'actions': [{'source': p.name,
            'destination': 'Factures/' + p.name, 'expected': fingerprint(p).as_dict()}]}
        for ident, state in [('calme-arbre','PREPARING'), ('calme-avion','BACKUPS_VERIFIED')]:
            backup = self.b/ident; backup.mkdir(); (backup/p.name).write_bytes(p.read_bytes())
            (self.s/(ident+'.journal.json')).write_text(json.dumps({'plan_id':ident,'state':state,
                'manifest':manifest,'moved':[],'created':{},'incident':'test'}))
        results = self.broker.executor.recover()
        self.assertEqual([item['state'] for item in results], ['ROLLED_BACK','ROLLED_BACK'])
        self.assertTrue(p.exists())

    def test_recovery_blocks_concurrent_edit(self):
        p = self.source(); manifest = {'version': 2, 'actions': [{'source': p.name, 'destination': 'Factures/' + p.name,
                                                                   'expected': fingerprint(p).as_dict()}]}
        ident = 'calme-arbre'; backup = self.b / ident; backup.mkdir(); (backup / p.name).write_bytes(p.read_bytes())
        dest = self.o / 'Factures' / p.name; dest.write_bytes(b'edited'); p.unlink()
        (self.s / (ident + '.journal.json')).write_text(json.dumps({'plan_id': ident, 'state': 'APPLYING',
            'manifest': manifest, 'moved': [], 'created': {'Factures/facture.txt':
            {'device': dest.stat().st_dev, 'inode': dest.stat().st_ino}}}))
        self.assertEqual(self.broker.executor.recover()[0]['state'], 'BLOCKED_RECOVERY')
        self.assertEqual(dest.read_bytes(), b'edited')

    def test_unknown_matching_target_is_never_removed(self):
        p = self.source(); manifest = {'version': 2, 'actions': [{'source': p.name,
            'destination': 'Factures/' + p.name, 'expected': fingerprint(p).as_dict()}]}
        dest = self.o/'Factures'/p.name; dest.write_bytes(p.read_bytes())
        journal = {'plan_id': 'calme-arbre', 'state': 'APPLYING', 'manifest': manifest,
                   'moved': [], 'created': {}, 'incident': 'test'}
        (self.s/'calme-arbre.journal.json').write_text(json.dumps(journal))
        outcome = self.broker.executor.recover()[0]
        self.assertEqual(outcome['state'], 'BLOCKED_RECOVERY')
        self.assertEqual(dest.read_bytes(), b'data')
        with self.assertRaises(RuntimeError): self.broker.create_plan('telegram:1', manifest, {'actions': []})

    def test_hard_process_crash_and_restart(self):
        p = self.source()
        manifest = {'version': 2, 'actions': [{'source': p.name, 'destination': 'Factures/' + p.name,
                                               'expected': fingerprint(p).as_dict()}]}
        code = ('from pathlib import Path; from pere_blaise.executor import Executor; '
                f'Executor(Path({str(self.d)!r}),Path({str(self.o)!r}),Path({str(self.b)!r}),Path({str(self.s)!r}))'
                f'.apply("calme-arbre",{manifest!r},crash_after=1)')
        env = __import__('os').environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
        result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True)
        self.assertEqual(result.returncode, 77)
        recovered = Executor(self.d, self.o, self.b, self.s).recover()
        self.assertEqual(recovered[0]['state'], 'ROLLED_BACK')
        self.assertTrue(p.exists()); self.assertFalse((self.o / 'Factures' / p.name).exists())

    def test_restart_finishes_committed_journal_without_reapplying(self):
        p = self.source(); manifest = {'version': 2, 'actions': [{'source': p.name,
            'destination': 'Factures/' + p.name, 'expected': fingerprint(p).as_dict()}]}
        plan = self.broker.create_plan('telegram:1', manifest, {'actions': []})
        self.store.claim(plan['id'], 'telegram:1')
        self.assertEqual(self.broker.executor.apply(plan['id'], manifest)['state'], 'APPLIED')
        restarted = Broker(PlanStore(self.store.database), runtime_dir=self.s,
                           downloads=self.d, documents=self.o, backups=self.b)
        self.assertEqual(restarted.store.get(plan['id'])['state'], 'applied')
        self.assertFalse(p.exists())

    def test_plan_expiry_and_invalidation(self):
        self.source(); first = analyse('telegram:1', self.root, self.broker, self.planner, 1000)
        self.assertEqual((datetime.fromisoformat(first['expires_at']) - datetime.fromisoformat(first['created_at'])).total_seconds(), 1800)
        second = analyse('telegram:1', self.root, self.broker, self.planner, 1000)
        with self.assertRaises(ValueError): self.broker.detail('telegram:1', first['id'])
        with sqlite3.connect(self.store.database) as db:
            db.execute('UPDATE plans SET expires_at=? WHERE id=?', ((datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(), second['id']))
        with self.assertRaises(ValueError): self.broker.apply('telegram:1', second['id'])

    def test_changed_download_and_directory_invalidate(self):
        self.source(); plan = analyse('telegram:1', self.root, self.broker, self.planner, 1000)
        (self.o / 'Nouveau').mkdir()
        with self.assertRaises(ValueError): self.broker.apply('telegram:1', plan['id'])
        self.assertTrue((self.d / 'facture.txt').exists())

    def test_proposal_requires_complete_and_existing_directory(self):
        self.source(); inv = {'downloads': scan(self.d, hash_files=True, sha256_max_bytes=1000),
                              'documents': scan(self.o, hash_files=False, sha256_max_bytes=1000)}
        with self.assertRaises(ValueError): manifest_from_proposal({'actions': []}, inv)
        with self.assertRaises(ValueError): manifest_from_proposal({'actions': [{'source_relative': 'facture.txt',
            'destination_relative': 'MadeUp/facture.txt', 'reason': 'x', 'certainty': 'clear'}]}, inv)

    def test_send_zero_one_many_and_symlink(self):
        self.assertEqual(search_documents(self.o, 'facture'), [])
        a = self.o / 'Factures' / 'facturé.txt'; a.write_text('a')
        self.assertEqual(search_documents(self.o, 'facture'), [a])
        other = self.o / 'autre'; other.mkdir(); b = other / 'facture.pdf'; b.write_text('b')
        self.assertEqual(len(search_documents(self.o, 'facture')), 2)
        target = self.root / 'outside'; target.write_text('x'); (self.o / 'Factures' / 'facture-link').symlink_to(target)
        self.assertEqual(len(search_documents(self.o, 'facture')), 2)
        with self.assertRaises(ValueError): validate_selection(self.o, a, identity(a), 0)

    def test_fifo_cannot_block_file_fingerprinting(self):
        fifo = self.d / 'untrusted.fifo'
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            fingerprint(fifo)

    def test_send_choice_owner_and_revalidation(self):
        config = {'database': str(self.s / 'plans.sqlite3'), 'runtime_dir': str(self.s), 'downloads': str(self.d),
                  'documents': str(self.o), 'backups': str(self.b), 'sha256_max_bytes': 1000,
                  'send_max_bytes': 1000, 'telegram_allowed_user_ids': ['1']}
        gateway = Gateway(config, None, Path(__file__).resolve().parents[1], self.root / 'unused.env')
        (self.o / 'Factures' / 'invoice.txt').write_bytes(b'a')
        (self.o / 'invoice.txt').write_bytes(b'b')
        sent = []
        response = gateway._send('telegram:1', 'invoice', sent.append)
        self.assertIn('1.', response); self.assertIn('2.', response); self.assertEqual(sent, [])
        with self.assertRaises(ValueError): gateway.select('slack:1', '1', sent.append)
        (self.o / 'Factures' / 'invoice.txt').write_bytes(b'changed')
        with self.assertRaises(ValueError): gateway.select('telegram:1', '1', sent.append)
        self.assertEqual(sent, [])

    def test_send_selection_is_bound_to_original_channel_and_thread(self):
        config = {'database': str(self.s / 'plans.sqlite3'), 'runtime_dir': str(self.s), 'downloads': str(self.d),
                  'documents': str(self.o), 'backups': str(self.b), 'sha256_max_bytes': 1000,
                  'send_max_bytes': 1000, 'identity_map': {'telegram:1': 'person:one', 'slack:U1': 'person:one'}}
        gateway = Gateway(config, None, Path(__file__).resolve().parents[1], self.root / 'unused.env')
        (self.o / 'Factures' / 'invoice.txt').write_bytes(b'a')
        (self.o / 'invoice.txt').write_bytes(b'b')
        sent = []
        gateway._send('person:one', 'invoice', lambda path, content: sent.append(content), 'telegram:1')
        with self.assertRaises(ValueError):
            gateway.select('person:one', '1', lambda path, content: sent.append(content), 'slack:C1:123')
        gateway._send('person:one', 'invoice', lambda path, content: sent.append(content), 'slack:C1:123')
        with self.assertRaises(ValueError):
            gateway.select('person:one', '1', lambda path, content: sent.append(content), 'slack:C1:456')
        self.assertEqual(sent, [])

    def test_send_one_passes_only_selected_bytes(self):
        config = {'database': str(self.s / 'plans.sqlite3'), 'runtime_dir': str(self.s), 'downloads': str(self.d),
                  'documents': str(self.o), 'backups': str(self.b), 'sha256_max_bytes': 1000,
                  'send_max_bytes': 1000, 'telegram_allowed_user_ids': ['1']}
        gateway = Gateway(config, None, Path(__file__).resolve().parents[1], self.root/'unused.env')
        file = self.o/'Factures'/'invoice.txt'; file.write_bytes(b'only this file')
        sent=[]
        result = gateway._send('telegram:1', 'invoice', lambda path, content: sent.append((path,content)))
        self.assertIn('Fichier envoyé', result)
        self.assertEqual(sent, [(file,b'only this file')])

    def test_private_identity_mapping_requires_configuration(self):
        config = {'database': str(self.s/'plans.sqlite3'), 'runtime_dir': str(self.s), 'downloads': str(self.d),
                  'documents': str(self.o), 'backups': str(self.b), 'sha256_max_bytes': 1000,
                  'send_max_bytes': 1000, 'identity_map': {'telegram:1':'person:clement', 'slack:U1':'person:clement'}}
        gateway = Gateway(config, None, Path(__file__).resolve().parents[1], self.root/'unused.env')
        self.assertEqual(gateway.owner('telegram','1'), gateway.owner('slack','U1'))
        self.assertNotEqual(gateway.owner('telegram','2'), gateway.owner('slack','U2'))

    def test_slack_native_upload_uses_only_original_thread(self):
        from unittest.mock import patch
        class FakeSlack(Slack):
            def __init__(self): super().__init__('fake-bot', 'fake-app'); self.calls=[]
            def call(self, method, payload, **kwargs):
                self.calls.append((method,payload))
                return {'upload_url':'https://files.slack.com/upload/fake','file_id':'F1'} if method=='files.getUploadURLExternal' else {'ok':True}
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*_): pass
        slack=FakeSlack()
        with patch('pere_blaise.slack_gateway.urlopen', return_value=Response()) as upload:
            slack.document('C1','123.4',Path('invoice.txt'),b'bytes')
        self.assertEqual(slack.calls[0][0], 'files.getUploadURLExternal')
        self.assertEqual(slack.calls[1][1]['channel_id'], 'C1')
        self.assertEqual(slack.calls[1][1]['thread_ts'], '123.4')
        self.assertEqual(upload.call_args.args[0].data, b'bytes')

    def test_slack_upload_methods_use_form_fields(self):
        import io
        from unittest.mock import patch
        from urllib.parse import parse_qs
        slack = Slack('bot-test-token', 'app-test-token')
        with patch('pere_blaise.slack_gateway.urlopen', return_value=io.BytesIO(b'{"ok":true}')) as api:
            slack.call('files.getUploadURLExternal', {'filename': 'test.txt', 'length': 60})
            request = api.call_args.args[0]
            self.assertEqual(request.get_header('Content-type'), 'application/x-www-form-urlencoded')
            self.assertEqual(parse_qs(request.data.decode()), {'filename': ['test.txt'], 'length': ['60']})
        with patch('pere_blaise.slack_gateway.urlopen', return_value=io.BytesIO(b'{"ok":true}')) as api:
            slack.call('files.completeUploadExternal', {'files': [{'id': 'F1', 'title': 'test.txt'}],
                                                        'channel_id': 'C1', 'thread_ts': '123.4'})
            fields = parse_qs(api.call_args.args[0].data.decode())
            self.assertEqual(json.loads(fields['files'][0]), [{'id': 'F1', 'title': 'test.txt'}])
            self.assertEqual(fields['channel_id'], ['C1'])
            self.assertEqual(fields['thread_ts'], ['123.4'])

    def test_slack_channel_allowlist_and_thread_delivery(self):
        config = {'database': str(self.s / 'plans.sqlite3'), 'runtime_dir': str(self.s), 'downloads': str(self.d),
                  'documents': str(self.o), 'backups': str(self.b), 'sha256_max_bytes': 1000,
                  'send_max_bytes': 1000, 'telegram_allowed_user_ids': [], 'slack_allowed_user_ids': ['U1']}
        class Slack:
            def __init__(self): self.replies=[]; self.documents=[]
            def reply(self, channel, thread, text): self.replies.append((channel, thread, text))
            def document(self, channel, thread, path, root): self.documents.append((channel, thread, path, root))
        slack=Slack()
        gateway=SlackGateway(config, slack, Path(__file__).resolve().parents[1], self.root/'unused.env', 'C1', {'U1'})
        file=self.o/'Factures'/'invoice.txt'; file.write_bytes(b'a')
        def envelope(channel='C1', user='U1', event_id='e1', text='<@B1> envoie invoice'):
            return {'type':'events_api','payload':{'event_id':event_id,'event':{'type':'app_mention','channel':channel,
                    'user':user,'ts':'123.4','text':text}}}
        gateway.handle_envelope(envelope(channel='C2'))
        gateway.handle_envelope(envelope(user='U2',event_id='e2'))
        self.assertEqual(slack.replies, []); self.assertEqual(slack.documents, [])
        gateway.handle_envelope(envelope(event_id='e3'))
        self.assertEqual(slack.documents[0][:2], ('C1','123.4'))
        self.assertEqual(slack.documents[0][2], file)
        restarted = SlackGateway(config, slack, Path(__file__).resolve().parents[1], self.root/'unused.env', 'C1', {'U1'})
        restarted.handle_envelope(envelope(event_id='e3'))
        self.assertEqual(len(slack.documents), 1)

    def test_ingress_ledger_prevents_replay_after_restart(self):
        first = IngressLedger(self.s)
        self.assertTrue(first.begin('telegram', '123'))
        self.assertFalse(IngressLedger(self.s).begin('telegram', '123'))
        first.complete('telegram', '123')
        self.assertFalse(IngressLedger(self.s).begin('telegram', '123'))
        self.assertTrue(IngressLedger(self.s).begin('slack', '123'))

    def test_telegram_update_is_not_replayed_after_restart(self):
        class GatewayStub:
            def __init__(self): self.handled = []
            def handle(self, message): self.handled.append(message['text'])
        event = [{'update_id': 101, 'message': {'text': 'envoie facture'}}]
        first = GatewayStub()
        self.assertEqual(process_updates(event, first, IngressLedger(self.s), 0), 102)
        self.assertEqual(first.handled, ['envoie facture'])
        restarted = GatewayStub()
        self.assertEqual(process_updates(event, restarted, IngressLedger(self.s), 0), 102)
        self.assertEqual(restarted.handled, [])

    def test_a_trier_does_not_collect_learning(self):
        p = self.source('opaque.txt', b'unique')
        manifest = {'version': 2, 'actions': [{'source': p.name, 'destination': 'a_trier/' + p.name,
                                               'expected': fingerprint(p).as_dict()}]}
        plan = self.broker.create_plan('telegram:1', manifest, {'actions': [], 'snapshot': None})
        result = self.broker.apply('telegram:1', plan['id'])
        self.assertEqual(result['state'], 'APPLIED')
        with sqlite3.connect(self.store.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM a_trier_tracking').fetchone()[0], 0)
        self.assertIsNone(parse_message('apprentissages'))
        with self.assertRaisesRegex(RuntimeError, 'PB-LEARNING-DEFERRED'):
            self.store.reconcile_a_trier({}, self.o, 1000)

    def test_scheduler_and_channel_failure(self):
        schedule = WeeklyScheduler(self.s / 'schedule.sqlite3', enabled=True)
        sunday = datetime(2026, 10, 18, 15, 0, tzinfo=timezone.utc)
        self.assertTrue(schedule.claim(sunday)); self.assertFalse(schedule.claim(sunday))
        winter = datetime(2026, 12, 20, 16, 0, tzinfo=timezone.utc)
        self.assertTrue(schedule.claim(winter))
        class Fail:
            def message(self, *_): raise RuntimeError('offline')
        class Slack:
            def __init__(self): self.messages=[]
            def call(self, _method, payload): self.messages.append(payload['text'])
        class Gateway:
            def _analyse(self, _owner): return 'plan ready'
        slack = Slack(); failures = run_once(Gateway(), Fail(), slack, '1', 'C1', 'telegram:1')
        self.assertEqual(len(slack.messages), 2); self.assertIn('telegram_start', failures)

    def test_scheduler_catchup_window_dst_and_restart(self):
        path = self.s / 'schedule.sqlite3'
        schedule = WeeklyScheduler(path, enabled=True)
        self.assertFalse(schedule.claim(datetime(2026, 10, 18, 14, 59, tzinfo=timezone.utc)))
        self.assertTrue(schedule.claim(datetime(2026, 10, 19, 7, 0, tzinfo=timezone.utc)))  # Monday 09 Paris
        self.assertFalse(WeeklyScheduler(path, enabled=True).claim(datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)))
        self.assertFalse(schedule.claim(datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)))  # Monday 17 Paris
        self.assertFalse(schedule.due(datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)))
        self.assertTrue(schedule.claim(datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)))  # DST ended
        self.assertTrue(schedule.claim(datetime(2027, 3, 29, 7, 0, tzinfo=timezone.utc)))  # DST started
        self.assertFalse(WeeklyScheduler(path, enabled=False).claim(datetime(2027, 4, 4, 15, 0, tzinfo=timezone.utc)))

    def test_weekly_notifies_both_before_analysis_without_range(self):
        events=[]
        class Telegram:
            def message(self, _chat, text): events.append(('telegram',text))
        class Slack:
            def call(self, _method, payload): events.append(('slack',payload['text']))
        class Gateway:
            def _analyse(self, _owner): events.append(('analyse','once')); return 'plan'
        self.assertEqual(run_once(Gateway(),Telegram(),Slack(),'1','C1','telegram:1'),{})
        self.assertEqual([item[0] for item in events], ['telegram','slack','analyse','telegram','slack'])

    def test_exact_confidence_threshold(self):
        for i in range(5): self.source(f'f{i}.txt', str(i).encode())
        def planner(context):
            actions = self.planner(context)['actions']
            actions[0]['destination_relative'] = 'a_trier/' + actions[0]['source_relative']
            actions[0]['certainty'] = 'uncertain'
            return {'actions': actions}
        plan = analyse('telegram:1', self.root, self.broker, planner, 1000)
        self.assertEqual(plan['details']['confidence'], 'Low')
        self.assertEqual(plan['details']['a_trier_percent'], 20.0)

    def test_confidence_below_twenty_percent_is_medium(self):
        for i in range(6): self.source(f'f{i}.txt', str(i).encode())
        def planner(context):
            actions = self.planner(context)['actions']
            actions[0]['destination_relative'] = 'a_trier/' + actions[0]['source_relative']
            actions[0]['certainty'] = 'uncertain'
            return {'actions': actions}
        plan = analyse('telegram:1', self.root, self.broker, planner, 1000)
        self.assertEqual(plan['details']['confidence'], 'Medium')

    def test_opaque_name_forces_low_even_if_model_claims_clear(self):
        self.source('1245487654657564jhkjh.pdf')
        plan = analyse('telegram:1', self.root, self.broker, self.planner, 1000)
        self.assertEqual(plan['details']['confidence'], 'Low')

    def test_casefold_collision_and_no_unknown_source(self):
        self.source('A.txt')
        (self.o / 'Factures' / 'a.TXT').write_text('existing')
        with self.assertRaises(ValueError): analyse('telegram:1', self.root, self.broker, self.planner, 1000)
        self.assertTrue((self.d / 'A.txt').exists())

    def test_unicode_normalization_preserves_real_disk_name(self):
        actual = 'cafe\u0301.txt'
        self.source(actual)
        plan = analyse('telegram:1', self.root, self.broker, self.planner, 1000)
        self.assertEqual(plan['manifest']['actions'][0]['source'], actual)
        self.assertEqual(plan['manifest']['actions'][0]['destination'], 'Factures/' + actual)

    def test_symlinked_download_excluded_and_parent_denied(self):
        target = self.root / 'outside'; target.write_text('private')
        (self.d / 'link.txt').symlink_to(target)
        result = scan(self.d, hash_files=True, sha256_max_bytes=1000)
        self.assertEqual(result['files'], [])
        self.assertEqual(result['excluded_count'], 1)
        nested = self.o / 'Nested'; nested.symlink_to(self.root, target_is_directory=True)
        self.source('x.txt')
        with self.assertRaises(ValueError):
            analyse('telegram:1', self.root, self.broker, lambda c: {'actions': [{'source_relative': 'x.txt',
                'destination_relative': 'Nested/x.txt', 'reason': 'x', 'certainty': 'clear'}]}, 1000)

    def test_file_size_limit_refuses_entire_inventory(self):
        self.source('small.txt', b'a'); self.source('large.txt', b'large')
        with self.assertRaises(ValueError): analyse('telegram:1', self.root, self.broker, self.planner, 1)
        self.assertFalse(any(self.b.iterdir()))

    def test_backup_space_refusal_precedes_first_movement(self):
        from unittest.mock import patch
        p = self.source()
        manifest = {'version': 2, 'actions': [{'source': p.name, 'destination': 'Factures/' + p.name,
                                               'expected': fingerprint(p).as_dict()}]}
        class Usage:
            free = 0
        with patch('pere_blaise.executor.shutil.disk_usage', return_value=Usage()):
            with self.assertRaises(TransactionError): self.broker.executor.apply('calme-arbre', manifest)
        self.assertTrue(p.exists())
        self.assertFalse((self.o/'Factures'/p.name).exists())
        self.assertFalse((self.b/'calme-arbre').exists())

    def test_broker_records_preflight_rejection_without_movement(self):
        from unittest.mock import patch
        p = self.source()
        manifest = {'version': 2, 'actions': [{'source': p.name, 'destination': 'Factures/' + p.name,
                                               'expected': fingerprint(p).as_dict()}]}
        plan = self.broker.create_plan('telegram:1', manifest, {'actions': []})
        class Usage:
            free = 0
        with patch('pere_blaise.executor.shutil.disk_usage', return_value=Usage()):
            result = self.broker.apply('telegram:1', plan['id'])
        self.assertEqual(result['state'], 'REJECTED')
        self.assertEqual(result['code'], 'PB-BACKUP-SPACE')
        self.assertEqual(self.store.get(plan['id'])['state'], 'rejected')
        self.assertTrue(p.exists())

    def test_invalidation_on_content_edit_even_same_size(self):
        self.source(); plan = analyse('telegram:1', self.root, self.broker, self.planner, 1000)
        (self.d / 'facture.txt').write_bytes(b'edit')
        with self.assertRaises(ValueError): self.broker.apply('telegram:1', plan['id'])
        self.assertFalse(any(self.b.iterdir()))

    def test_existing_learning_rows_remain_intact_but_unavailable(self):
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.store.database) as db:
            cursor = db.execute('INSERT INTO learning_examples (source_name,extension,size,destination_directory,learned_at,expires_at) VALUES (?,?,?,?,?,?)',
                                ('facture.txt','.txt',4,'a_trier',now.isoformat(),(now+timedelta(days=90)).isoformat()))
            example_id = cursor.lastrowid
        self.source('facture.txt')
        seen=[]
        analyse('telegram:1', self.root, self.broker, lambda context: (seen.append(context) or self.planner(context)), 1000)
        self.assertNotIn('learning_hints', seen[0])
        for call in (lambda: self.store.learning_hints([]), lambda: self.store.learning_status(),
                     lambda: self.store.list_learning_examples(), lambda: self.store.delete_learning_example(example_id),
                     lambda: self.store.correct_learning_example(example_id, 'Factures', self.o)):
            with self.assertRaisesRegex(RuntimeError, 'PB-LEARNING-DEFERRED'): call()
        with sqlite3.connect(self.store.database) as db:
            self.assertEqual(db.execute('SELECT destination_directory FROM learning_examples WHERE id=?', (example_id,)).fetchone()[0], 'a_trier')

    def test_error_catalog_and_sanitized_incident(self):
        import io
        from contextlib import redirect_stderr
        for code in ('PB-DL-EMPTY','PB-FS-DENIED','PB-PLAN-EXPIRED','PB-PLAN-INVALID','PB-PLAN-OWNER',
                     'PB-PLAN-COLLISION','PB-BACKUP-SPACE','PB-BACKUP-VERIFY','PB-APPLY-FAILED',
                     'PB-ROLLBACK-BLOCKED','PB-MODEL-UNAVAILABLE','PB-SEND-NOTFOUND','PB-SEND-AMBIGUOUS',
                     'PB-SEND-LIMIT','PB-SEND-FAILED','PB-SEND-UNCERTAIN','PB-CHANNEL-FAILED'):
            self.assertIn(code, CATALOG)
            secret = 'secret-token-and-document-name'
            output = io.StringIO()
            with redirect_stderr(output):
                response = user_message(code, stage='test', exc=ValueError(secret))
            incident_id = response.rsplit('incident ', 1)[1]
            self.assertIn(incident_id, output.getvalue())
            self.assertNotIn(secret, output.getvalue() + response)
        self.assertEqual(classify(ValueError('backup verification failed'), stage='apply'), 'PB-BACKUP-VERIFY')

    def test_slack_socket_origin_is_restricted(self):
        slack = Slack('fixture-bot', 'fixture-app')
        for url in ('wss://wss-primary.slack.com/link', 'wss://wss-backup.slack.com/link'):
            slack.call = lambda *_args, **_kwargs: {'url': url}
            self.assertEqual(slack.socket_url(), url)
        for url in ('wss://slack.com.evil.test/link', 'wss://user@wss-primary.slack.com/link',
                    'ws://wss-primary.slack.com/link', 'wss://wss-primary.slack.com:8443/link'):
            slack.call = lambda *_args, **_kwargs: {'url': url}
            with self.assertRaises(ValueError): slack.socket_url()

    def test_sqlite_backup_restore(self):
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'state-backup.py'
        p = self.source()
        plan = self.broker.create_plan('telegram:1', {'version': 2, 'actions': [{'source': p.name,
            'destination': 'Factures/' + p.name, 'expected': fingerprint(p).as_dict()}]}, {'actions': []})
        backup = self.root / 'backup.sqlite3'
        restored = self.root / 'restored.sqlite3'
        first = subprocess.run([sys.executable, str(script), 'backup', '--source', str(self.store.database),
                                '--destination', str(backup)], capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = subprocess.run([sys.executable, str(script), 'restore', '--source', str(backup),
                                 '--destination', str(restored)], capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIsNotNone(PlanStore(restored).get(plan['id']))

    def test_versioned_schema_migration_and_rollback_preserve_legacy_data(self):
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'migrate-state.py'
        with sqlite3.connect(self.store.database) as db:
            db.execute('INSERT INTO learning_events (event_type,source_path,destination,created_at,expires_at) VALUES (?,?,?,?,?)',
                       ('legacy','private-name',None,'2026-10-14','2027-01-14'))
        first = self.root / 'before-upgrade.sqlite3'
        command = [sys.executable, str(script), 'upgrade', '--database', str(self.store.database),
                   '--state', str(self.s), '--backup', str(first)]
        preview = subprocess.run(command + ['--dry-run'], capture_output=True, text=True)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse(first.exists())
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with sqlite3.connect(self.store.database) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT source_path FROM learning_events').fetchone()[0], 'private-name')
        second = self.root / 'before-rollback.sqlite3'
        result = subprocess.run([sys.executable, str(script), 'rollback', '--database', str(self.store.database),
                                 '--state', str(self.s), '--backup', str(second)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with sqlite3.connect(self.store.database) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT source_path FROM learning_events').fetchone()[0], 'private-name')
        self.assertTrue(first.with_name(first.name+'.sha256').exists())

    def test_schema_migration_refuses_active_journal(self):
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'migrate-state.py'
        (self.s/'unfinished.journal.json').write_text(json.dumps({'state':'APPLYING'}))
        backup = self.root/'no-backup.sqlite3'
        result = subprocess.run([sys.executable, str(script), 'upgrade', '--database', str(self.store.database),
                                 '--state', str(self.s), '--backup', str(backup)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(backup.exists())


if __name__ == '__main__': unittest.main()
