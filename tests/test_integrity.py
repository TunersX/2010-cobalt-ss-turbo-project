import json
import tempfile
import unittest
from pathlib import Path

from tunersx.audit.integrity import AuditLogger, build_hashes, verify_bundle, write_manifest


class IntegrityTests(unittest.TestCase):
    def _make_valid_bundle(self, root: Path) -> None:
        frames = [
            {
                "ts": "0.000",
                "monotonic_s": 0.0,
                "can_id": 0x100,
                "data": [1, 2, 3, 4, 5, 6, 7, 8],
                "dlc": 8,
                "bus": "hs_can",
            }
        ]
        with (root / "frames.jsonl").open("w", encoding="utf-8") as f:
            for row in frames:
                f.write(json.dumps(row) + "\n")
        (root / "signals.jsonl").write_text("", encoding="utf-8")
        (root / "anomalies.jsonl").write_text("", encoding="utf-8")
        (root / "audit.jsonl").write_text("", encoding="utf-8")

        audit = AuditLogger(root / "audit.jsonl")
        audit.log("policy", "test", "BOOT", "session.start", "ALLOW", {"rule": "POL-001"})

        hashes = build_hashes(root, ["frames.jsonl", "signals.jsonl", "anomalies.jsonl", "audit.jsonl"])
        (root / "hashes.json").write_text(json.dumps(hashes), encoding="utf-8")
        write_manifest(
            root,
            hashes,
            versions={
                "app_version": "1.0.0",
                "bundle_schema_version": "1.1",
                "registry_version": "1.1",
                "dbc_version": "builtin-demo-1.1",
                "vehicle_profile_version": "1.0",
            },
            policy_snapshot={"risk_class": "PASSIVE", "state": "COMPLETE", "armed": False},
            capture_stats={"drop_count": 0},
            transport_config={"transport": "demo"},
        )

    def test_audit_chain_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            self._make_valid_bundle(b)
            ok, payload = verify_bundle(b)
            self.assertTrue(ok, payload)

    def test_verify_fails_when_frames_schema_tampered(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            self._make_valid_bundle(b)
            (b / "frames.jsonl").write_text('{"ts":1,"can_id":"bad"}\n', encoding="utf-8")
            ok, payload = verify_bundle(b)
            self.assertFalse(ok)
            self.assertTrue(any(err.startswith("frames_schema:") for err in payload["errors"]))

    def test_verify_fails_when_audit_schema_tampered(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            self._make_valid_bundle(b)
            bad = {
                "ts": "2026-01-01T00:00:00.000+00:00",
                "event_type": "policy",
                "actor": "test",
                "state": "BOOT",
                "command_id": "session.start",
                "result": "ALLOW",
                "details": {"rule": "POL-001"},
                "prev_hash": "0" * 64,
            }
            (b / "audit.jsonl").write_text(json.dumps(bad) + "\n", encoding="utf-8")
            ok, payload = verify_bundle(b)
            self.assertFalse(ok)
            self.assertTrue(any(err.startswith("audit_schema:") for err in payload["errors"]))

    def test_verify_fails_when_manifest_schema_tampered(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            self._make_valid_bundle(b)
            manifest = json.loads((b / "manifest.json").read_text(encoding="utf-8"))
            manifest["software"].pop("registry_version")
            (b / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            ok, payload = verify_bundle(b)
            self.assertFalse(ok)
            self.assertTrue(any(err.startswith("manifest_schema:") for err in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
