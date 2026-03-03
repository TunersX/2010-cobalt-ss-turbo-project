import tempfile
import unittest
from pathlib import Path

from tunersx.decode.dbc_loader import load_dbc_map


class DbcParserTests(unittest.TestCase):
    def test_parse_minimal_dbc(self):
        dbc = '''BO_ 256 MSG: 8 ECU\n SG_ IAT : 0|8@1+ (0.5,0) [0|200] "degC" ECU\n'''
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.dbc"
            p.write_text(dbc, encoding="utf-8")
            m, ver = load_dbc_map(str(p))
            self.assertIn("0x100", m)
            self.assertEqual(m["0x100"][0]["channel"], "IAT")


if __name__ == "__main__":
    unittest.main()
