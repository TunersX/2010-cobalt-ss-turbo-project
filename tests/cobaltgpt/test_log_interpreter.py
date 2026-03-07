import unittest
from tunersx.cobaltgpt.log_interpreter import interpret

class T(unittest.TestCase):
    def test_interpret(self):
        self.assertIn("summary", interpret({}))

if __name__=="__main__": unittest.main()
