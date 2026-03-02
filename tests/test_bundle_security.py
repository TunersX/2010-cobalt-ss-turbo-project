import json
import tempfile
import unittest
from pathlib import Path

from tunersx.audit.integrity import AuditLogger, build_hashes, verify_bundle, write_manifest
from tunersx.integrity.signing import sign_file, verify_file_signature


class BundleSecurityTests(unittest.TestCase):
    def _bundle(self, root: Path):
        (root / 'frames.jsonl').write_text('{"ts":"0.000","monotonic_s":0.0,"can_id":256,"data":[1,2,3,4,5,6,7,8],"dlc":8,"bus":"hs_can"}\n', encoding='utf-8')
        (root / 'signals.jsonl').write_text('', encoding='utf-8')
        (root / 'anomalies.jsonl').write_text('', encoding='utf-8')
        (root / 'audit.jsonl').write_text('', encoding='utf-8')
        audit = AuditLogger(root / 'audit.jsonl')
        audit.log('policy', 'test', 'BOOT', 'session.start', 'ALLOW', {})
        hashes = build_hashes(root, ['frames.jsonl', 'signals.jsonl', 'anomalies.jsonl', 'audit.jsonl'])
        (root / 'hashes.json').write_text(json.dumps(hashes), encoding='utf-8')
        write_manifest(
            root,
            hashes,
            versions={"app_version": "1", "bundle_schema_version": "1.1", "registry_version": "1.1", "dbc_version": "d", "vehicle_profile_version": "1"},
            policy_snapshot={"risk_class": "PASSIVE", "state": "COMPLETE", "armed": False},
            capture_stats={},
            transport_config={"transport": "demo"},
        )

    def test_verify_reports_first_break(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            self._bundle(b)
            (b / 'frames.jsonl').write_text('broken\n', encoding='utf-8')
            ok, payload = verify_bundle(b)
            self.assertFalse(ok)
            self.assertTrue(payload['errors'][0].startswith('frames_schema:'))

    def test_signature_valid_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            self._bundle(b)
            key = b / 'key.txt'
            key.write_text('secret', encoding='utf-8')
            sig = sign_file(b / 'manifest.json', key)
            valid, _ = verify_file_signature(b / 'manifest.json', sig, key)
            self.assertTrue(valid)
            manifest = json.loads((b / 'manifest.json').read_text(encoding='utf-8'))
            manifest['capture_stats'] = {'tampered': True}
            (b / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            valid2, status = verify_file_signature(b / 'manifest.json', sig, key)
            self.assertFalse(valid2)
            self.assertEqual(status, 'invalid')


if __name__ == '__main__':
    unittest.main()
