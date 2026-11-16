import unittest
from main import Exam, check_schedule, conflicts, schedule, validate_input

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
    def test_empty_problem(self): self.assertEqual(schedule([],None),{})
    def test_duplicate_name(self):
        with self.assertRaisesRegex(ValueError,"duplicate"): validate_input({"exams":[{"name":"A","students":[]},{"name":"A","students":[]}]})
    def test_bad_shape(self):
        with self.assertRaises(ValueError): validate_input({"exams":"bad"})
if __name__=="__main__": unittest.main()
