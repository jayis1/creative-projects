import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from cli import main


class CliTests(unittest.TestCase):
    def test_example_emits_route_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["example.json"]), 0)
        result = json.loads(output.getvalue())
        self.assertTrue(result["reachable"])
        self.assertEqual(result["path"][0], [0, 0])

    def test_invalid_scenario_is_clean_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{}", encoding="utf-8")
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                self.assertEqual(main([str(path)]), 2)
            self.assertIn("scenario must contain", errors.getvalue())


if __name__ == '__main__':
    unittest.main()
