"""Release decisions must use current, matching evidence, never a green badge alone."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_readiness', ROOT / 'scripts/release_readiness.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
COMMIT = 'a' * 40
NOW = datetime(2026, 10, 25, 21, 45, tzinfo=timezone.utc)
STAMP = NOW.isoformat()


def evidence():
    """Synthetic complete technical evidence; never a production authorization."""
    record = {'commit': COMMIT, 'observed_at': STAMP,
              'source': 'https://evidence.example.invalid/verified-record'}
    return {
        'schema_version': 1, 'candidate_commit': COMMIT, 'observed_at': STAMP,
        'github': {**record, 'checks': [
            {'name': name, 'status': 'completed', 'conclusion': 'success'}
            for name in ('source-checks', 'container-build')
        ]},
        'vercel': [{**record, 'project': name, 'state': 'READY',
                    'environment': 'preview', 'readiness': {
                        **record, 'http_status': 200, 'database': 'ok'}}
                   for name in ('wrench-relay', 'wrenchrelay-industrial')],
        'cloudflare': {**record, 'state': 'success', 'scope': 'non-production-version-upload', 'readiness': {
            **record, 'http_status': 200, 'database': 'ok'}},
        'proofs': {name: {**record, 'result': 'passed'} for name in (
            'source_parity', 'storage_compatibility', 'session_compatibility',
            'backup_restore', 'customer_workflows', 'payment_safeguards', 'rollback')},
    }


class ReleaseReadinessTests(unittest.TestCase):
    def assess(self, payload, target='vercel'):
        return gate.evaluate(payload, COMMIT, target, now=NOW)

    def test_complete_evidence_never_authorizes_production(self):
        result = self.assess(evidence())
        self.assertEqual(result['decision'], 'TECHNICAL_CHECKS_PASSED')
        self.assertFalse(result['production_approved'])

    def test_ready_build_cannot_hide_database_failure(self):
        payload = evidence()
        payload['vercel'][0]['readiness'].update(http_status=503, database='not_configured')
        result = self.assess(payload)
        self.assertEqual(result['decision'], 'BLOCKED')
        self.assertIn('vercel:wrench-relay:readiness', result['blockers'])
        self.assertEqual(result['paths']['vercel']['wrench-relay'], 'BUILD_READY')

    def test_wrong_commit_cannot_reuse_success(self):
        for section in ('candidate_commit', 'github', 'vercel', 'proofs'):
            with self.subTest(section=section):
                payload = evidence()
                if section == 'candidate_commit':
                    payload[section] = 'b' * 40
                elif section == 'vercel':
                    payload[section][1]['commit'] = 'b' * 40
                elif section == 'proofs':
                    payload[section]['session_compatibility']['commit'] = 'b' * 40
                else:
                    payload[section]['commit'] = 'b' * 40
                self.assertEqual(self.assess(payload)['decision'], 'BLOCKED')

    def test_each_release_prerequisite_is_required(self):
        for name in list(evidence()['proofs']):
            for change in ('missing', 'unverified', 'no_source'):
                with self.subTest(name=name, change=change):
                    payload = evidence()
                    if change == 'missing':
                        del payload['proofs'][name]
                    elif change == 'unverified':
                        payload['proofs'][name]['result'] = 'unverified'
                    else:
                        payload['proofs'][name]['source'] = ''
                    self.assertEqual(self.assess(payload)['decision'], 'BLOCKED')

    def test_both_named_vercel_projects_are_required(self):
        payload = evidence()
        payload['vercel'].pop()
        self.assertIn('vercel:wrenchrelay-industrial:missing_or_duplicate', self.assess(payload)['blockers'])

    def test_duplicate_deployment_or_ci_result_is_ambiguous(self):
        for field in ('vercel', 'github'):
            with self.subTest(field=field):
                payload = evidence()
                if field == 'vercel':
                    payload[field].append(copy.deepcopy(payload[field][0]))
                else:
                    duplicate = copy.deepcopy(payload['github']['checks'][0])
                    duplicate['conclusion'] = 'failure'
                    payload['github']['checks'].append(duplicate)
                self.assertEqual(self.assess(payload)['decision'], 'BLOCKED')

    def test_pending_or_failed_ci_is_blocked(self):
        for status, conclusion in [('in_progress', None), ('completed', 'failure'), ('completed', 'skipped')]:
            with self.subTest(status=status, conclusion=conclusion):
                payload = evidence()
                payload['github']['checks'][0].update(status=status, conclusion=conclusion)
                self.assertIn('github:source-checks', self.assess(payload)['blockers'])

    def test_cloudflare_does_not_borrow_vercel_success(self):
        for state in ('in_progress', 'failed', 'unknown'):
            with self.subTest(state=state):
                payload = evidence()
                payload['cloudflare']['state'] = state
                result = self.assess(payload, 'cloudflare')
                self.assertEqual(result['decision'], 'BLOCKED')
                self.assertEqual(result['paths']['cloudflare'], state)

    def test_unselected_cloudflare_failure_is_reported_separately(self):
        payload = evidence()
        payload['cloudflare']['state'] = 'failed'
        result = self.assess(payload)
        self.assertEqual(result['decision'], 'TECHNICAL_CHECKS_PASSED')
        self.assertEqual(result['paths']['cloudflare'], 'failed')
        self.assertFalse(result['production_approved'])

    def test_cloudflare_requires_its_own_preview_scope_and_health(self):
        self.assertEqual(self.assess(evidence(), 'cloudflare')['decision'], 'TECHNICAL_CHECKS_PASSED')
        for field, value in [('scope', 'production'), ('readiness', None)]:
            with self.subTest(field=field):
                payload = evidence()
                payload['cloudflare'][field] = value
                self.assertEqual(self.assess(payload, 'cloudflare')['decision'], 'BLOCKED')

    def test_old_future_and_naive_evidence_is_blocked(self):
        for stamp in ((NOW - timedelta(hours=5)).isoformat(),
                      (NOW + timedelta(minutes=6)).isoformat(), '2026-10-25T21:45:00', 'invalid'):
            for location in ('snapshot', 'proof', 'readiness'):
                with self.subTest(stamp=stamp, location=location):
                    payload = evidence()
                    record = payload if location == 'snapshot' else (
                        payload['proofs']['backup_restore'] if location == 'proof'
                        else payload['vercel'][0]['readiness'])
                    record['observed_at'] = stamp
                    self.assertEqual(self.assess(payload)['decision'], 'BLOCKED')

    def test_health_from_another_commit_is_not_readiness(self):
        payload = evidence()
        payload['vercel'][0]['readiness']['commit'] = 'b' * 40
        self.assertEqual(self.assess(payload)['decision'], 'BLOCKED')

    def test_http_200_without_database_ready_is_blocked(self):
        payload = evidence()
        payload['vercel'][0]['readiness']['database'] = 'not_configured'
        self.assertEqual(self.assess(payload)['decision'], 'BLOCKED')

    def test_production_deployment_cannot_masquerade_as_preview(self):
        payload = evidence()
        payload['vercel'][0]['environment'] = 'production'
        self.assertEqual(self.assess(payload)['decision'], 'BLOCKED')

    def test_empty_and_malformed_sections_fail_closed(self):
        for key in ('github', 'vercel', 'proofs'):
            for value in (None, 'success', True):
                with self.subTest(key=key, value=value):
                    payload = evidence()
                    payload[key] = value
                    self.assertEqual(self.assess(payload)['decision'], 'BLOCKED')
        self.assertEqual(self.assess({})['decision'], 'BLOCKED')
        for payload in (None, [], 'READY'):
            with self.assertRaises(ValueError):
                self.assess(payload)

    def test_commit_and_target_must_be_explicit_and_valid(self):
        for commit, target in [('70fb5a7', 'vercel'), (COMMIT, 'other')]:
            with self.assertRaises(ValueError):
                gate.evaluate(evidence(), commit, target, now=NOW)

    def cli(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.json'
            path.write_text(content, encoding='utf-8')
            return subprocess.run([sys.executable, str(ROOT / 'scripts/release_readiness.py'),
                                   str(path), '--commit', COMMIT, '--target', 'vercel'],
                                  text=True, capture_output=True, timeout=5)

    def test_cli_blocks_empty_evidence(self):
        result = self.cli('{}')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['decision'], 'BLOCKED')

    def test_cli_invalid_input_does_not_echo_private_content(self):
        result = self.cli('private-record-that-is-not-json')
        self.assertEqual(result.returncode, 3)
        self.assertNotIn('private-record', result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['decision'], 'INVALID_EVIDENCE')

    def test_cli_complete_current_evidence_passes_technical_checks_only(self):
        payload = evidence()
        current = datetime.now(timezone.utc).isoformat()

        def refresh(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == 'observed_at':
                        value[key] = current
                    else:
                        refresh(item)
            elif isinstance(value, list):
                for item in value:
                    refresh(item)

        refresh(payload)
        result = self.cli(json.dumps(payload))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(json.loads(result.stdout)['production_approved'])


if __name__ == '__main__':
    unittest.main()
