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

    def test_invalid_values_and_empty(self):
        with self.assertRaises(ValueError):
            QuantileSketch(0).quantile(.5)
        with self.assertRaises(ValueError):
            QuantileSketch().quantile(.5)
        with self.assertRaises(ValueError):
            QuantileSketch().insert(float('nan'))


if __name__ == '__main__':
    unittest.main()
