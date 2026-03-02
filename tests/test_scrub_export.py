import json
import tempfile
import unittest
from pathlib import Path

from tunersx.export.compliance import export_compliance
from tunersx.privacy.scrub import scrub_bundle


class ScrubExportTests(unittest.TestCase):
    def test_scrub_removes_vin(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td) / 'b'
            b.mkdir()
            (b / 'manifest.json').write_text(json.dumps({"VIN": "123", "software": {}, "files": [], "generated_at": "x", "policy_snapshot": {}, "transport_config": {}, "capture_stats": {}}), encoding='utf-8')
            for f in ['frames.jsonl','signals.jsonl','anomalies.jsonl','audit.jsonl','hashes.json']:
                (b / f).write_text('{}\n' if f.endswith('jsonl') else '{}', encoding='utf-8')
            out = Path(td) / 'out'
            scrub_bundle(b, out, 'public')
            self.assertIn('REDACTED', (out / 'manifest.json').read_text(encoding='utf-8'))
            self.assertTrue((out / 'scrub_manifest.json').exists())

    def test_compliance_export_files(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td) / 'b'
            b.mkdir()
            (b / 'manifest.json').write_text(json.dumps({"software": {"bundle_schema_version": "1.1"}, "generated_at": "x", "policy_snapshot": {}, "transport_config": {}, "capture_stats": {}, "files": []}), encoding='utf-8')
            for f in ['frames.jsonl','signals.jsonl','anomalies.jsonl','audit.jsonl']:
                (b / f).write_text('', encoding='utf-8')
            (b / 'hashes.json').write_text('{}', encoding='utf-8')
            out = Path(td) / 'compliance'
            export_compliance(b, out)
            for f in ['verification_report.json','policy_snapshot.json','registry_versions.json','environment.json','run_summary.md']:
                self.assertTrue((out / f).exists())


if __name__ == '__main__':
    unittest.main()
