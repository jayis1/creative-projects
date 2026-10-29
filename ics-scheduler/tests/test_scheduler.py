import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import Event, Recurrence, expand, to_ics, from_ics, find_conflicts
UTC = timezone.utc
class SchedulerTests(unittest.TestCase):
    def setUp(self): self.start = datetime(2026, 1, 31, 9, tzinfo=UTC)
    def test_recurrence_round_trip_and_month_end(self):
        source = Event(self.start, timedelta(minutes=20), "Design, review; v2", Recurrence("MONTHLY", count=3))
        decoded = from_ics(to_ics([source]))[0]
        self.assertEqual(expand(source), expand(decoded))
        self.assertEqual([e.start.day for e in expand(decoded)], [31, 28, 31])
        self.assertEqual(decoded.summary, source.summary)
    def test_until_inclusive(self):
        stop = self.start + timedelta(days=2)
        self.assertEqual(len(expand(Event(self.start, timedelta(hours=1), "daily", Recurrence("DAILY", until=stop)))), 3)
    def test_conflicts_half_open(self):
        a = Event(self.start, timedelta(hours=1), "a")
        touching = Event(self.start + timedelta(hours=1), timedelta(hours=1), "touch")
        overlap = Event(self.start + timedelta(minutes=59), timedelta(hours=1), "overlap")
        self.assertEqual(find_conflicts([a, touching, overlap]), [(a, overlap), (overlap, touching)])
    def test_invalids_and_limit(self):
        with self.assertRaises(ValueError): Recurrence("HOURLY", count=2)
        with self.assertRaises(ValueError): Event(self.start, timedelta(0), "bad")
        with self.assertRaises(ValueError): expand(Event(self.start, timedelta(hours=1), "x", Recurrence("DAILY", count=9)), 2)
    def test_rejects_duplicate_and_missing_fields(self):
        with self.assertRaises(ValueError): from_ics("BEGIN:VEVENT\nDTSTART:20260101T000000Z\nDTSTART:20260101T000000Z\nEND:VEVENT")
        with self.assertRaises(ValueError): from_ics("BEGIN:VEVENT\nDTSTART:20260101T000000Z\nEND:VEVENT")
    def test_rejects_unknown_summary_escape(self):
        text = "BEGIN:VEVENT\nDTSTART:20260101T000000Z\nDURATION:PT60S\nSUMMARY:bad\\qescape\nEND:VEVENT"
        with self.assertRaisesRegex(ValueError, "unsupported escape"):
            from_ics(text)
    def test_calendar_check_reports_expanded_overlaps(self):
        from main import check_calendar
        from tempfile import TemporaryDirectory
        from contextlib import redirect_stdout
        from io import StringIO
        first = Event(self.start, timedelta(hours=1), "first", Recurrence("DAILY", count=2))
        second = Event(self.start + timedelta(minutes=30), timedelta(minutes=10), "second")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "calendar.ics"
            path.write_text(to_ics([first, second]), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output): status = check_calendar(path)
        self.assertEqual(status, 1)
        self.assertIn("1 conflict(s)", output.getvalue())
        self.assertIn("second", output.getvalue())
if __name__ == "__main__": unittest.main()
