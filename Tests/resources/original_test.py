import unittest
import application


class TestApplication(unittest.TestCase):
    def test_nothing(self):
        return True

    def test_add(self):
        result = application.add(1, 1)
        self.assertEqual(2, result)

if __name__ == '__main__':
    unittest.main()
