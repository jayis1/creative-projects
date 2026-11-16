import unittest
import json
import subprocess
import sys
from pathlib import Path
from main import Exam, check_schedule, conflicts, schedule, schedule_report, validate_input

class TimetableTests(unittest.TestCase):
    def setUp(self):
        self.exams=validate_input({"exams":[{"name":"A","students":["1","2"]},{"name":"B","students":["2","3"]},{"name":"C","students":["3","4"]},{"name":"D","students":[]}]})
    def test_conflict_graph_and_coloring(self):
        graph=conflicts(self.exams)
        self.assertEqual(graph["A"],{"B"})
        result=schedule(self.exams,2)
        self.assertEqual(check_schedule(self.exams,result),[])
        self.assertEqual(result["A"],result["C"])
    def test_impossible_slot_limit(self):
        with self.assertRaises(ValueError): schedule(self.exams[:2],1)
    def test_checker_rejects_non_integer_and_negative_slots(self):
        self.assertTrue(check_schedule(self.exams,{"A":-1,"B":1,"C":2,"D":3}))
        self.assertTrue(check_schedule(self.exams,{"A":0.5,"B":1,"C":2,"D":3}))
    def test_empty_problem(self): self.assertEqual(schedule([],None),{})
    def test_report_includes_empty_slots(self):
        report=schedule_report(self.exams,{"A":0,"B":1,"C":0,"D":2})
        self.assertEqual(report["slot_count"],3)
        self.assertEqual(report["slots"][0],["A","C"])
        self.assertEqual(report["exam_count"],4)
    def test_duplicate_name(self):
        with self.assertRaisesRegex(ValueError,"duplicate"): validate_input({"exams":[{"name":"A","students":[]},{"name":"A","students":[]}]})
    def test_bad_shape(self):
        with self.assertRaises(ValueError): validate_input({"exams":"bad"})
    def test_cli_report_mode(self):
        project = Path(__file__).parent
        result = subprocess.run(
            [sys.executable, str(project / "main.py"), "--report"],
            cwd=project, capture_output=True, text=True, check=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["exam_count"], 4)
        self.assertEqual(sum(len(names) for names in report["slots"].values()), 4)
if __name__=="__main__": unittest.main()
