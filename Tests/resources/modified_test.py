import unittest
import application


class TestApp(unittest.TestCase):
    def test_success(self):
        result = application.add(2, 2)
        self.assertEqual(4, result)

    def test_all_bad(self):
        # self.assertEqual(year, 1984)
        result = application.add(2, 2)
        self.assertEqual(5, result)

    def test_all_good(self):
        result = application.add(1, 1)
        self.assertEqual(2, result)

if __name__ == '__main__':
    unittest.main()
