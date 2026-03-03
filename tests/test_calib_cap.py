import json
import tempfile
import unittest
from pathlib import Path

from tunersx.calib.cap import diff_calibrations, pack_calibration, verify_calibration


class CalibCapTests(unittest.TestCase):
    def test_pack_verify_diff(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bin_a = root / "a.bin"
            bin_b = root / "b.bin"
            bin_a.write_bytes(b"AAAA")
            bin_b.write_bytes(b"BBBB")

            cap_a = pack_calibration(bin_a, root / "cap_a", {"vin": "VIN1"})
            cap_b = pack_calibration(bin_b, root / "cap_b", {"vin": "VIN1"})

            ok, report = verify_calibration(cap_a)
            self.assertTrue(ok, report)

            diff = diff_calibrations(cap_a, cap_b)
            self.assertTrue(diff["changed"])

    def test_verify_detects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bin_a = root / "a.bin"
            bin_a.write_bytes(b"AAAA")
            cap_a = pack_calibration(bin_a, root / "cap", {"vin": "VIN2"})
            payload = next((cap_a / "payload").iterdir())
            payload.write_bytes(b"CCCC")
            ok, report = verify_calibration(cap_a)
            self.assertFalse(ok)
            self.assertTrue(any(e.startswith("hash_mismatch:") for e in report["errors"]))


if __name__ == "__main__":
    unittest.main()
