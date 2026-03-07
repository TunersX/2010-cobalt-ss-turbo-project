import unittest
from tunersx.cobaltgpt.fault_explainer import explain

class T(unittest.TestCase):
    def test_explain(self):
        self.assertIn("P0300", explain("P0300"))

if __name__=="__main__": unittest.main()
