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
    def test_window_cli_json(self):
        import json, subprocess, sys
        proc = subprocess.run([sys.executable, 'entropy_lab.py', '--json', '--window', '2'],
                              input='aabb', text=True, capture_output=True, check=True)
        data = json.loads(proc.stdout)
        self.assertAlmostEqual(data['mean_window_entropy'], 0.0)
        self.assertEqual(data['window_size'], 2)
    def test_window_rejects_negative(self):
        import subprocess, sys
        proc = subprocess.run([sys.executable, 'entropy_lab.py', '--window', '-1'],
                              input='', text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)

if __name__ == '__main__':
    unittest.main()
