import unittest

from tunersx.transports.logging import CANLogFramework


class CanLoggingTests(unittest.TestCase):
    def test_summary_stats(self):
        fw = CANLogFramework()
        fw.ingest({"bus": "hs_can", "can_id": 0x100})
        fw.ingest({"bus": "hs_can", "can_id": 0x100})
        fw.ingest({"bus": "hs_can", "can_id": 0x101})
        summary = fw.summary(seconds=1)
        self.assertEqual(summary["buses"]["hs_can"]["frame_count"], 3)
        self.assertEqual(summary["id_histogram"]["0x100"], 2)


if __name__ == "__main__":
    unittest.main()
