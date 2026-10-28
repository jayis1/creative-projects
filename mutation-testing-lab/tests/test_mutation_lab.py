import json
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mutation_lab import candidates

class MutationTests(unittest.TestCase):
    def test_strings_and_comments_are_ignored(self):
        source = 'x = "a < b"  # x != y\nif x <= 3 and True:\n    pass\n'
        self.assertEqual([item[3] for item in candidates(source)], ["<=", "and", "True"])

    def test_empty_source_has_no_candidates(self):
        self.assertEqual(candidates(""), [])

    def test_each_edit_is_local(self):
        source = 'if a == b:\n    return False\n'
        edits = candidates(source)
        self.assertEqual(len(edits), 2)
        start, end, replacement, _ = edits[0]
        self.assertEqual(source[:start] + replacement + source[end:], 'if a != b:\n    return False\n')

    def test_runner_json_and_timeout_options(self):
        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run([sys.executable, str(root / "mutation_lab.py"), str(Path(__file__).resolve()), "--tests", str(Path(__file__).parent), "--json", "--timeout", "5"], capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(result["total"], result["killed"] + result["survived"])
        self.assertIn("skipped_syntax", result)
        self.assertEqual(len(result["mutants"]), result["total"] + result["skipped_syntax"])
        self.assertTrue(all(item["status"] in {"KILLED", "SURVIVED", "SKIPPED_SYNTAX"} for item in result["mutants"]))
        self.assertTrue(all(isinstance(item["line"], int) and item["line"] > 0 for item in result["mutants"]))

if __name__ == "__main__":
    unittest.main()
