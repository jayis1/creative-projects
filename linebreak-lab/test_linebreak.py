import unittest
from linebreak import balanced_wrap, greedy_wrap


class LayoutTests(unittest.TestCase):
    def test_empty_and_single_word(self):
        self.assertEqual(balanced_wrap("", 5), [])
        self.assertEqual(balanced_wrap("one", 5), ["one"])

    def test_balanced_respects_width_and_preserves_words(self):
        lines = balanced_wrap("alpha beta gamma delta", 10)
        self.assertEqual(" ".join(lines), "alpha beta gamma delta")
        self.assertTrue(all(len(line) <= 10 for line in lines))

    def test_unicode_display_width(self):
        self.assertEqual(greedy_wrap("A 界 B", 4), ["A 界", "B"])

    def test_invalid_width_and_long_word(self):
        for width in (0, -1):
            with self.assertRaises(ValueError):
                balanced_wrap("x", width)
        with self.assertRaises(ValueError):
            balanced_wrap("toolong", 3)


if __name__ == "__main__":
    unittest.main()
