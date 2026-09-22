import unittest
from temporal_query import Event, IntervalIndex, Relation

class TemporalTests(unittest.TestCase):
    def test_allen_relations(self):
        a=Event('a',0,2); b=Event('b',2,4); c=Event('c',1,3)
        self.assertIs(a.relation_to(b), Relation.MEETS)
        self.assertIs(a.relation_to(c), Relation.OVERLAPS)
        self.assertIs(c.relation_to(a), Relation.OVERLAPPED_BY)
    def test_index_prunes_and_orders(self):
        idx=IntervalIndex([Event('late',10,20),Event('early',1,4),Event('mid',3,8)])
        self.assertEqual([e.id for e in idx.overlaps(2,5)], ['early','mid'])
    def test_duplicate_and_invalid(self):
        idx=IntervalIndex(); idx.add(Event('x',0,1))
        with self.assertRaises(ValueError): idx.add(Event('x',2,3))
        with self.assertRaises(ValueError): idx.overlaps(2,1)
    def test_remove(self):
        idx=IntervalIndex([Event('x',0,1)])
        self.assertEqual(idx.remove('x').id,'x')
        with self.assertRaises(KeyError): idx.remove('x')
if __name__ == '__main__': unittest.main()
