"""store.events: tolerant reading, UTC with time zone, offsets for incremental reading."""
import unittest
from datetime import datetime, timezone

from tests.unit.base import TempTest
from keel.store import events

LINES = (b'{"event":"a","ts":"2026-10-01T10:00:00Z"}\n'
         b'kaputt\n'
         b'{"event":"b"}\n'
         b'{"event":"c","ts":"2026-10-01T12:00:00+02:00"}\n'
         b'[1, 2]\n'
         b'{"event":"d","ts":17}\n'
         b'{"event":"e","ts":"2026-10-01T11:00:00","x":"\xff"}\n'
         b'{"event":"f","ts":"2026-10-01T11:00:00"}\n')


class EventsTest(TempTest):
    def file(self, data=LINES):
        f = self.tmp / "events.jsonl"
        f.write_bytes(data)
        return f

    def test_parse_ts(self):
        utc = timezone.utc
        self.assertEqual(events.parse_ts("2026-10-01T10:00:00Z"), datetime(2026, 10, 1, 10, tzinfo=utc))
        self.assertEqual(events.parse_ts("2026-10-01T12:00:00+02:00"), datetime(2026, 10, 1, 10, tzinfo=utc))
        self.assertEqual(events.parse_ts("2026-10-01"), datetime(2026, 10, 1, tzinfo=utc))
        for bad in (None, 17, "", "gestern", "2026-13-01"):
            self.assertIsNone(events.parse_ts(bad))

    def test_tolerant_read(self):
        r = events.read(self.file())
        self.assertEqual([e["event"] for e in r.events], ["a", "c", "f"])
        self.assertEqual(r.skipped, 5)
        self.assertTrue(all(e["_ts"].tzinfo is not None for e in r.events))

    def test_since(self):
        since = events.parse_ts("2026-10-01T10:30:00Z")
        self.assertEqual([e["event"] for e in events.read(self.file(), since=since).events], ["f"])

    def test_incremental_reading(self):
        f = self.file(b'{"event":"a","ts":"2026-10-01T10:00:00Z"}\n{"event":"b","ts":"2026-10-01T10:')
        first = events.read(f)
        self.assertEqual([e["event"] for e in first.events], ["a"])
        with f.open("ab") as h:
            h.write(b'01:00Z"}\n')
        second = events.read(f, start=first.end)
        self.assertEqual([e["event"] for e in second.events], ["b"])
        self.assertEqual(second.end, f.stat().st_size)

    def test_tail(self):
        f = self.file(b"".join(b'{"event":"%d","ts":"2026-10-01T10:00:00Z"}\n' % i for i in range(100)))
        tail = events.read(f, tail_bytes=200).events
        self.assertTrue(0 < len(tail) < 6)
        self.assertEqual(tail[-1]["event"], "99")

    def test_missing_file(self):
        self.assertEqual(events.read(self.tmp / "fehlt.jsonl"), events.ReadResult([], 0, 0))

    def test_append_sets_ts(self):
        f = self.tmp / "neu" / "events.jsonl"
        events.append(f, {"event": "x"})
        [e] = events.read(f).events
        self.assertEqual(e["event"], "x")


if __name__ == "__main__":
    unittest.main()
