import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ledger import Ledger, LedgerError

class LedgerTests(unittest.TestCase):
    def test_replay_and_transfer(self):
        l=Ledger(); l.append({'id':'a','account':'cash','amount':900}); l.transfer('t','cash','bank',250)
        self.assertEqual(l.balances,{'cash':650,'bank':250}); self.assertTrue(l.verify())
    def test_duplicate_id_rejected(self):
        l=Ledger(); e={'id':'x','account':'a','amount':1}; l.append(e)
        with self.assertRaises(LedgerError): l.append(e)
    def test_transfer_rejects_insufficient_funds_atomically(self):
        l=Ledger()
        with self.assertRaises(LedgerError): l.transfer('t','a','b',1)
        self.assertEqual(l.events,[])
    def test_transfer_id_collision_is_atomic(self):
        l=Ledger([{'id':'t:credit','account':'other','amount':5}, {'id':'fund','account':'a','amount':20}])
        before=(list(l.events),dict(l.balances))
        with self.assertRaises(LedgerError): l.transfer('t','a','b',3)
        self.assertEqual((l.events,l.balances),before)
    def test_bool_is_not_integer_amount(self):
        with self.assertRaises(LedgerError): Ledger([{'id':'x','account':'a','amount':True}])
    def test_snapshot_checksum_and_replay(self):
        import tempfile
        l=Ledger([{'id':'a','account':'cash','amount':25}])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger.json'; l.save(path); self.assertEqual(Ledger.load(path).balances,l.balances)
            path.write_text(path.read_text().replace('25','26'))
            with self.assertRaises(LedgerError): Ledger.load(path)
if __name__=='__main__': unittest.main()
