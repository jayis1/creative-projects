import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mutation_lab import candidates

class MutationTests(unittest.TestCase):
    def test_strings_and_comments_are_ignored(self):
        source = 'x = "a < b"  # x != y\nif x <= 3 and True:\n    pass\n'
        self.assertEqual([item[3] for item in candidates(source)], ["<=", "and", "True"])

    def test_each_edit_is_local(self):
        source = 'if a == b:\n    return False\n'
        edits = candidates(source)
        self.assertEqual(len(edits), 2)
        start, end, replacement, _ = edits[0]
        self.assertEqual(source[:start] + replacement + source[end:], 'if a != b:\n    return False\n')

if __name__ == "__main__":
    unittest.main()
