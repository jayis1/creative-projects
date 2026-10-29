import math
import unittest
from entropy_lab import analyze

class EntropyTests(unittest.TestCase):
    def test_uniform_binary(self):
        self.assertAlmostEqual(analyze('ab')['entropy'], 1.0)
    def test_constant_and_empty(self):
        self.assertEqual(analyze('xxxx')['entropy'], 0.0)
        self.assertEqual(analyze('')['entropy'], 0.0)
    def test_unicode_is_counted_as_codepoints(self):
        self.assertEqual(analyze('🙂🙂a')['frequencies']['🙂'], 2)

if __name__ == '__main__':
    unittest.main()
