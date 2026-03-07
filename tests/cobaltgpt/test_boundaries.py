import unittest
from tunersx.cobaltgpt.boundaries import BLOCKED_TOPICS

class T(unittest.TestCase):
    def test_blocked_seed_key(self):
        self.assertIn("seed-key", BLOCKED_TOPICS)

if __name__=="__main__": unittest.main()
