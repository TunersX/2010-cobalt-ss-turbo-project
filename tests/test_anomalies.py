import tempfile
import unittest
from pathlib import Path

from tunersx.core.config import AnomalyConfig
from tunersx.decode.anomalies import detect_anomalies


class AnomalyTests(unittest.TestCase):
    def test_anomaly_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            s = p / "signals.jsonl"
            s.write_text(
                '\n'.join([
                    '{"timestamp":"0.0","channel":"IAT","value":20,"evidence_pointer":{"file":"frames.jsonl","line":1}}',
                    '{"timestamp":"1.0","channel":"IAT","value":50,"evidence_pointer":{"file":"frames.jsonl","line":2}}',
                    '{"timestamp":"2.0","channel":"IAT","value":55,"evidence_pointer":{"file":"frames.jsonl","line":3}}',
                    '{"timestamp":"3.0","channel":"IAT","value":60,"evidence_pointer":{"file":"frames.jsonl","line":4}}',
                ]) + "\n",
                encoding="utf-8",
            )
            a = p / "anomalies.jsonl"
            n, _ = detect_anomalies(s, a, AnomalyConfig())
            self.assertGreaterEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
