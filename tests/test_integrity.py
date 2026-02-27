import json
import tempfile
import unittest
from pathlib import Path

from tunersx.audit.integrity import AuditLogger, build_hashes, verify_bundle


class IntegrityTests(unittest.TestCase):
    def test_audit_chain_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            for name in ["frames.jsonl", "signals.jsonl", "anomalies.jsonl", "audit.jsonl"]:
                (b / name).write_text("", encoding="utf-8")
            a = AuditLogger(b / "audit.jsonl")
            a.log("policy", "test", "BOOT", "session.start", "ALLOW", {"x": 1})
            hashes = build_hashes(b, ["frames.jsonl", "signals.jsonl", "anomalies.jsonl", "audit.jsonl"])
            (b / "hashes.json").write_text(json.dumps(hashes), encoding="utf-8")
            (b / "manifest.json").write_text(json.dumps({"software": {"bundle_schema_version": "1.1"}}), encoding="utf-8")
            ok, payload = verify_bundle(b)
            self.assertTrue(ok, payload)


if __name__ == "__main__":
    unittest.main()
