import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import date, timedelta
from main import Event, expand, conflicts, free_slots, load_events

MON = date(2026, 11, 2)
def event(name, start, duration, days=frozenset({0}), span=7):
    return Event(name, MON, MON + timedelta(days=span), days, start, duration)

class CalendarTests(unittest.TestCase):
    def test_conflict_and_adjacent_events(self):
        a=event('A',540,60); b=event('B',599,30); c=event('C',600,30)
        self.assertEqual([(x.event,y.event) for x,y in conflicts([a,b,c],MON,MON)], [('A','B'),('B','C')])
    def test_weekly_inclusive_dates(self):
        e=event('X',60,30,span=7)
        self.assertEqual(len(expand([e],MON,MON+timedelta(days=7))),2)
    def test_free_windows_clip_outside_hours(self):
        e=event('X',480,90)
        self.assertEqual(free_slots([e],MON),[(570,1020)])
    def test_invalid_event(self):
        with self.assertRaises(ValueError): event('bad',1400,90)
    def test_horizon_bound(self):
        with self.assertRaises(ValueError): expand([],MON,MON+timedelta(days=3661))

    def test_load_events_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'events.json'
            path.write_text(json.dumps([{'name':'Planning','start_date':'2026-11-02','end_date':'2026-11-02','weekdays':[0],'start':'09:00','duration':60}]))
            self.assertEqual(load_events(path)[0], event('Planning',540,60,span=0))

    def test_cli_help(self):
        result=subprocess.run([sys.executable,'main.py','--help'],capture_output=True,text=True,check=True)
        self.assertIn('--input',result.stdout)

if __name__ == '__main__': unittest.main()
