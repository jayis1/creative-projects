import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import learn


class GrammarTests(unittest.TestCase):
    def test_learn_and_seeded_sample(self):
        grammar = learn(["red birds fly", "small birds fly", "red birds sing"])
        self.assertGreater(grammar.rule_count, 0)
        self.assertEqual(grammar.sample(seed=7), grammar.sample(seed=7))

    def test_empty_corpus_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            learn([])

    def test_empty_sentences_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one token"):
            learn(["  "])

    def test_reserved_separator_rejected(self):
        with self.assertRaisesRegex(ValueError, "reserved separator"):
            learn(["alpha\\x1fbeta"])

    def test_sample_bounds(self):
        with self.assertRaises(ValueError):
            learn(["a"]).sample(max_tokens=0)


if __name__ == "__main__":
    unittest.main()
