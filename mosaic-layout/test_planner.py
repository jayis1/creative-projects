import unittest
from planner import Part, LayoutError, plan, waste_summary


class PlannerTests(unittest.TestCase):
    def test_layout_nonoverlap_and_area(self):
        parts = [Part("A", 6, 4), Part("B", 4, 4), Part("C", 2, 4)]
        placed, free = plan(10, 8, parts)
        self.assertEqual(len(placed), 3)
        for i, a in enumerate(placed):
            for b in placed[i+1:]:
                self.assertFalse(a.x < b.x+b.width and b.x < a.x+a.width and a.y < b.y+b.height and b.y < a.y+a.height)
        stats = waste_summary(10, 8, placed)
        self.assertEqual(stats["used"] + stats["waste"], 80)

    def test_rotation(self):
        placed, _ = plan(3, 5, [Part("wide", 5, 3)])
        self.assertTrue(placed[0].rotated)
        self.assertEqual((placed[0].width, placed[0].height), (3, 5))

    def test_invalid_and_unfit(self):
        with self.assertRaises(LayoutError):
            plan(0, 5, [])
        with self.assertRaises(LayoutError):
            plan(2, 2, [Part("large", 3, 3)])


if __name__ == "__main__":
    unittest.main()
