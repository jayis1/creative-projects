import json
import subprocess
import sys
import unittest
from pathlib import Path
from planner import Part, LayoutError, plan, waste_summary


class PlannerTests(unittest.TestCase):
    def test_layout_nonoverlap_and_area(self):
        parts = [Part("A", 6, 4), Part("B", 4, 4), Part("C", 2, 4)]
        placed, _ = plan(10, 8, parts)
        self.assertEqual(len(placed), 3)
        for i, a in enumerate(placed):
            for b in placed[i+1:]:
                self.assertFalse(a.x < b.x+b.width and b.x < a.x+a.width and a.y < b.y+b.height and b.y < a.y+a.height)
        stats = waste_summary(10, 8, placed)
        self.assertEqual(stats["used"] + stats["waste"], 80)

    def test_rotation_and_no_rotation(self):
        placed, _ = plan(3, 5, [Part("wide", 5, 3)])
        self.assertTrue(placed[0].rotated)
        with self.assertRaises(LayoutError):
            plan(3, 5, [Part("wide", 5, 3)], allow_rotation=False)

    def test_invalid_and_unfit(self):
        with self.assertRaises(LayoutError):
            plan(0, 5, [])
        with self.assertRaises(LayoutError):
            plan(2, 2, [Part("large", 3, 3)])
        with self.assertRaises(LayoutError):
            plan(8, 8, [Part("bad", 1, 1, 0)])

    def test_cli_json_report(self):
        script = Path(__file__).with_name("main.py")
        result = subprocess.run([sys.executable, str(script), "5", "3", "panel:5:3", "--json"], check=True, capture_output=True, text=True)
        report = json.loads(result.stdout)
        self.assertEqual(report["summary"]["used"], 15)
        self.assertEqual(report["placements"][0]["name"], "panel")

    def test_waste_summary_rejects_invalid_sheet_dimensions(self):
        with self.assertRaises(LayoutError):
            waste_summary(0, 5, [])
        with self.assertRaises(LayoutError):
            waste_summary(-1, 5, [])


if __name__ == "__main__":
    unittest.main()
