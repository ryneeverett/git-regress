import unittest
import application


class TestApplication(unittest.TestCase):
    def test_add_twos(self):
        result = application.add(2, 2)
        self.assertEqual(4, result)

if __name__ == '__main__':
    unittest.main()
