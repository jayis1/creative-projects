import unittest
from pathlab import analyze, analyze_svg, flatten, parse_path

class PathLabTests(unittest.TestCase):
    def test_relative_repeated_commands_and_close(self):
        segs=parse_path("M1 2 l3 0 0 4 z")
        self.assertEqual(len(segs),4)
        self.assertEqual(segs[-1].points[-1],(1.0,2.0))
    def test_horizontal_vertical(self):
        self.assertEqual(flatten(parse_path("M0 0 H4 v3")),[(0,0),(4,0),(4,3)])
    def test_smooth_cubic_reflects_control(self):
        self.assertEqual(parse_path("M0 0 C1 0 2 0 3 0 S5 0 6 0")[-1].points[1],(4.0,0.0))
    def test_smooth_quadratic_reflects_control(self):
        self.assertEqual(parse_path("M0 0 Q1 2 2 0 T4 0")[-1].points[1],(3.0,-2.0))
    def test_analysis_line(self):
        r=analyze("M0 0 L3 4")
        self.assertEqual(r["bounds"],(0.0,0.0,3.0,4.0))
        self.assertEqual(r["length"],5.0)
    def test_empty_path(self):
        self.assertIsNone(analyze("")["bounds"])
    def test_malformed_or_unsupported(self):
        for data in ("M0 0 @","M0 0 A1 1 0 0 0 2 2","L1 2"):
            with self.subTest(data=data),self.assertRaises(ValueError): parse_path(data)
    def test_curve_endpoints(self):
        pts=flatten(parse_path("M0 0 Q2 4 4 0"),8)
        self.assertEqual((len(pts),pts[-1]),(9,(4.0,0.0)))
    def test_steps_bounded_integer(self):
        for value in (0,10001,1.5,True):
            with self.subTest(value=value),self.assertRaises(ValueError): flatten(parse_path("M0 0 L1 1"),value)
    def test_analyze_svg_namespaced_multiple_paths(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg"><path id="a" d="M0 0 L3 4"/><g><path d="M1 1 H2"/></g></svg>'
        result=analyze_svg(svg)
        self.assertEqual([item["id"] for item in result],["a",None])
        self.assertEqual(result[0]["length"],5.0)
    def test_analyze_svg_rejects_malformed_or_empty_document(self):
        for source in ("<svg>","<svg/>"):
            with self.subTest(source=source),self.assertRaises(ValueError): analyze_svg(source)
    def test_move_to_starts_new_subpath_without_connector(self):
        result=analyze("M0 0 L1 0 M100 100 L101 100")
        self.assertEqual(result["length"],2.0)
        self.assertEqual(result["bounds"],(0.0,0.0,101.0,100.0))
    def test_relative_coordinate_overflow_rejected(self):
        with self.assertRaises(ValueError): parse_path("M1e308 0 l1e308 0")
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError): parse_path("M 0 1e999")

if __name__ == "__main__": unittest.main()
