import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quantile_sketch import QuantileSketch


class SketchTests(unittest.TestCase):
    def test_monotone_stream_quantiles(self):
        sketch = QuantileSketch(0.01)
        sketch.extend(range(10000))
        for q in (0.1, 0.5, 0.9):
            estimate = sketch.quantile(q)
            self.assertLessEqual(abs(estimate - q * 9999), 150)

    def test_streaming_and_summary_smaller_than_input(self):
        sketch = QuantileSketch(0.01)
        for i in range(10000):
            sketch.insert((i * 7919) % 10007)
        self.assertLess(sketch.summary_size, 10000)
        self.assertEqual(sketch.n, 10000)

    def test_jsonl_cli_streaming(self):
        import contextlib
        import io
        from unittest.mock import patch
        from quantile_sketch import main
        output = io.StringIO()
        with patch('sys.stdin', io.StringIO('1\n2\n3\n')), contextlib.redirect_stdout(output):
            self.assertEqual(main(['--jsonl', '--quantiles', '0.5']), 0)
        self.assertIn('2.0', output.getvalue())

    def test_gzip_jsonl_cli_streaming(self):
        import gzip
        import json
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jsonl.gz") as source:
            with gzip.open(source.name, "wt", encoding="utf-8") as stream:
                stream.write("1\n2\n3\n")
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "quantile_sketch.py"),
                 source.name, "--jsonl", "--quantiles", "0.5"],
                capture_output=True, text=True, check=True,
            )
        self.assertEqual(json.loads(result.stdout)["quantiles"]["0.5"], 2.0)

    def test_duplicate_values_preserve_median(self):
        sketch = QuantileSketch(0.01)
        sketch.extend([4] * 500 + [9] * 500)
        self.assertIn(sketch.quantile(.5), (4.0, 9.0))

    def test_rank_error_across_permuted_stream(self):
        values = [(i * 7919) % 10007 for i in range(10000)]
        sketch = QuantileSketch(0.01)
        sketch.extend(values)
        ordered = sorted(values)
        for q in (0.01, .1, .25, .5, .75, .9, .99):
            estimate = sketch.quantile(q)
            rank = sum(value < estimate for value in values)
            target = q * (len(values) - 1)
            self.assertLessEqual(abs(rank - target), .02 * len(values), (q, rank, target))

    def test_invalid_values_and_empty(self):
        with self.assertRaises(ValueError):
            QuantileSketch(0).quantile(.5)
        with self.assertRaises(ValueError):
            QuantileSketch().quantile(.5)
        with self.assertRaises(ValueError):
            QuantileSketch().insert(float('nan'))
        for value in (True, "4"):
            with self.assertRaises(ValueError):
                QuantileSketch().insert(value)  # type: ignore[arg-type]

    def test_cli_reports_invalid_jsonl_record_and_epsilon(self):
        import contextlib
        import io
        from unittest.mock import patch
        from quantile_sketch import main

        errors = io.StringIO()
        with patch('sys.stdin', io.StringIO('1\ntrue\n')), contextlib.redirect_stderr(errors):
            with self.assertRaises(SystemExit) as result:
                main(['--jsonl', '--quantiles', '0.5'])
        self.assertEqual(result.exception.code, 2)
        self.assertIn('line 2', errors.getvalue())
        self.assertIn('JSON/Python numbers', errors.getvalue())

        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            with self.assertRaises(SystemExit) as result:
                main(['--demo', '--epsilon', '0.5'])
        self.assertEqual(result.exception.code, 2)
        self.assertIn('between 0 and 0.5', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
