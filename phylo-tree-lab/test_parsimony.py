import contextlib
import io
import unittest

from cli import main
from parsimony import Node, fitch_score, parse_newick


class ParsimonyTests(unittest.TestCase):
    def test_classic_two_site_score(self):
        tree = parse_newick("((a:AA,b:AG),c:GG);")
        self.assertEqual(fitch_score(tree), 2)

    def test_polytomy(self):
        self.assertEqual(fitch_score(parse_newick("(a:A,b:C,c:G);")), 2)

    def test_independent_single_site_expectations(self):
        # Hand enumerated: constant sites cost zero; one differing leaf costs one.
        cases = {
            "((a:A,b:A),c:A);": 0,
            "((a:A,b:A),c:C);": 1,
            "((a:A,b:C),c:C);": 1,
            "((a:A,b:C),(c:G,d:T));": 3,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(fitch_score(parse_newick(text)), expected)

    def test_internal_labels_ignored(self):
        self.assertEqual(fitch_score(parse_newick("((a:A,b:C)clade,c:C)root;")), 1)

    def test_rejects_misaligned_and_malformed(self):
        for text in ("(a:AA,b:A);", "(a:AA,b:AA)", "(a:,b:A);", "(a:A,b:A);tail"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_newick(text)

    def test_rejects_single_leaf(self):
        with self.assertRaises(ValueError):
            fitch_score(Node(name="a", sequence="A"))

    def test_cli_stdin_success_and_invalid_input(self):
        import sys
        original = sys.stdin
        try:
            sys.stdin = io.StringIO("(a:A,b:C);")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([]), 0)
            self.assertEqual(output.getvalue(), "1\n")
            sys.stdin = io.StringIO("not a tree")
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                self.assertEqual(main([]), 2)
            self.assertIn("phylo-tree-lab:", errors.getvalue())
        finally:
            sys.stdin = original


if __name__ == "__main__":
    unittest.main()
