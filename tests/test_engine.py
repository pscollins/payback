import unittest

from engine.engine import Engine, Person
from utils import easylogger

LOG = easylogger.LOG

class TestEngine(unittest.TestCase):
    TEST_TO = Person("+19175961426", "FooA")
    TEST_FROM = Person("+15005550006", "FooB")
    TEST_AMT = 1500

    def setUp(self):
        self.engine = Engine()

    def test_send_auth_text(self):
        self.engine.send_auth_text(self.TEST_AMT, self.TEST_TO,
                                   self.TEST_FROM)

if __name__ == "__main__":
    unittest.main()
