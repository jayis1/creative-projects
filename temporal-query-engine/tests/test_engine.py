import json
import tempfile
import unittest
from pathlib import Path

from temporal_query import Event, IntervalIndex, Relation, load_events


class TemporalTests(unittest.TestCase):
    def test_allen_relations(self):
        a = Event("a", 0, 2)
        b = Event("b", 2, 4)
        c = Event("c", 1, 3)
        self.assertIs(a.relation_to(b), Relation.MEETS)
        self.assertIs(a.relation_to(c), Relation.OVERLAPS)
        self.assertIs(c.relation_to(a), Relation.OVERLAPPED_BY)

    def test_index_prunes_and_orders(self):
        idx = IntervalIndex([Event("late", 10, 20), Event("early", 1, 4), Event("mid", 3, 8)])
        self.assertEqual([e.id for e in idx.overlaps(2, 5)], ["early", "mid"])
        self.assertEqual([e.id for e in idx.overlaps(2, 5, label="x")], [])
        idx.add(Event("tagged", 2, 6, "x"))
        self.assertEqual([e.id for e in idx.overlaps(2, 5, label="x")], ["tagged"])

    def test_duplicate_and_invalid(self):
        idx = IntervalIndex()
        idx.add(Event("x", 0, 1))
        with self.assertRaises(ValueError): idx.add(Event("x", 2, 3))
        with self.assertRaises(ValueError): idx.overlaps(2, 1)
        with self.assertRaises(ValueError): Event("nan", float("nan"), 1)
        with self.assertRaises(ValueError): Event("inf", 0, float("inf"))

    def test_remove(self):
        idx = IntervalIndex([Event("x", 0, 1)])
        self.assertEqual(idx.remove("x").id, "x")
        with self.assertRaises(KeyError): idx.remove("x")

    def test_json_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(json.dumps({"events": [{"id": "a", "start": 1, "end": 2}]}), encoding="utf-8")
            self.assertEqual(load_events(path), [Event("a", 1, 2)])

    def test_configuration_errors_are_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "events"):
                load_events(path)


if __name__ == "__main__":
    unittest.main()
