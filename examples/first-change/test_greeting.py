import unittest

from greeting import greet


class GreetingTest(unittest.TestCase):
    def test_default_greeting(self):
        self.assertEqual(greet(), "Hello!")


if __name__ == "__main__":
    unittest.main()
