import unittest

from tunersx.health.scoring import compute_engine_health


class HealthScoringTests(unittest.TestCase):
    def test_health_scoring_prototype(self):
        signals = [{"channel": "IAT"}, {"channel": "KR"}, {"channel": "FUEL_PRESSURE_ACTUAL"}]
        anomalies = [{"severity": "MED"}, {"severity": "HIGH"}]
        report = compute_engine_health(signals, anomalies)
        self.assertIn("score", report)
        self.assertIn(report["tier"], {"GOOD", "WATCH", "CRITICAL"})


if __name__ == "__main__":
    unittest.main()
