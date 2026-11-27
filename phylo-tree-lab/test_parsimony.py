import unittest
from parsimony import Node, fitch_score, parse_newick


class ParsimonyTests(unittest.TestCase):
    def test_classic_two_site_score(self):
        tree = parse_newick("((a:AA,b:AG),c:GG);")
        self.assertEqual(fitch_score(tree), 2)

    def test_polytomy(self):
        self.assertEqual(fitch_score(parse_newick("(a:A,b:C,c:G);")), 2)

    def test_rejects_misaligned_and_malformed(self):
        with self.assertRaises(ValueError):
            parse_newick("(a:AA,b:A);")
        with self.assertRaises(ValueError):
            parse_newick("(a:AA,b:AA)")

    def test_rejects_single_leaf(self):
        with self.assertRaises(ValueError):
            fitch_score(Node(name="a", sequence="A"))


if __name__ == "__main__":
    unittest.main()
