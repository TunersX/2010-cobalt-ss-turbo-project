import tempfile
import unittest
from pathlib import Path

from tunersx.core.config import DecodeConfig
from tunersx.decode.dbc_loader import load_dbc_map
from tunersx.decode.pipeline import decode_frames_to_signals


class DecodeTests(unittest.TestCase):
    def test_decode_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            frames = p / "frames.jsonl"
            frames.write_text('{"ts":"0.0","can_id":256,"dlc":8,"data":[80,0,0,0,0,0,0,0]}\n', encoding="utf-8")
            out = p / "signals.jsonl"
            dbc, _ = load_dbc_map(None)
            stats = decode_frames_to_signals(frames, out, dbc, DecodeConfig())
            self.assertGreaterEqual(stats["decoded_signals"], 1)


if __name__ == "__main__":
    unittest.main()
