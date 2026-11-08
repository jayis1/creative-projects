import cmath
import unittest
from newton_fractal import ascii_art, classify, evaluate, load_config, ppm_bytes, render

class NewtonFractalTests(unittest.TestCase):
    def setUp(self):
        self.coeffs = (1, 0, 0, -1)
        self.roots = (1+0j, cmath.exp(2j*cmath.pi/3), cmath.exp(4j*cmath.pi/3))

    def test_json_config_supports_complex_pairs(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "poly.json"
            path.write_text('{"coefficients":[1,0,-1],"roots":[1,[-1,0]]}', encoding="utf-8")
            coefficients, roots = load_config(path)
            self.assertEqual(coefficients, (1+0j, 0j, -1+0j))
            self.assertEqual(roots, (1+0j, -1+0j))

    def test_json_config_rejects_missing_keys_and_nonfinite_values(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for text in ('{"coefficients":[1,0],"roots":[]}',
                         '{"coefficients":[1,0],"roots":[[NaN,0]]}'):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_evaluate_horner_value_and_derivative(self):
        value, derivative = evaluate((1, 0, 0, -1), 2)
        self.assertEqual(value, 7)
        self.assertEqual(derivative, 12)

    def test_cubic_roots_classify(self):
        for index, root in enumerate(self.roots):
            self.assertEqual(classify(root, self.coeffs, self.roots).basin, index)

    def test_singular_derivative_is_unresolved(self):
        self.assertEqual(classify(0j, self.coeffs, self.roots).basin, -1)

    def test_render_dimensions_and_ascii_determinism(self):
        rows = render(7, 5, (-1, 1, -1, 1), self.coeffs, self.roots)
        self.assertEqual((len(rows), len(rows[0])), (5, 7))
        self.assertEqual(ascii_art(rows), ascii_art(rows))

    def test_ppm_header_and_payload(self):
        image = ppm_bytes(render(3, 2, (-1, 1, -1, 1), self.coeffs, self.roots))
        self.assertTrue(image.startswith(b"P6\n3 2\n255\n"))
        self.assertEqual(len(image), len(b"P6\n3 2\n255\n") + 18)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError): classify(0j, (1,), self.roots)
        with self.assertRaises(ValueError): classify(0j, self.coeffs, self.roots, damping=0)
        with self.assertRaises(ValueError): render(0, 4, (-1, 1, -1, 1), self.coeffs, self.roots)
        with self.assertRaises(ValueError): render(2, 2, (float("nan"), 1, -1, 1), self.coeffs, self.roots)

if __name__ == "__main__":
    unittest.main()
