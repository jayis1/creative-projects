import math
import unittest
from entropy_lab import analyze

class EntropyTests(unittest.TestCase):
    def test_uniform_binary(self):
        result = analyze('ab')
        self.assertAlmostEqual(result['entropy'], 1.0)
        self.assertAlmostEqual(result['normalized_entropy'], 1.0)
        self.assertAlmostEqual(result['effective_symbols'], 2.0)
    def test_biased_distribution_metrics(self):
        result = analyze('aaaab')
        self.assertAlmostEqual(result['normalized_entropy'], result['entropy'])
        self.assertAlmostEqual(result['effective_symbols'], 2 ** result['entropy'])
    def test_constant_and_empty(self):
        self.assertEqual(analyze('xxxx')['entropy'], 0.0)
        self.assertEqual(analyze('xxxx')['normalized_entropy'], 0.0)
        self.assertEqual(analyze('xxxx')['effective_symbols'], 1.0)
        self.assertEqual(analyze('')['entropy'], 0.0)
        self.assertEqual(analyze('')['effective_symbols'], 1.0)
    def test_unicode_is_counted_as_codepoints(self):
        self.assertEqual(analyze('🙂🙂a')['frequencies']['🙂'], 2)
    def test_window_cli_json(self):
        import json, subprocess, sys
        proc = subprocess.run([sys.executable, 'entropy_lab.py', '--json', '--window', '2'],
                              input='aabb', text=True, capture_output=True, check=True)
        data = json.loads(proc.stdout)
        self.assertAlmostEqual(data['mean_window_entropy'], 0.0)
        self.assertEqual(data['window_size'], 2)
        self.assertEqual(data['normalized_entropy'], 1.0)
        self.assertEqual(data['effective_symbols'], 2.0)
    def test_window_includes_partial_final_chunk_and_empty_input(self):
        import json, subprocess, sys
        def run(text):
            proc = subprocess.run([sys.executable, 'entropy_lab.py', '--json', '--window', '2'],
                                  input=text, text=True, capture_output=True, check=True)
            return json.loads(proc.stdout)
        self.assertAlmostEqual(run('aab')['mean_window_entropy'], 0.0)
        self.assertEqual(run('')['mean_window_entropy'], 0.0)
    def test_invalid_analysis_type(self):
        with self.assertRaises(TypeError):
            analyze(None)  # type: ignore[arg-type]
    def test_window_rejects_negative(self):
        import subprocess, sys
        proc = subprocess.run([sys.executable, 'entropy_lab.py', '--window', '-1'],
                              input='', text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)

if __name__ == '__main__':
    unittest.main()
