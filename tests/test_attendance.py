import datetime
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from mma_tracker import db, store as store_mod
from mma_tracker.store import Store

TODAY = datetime.date(2026, 3, 10)  # a Tuesday


def day(offset):
    return TODAY + datetime.timedelta(days=offset)


class AttendanceTests(unittest.TestCase):
    def setUp(self):
        for name, value in (("today", TODAY),
                            ("now", datetime.datetime(2026, 3, 10, 18, 30))):
            patcher = mock.patch.object(store_mod, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.s = Store(":memory:")
        self.addCleanup(self.s.close)
        self.monthly = self.s.list_plans()[0]["id"]
        self.ali = self.s.add_member("Ali")
        self.omar = self.s.add_member("Omar")

    def test_one_check_in_per_day(self):
        self.assertTrue(self.s.check_in(self.ali))
        self.assertFalse(self.s.check_in(self.ali))
        rows = self.s.attendance_on()
        self.assertEqual([(r["name"], r["checked_at"]) for r in rows], [("Ali", "18:30")])
        self.assertEqual(self.s.summary()["checked_in_today"], 1)

    def test_backdated_check_in_has_no_time_and_toggles(self):
        self.assertTrue(self.s.toggle_check_in(self.ali, day(-3)))
        self.assertEqual(self.s.attendance_dates(self.ali), [day(-3).isoformat()])
        self.assertFalse(self.s.toggle_check_in(self.ali, day(-3)))
        self.assertEqual(self.s.attendance_dates(self.ali), [])

    def test_stats(self):
        # 2 visits in the last 7 days, 1 the week before, 1 in February.
        for offset in (0, -2, -9, -20):
            self.s.check_in(self.ali, day(offset))
        stats = self.s.attendance_stats(self.ali)
        self.assertEqual(stats["week"], 2)
        self.assertEqual(stats["month"], 3)        # March 10, 8 and 1
        self.assertEqual(stats["last_30"], 4)
        self.assertEqual(stats["avg_week"], 1.0)   # 4 visits in 28 days
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["last_visit"], TODAY.isoformat())
        # 7-day windows ending today: [0..-6], [-7..-13], [-14..-20] all have a visit.
        self.assertEqual(stats["streak_weeks"], 3)
        self.s.remove_check_in(self.ali, day(-9))
        self.assertEqual(self.s.attendance_stats(self.ali)["streak_weeks"], 1)
        self.assertEqual(self.s.attendance_stats(self.omar)["streak_weeks"], 0)

    def test_member_list_has_visits(self):
        self.s.check_in(self.ali, day(-1))
        self.s.check_in(self.ali, day(-40))
        row = [m for m in self.s.list_members() if m["id"] == self.ali][0]
        self.assertEqual(row["visits_30"], 1)
        self.assertEqual(row["last_visit"], day(-1).isoformat())

    def test_daily_and_top(self):
        self.s.check_in(self.ali)
        self.s.check_in(self.omar)
        self.s.check_in(self.ali, day(-1))
        daily = self.s.daily_attendance(3)
        self.assertEqual([c for _d, c in daily], [0, 1, 2])
        self.assertEqual(daily[-1][0], TODAY)
        top = self.s.top_attendees(day(-6), TODAY)
        self.assertEqual([(r["name"], r["visits"]) for r in top], [("Ali", 2), ("Omar", 1)])

    def test_inactive_members_only_counts_running_subscriptions(self):
        sami = self.s.add_member("Sami")
        for member in (self.ali, self.omar, sami):
            self.s.subscribe(member, self.monthly)
        self.s.check_in(self.ali, day(-1))      # trained recently
        self.s.check_in(self.omar, day(-20))    # stopped coming
        self.s.add_member("Never subscribed")   # no subscription: ignored
        self.assertEqual([r["name"] for r in self.s.inactive_members(14)], ["Sami", "Omar"])

    def test_subscription_days(self):
        self.s.subscribe(self.ali, self.monthly, start_date=day(-2), days=3)
        days = self.s.subscription_days(self.ali, day(-5), day(5))
        self.assertEqual(sorted(days), [day(-2).isoformat(), day(-1).isoformat(),
                                        TODAY.isoformat()])

    def test_delete_member_removes_attendance(self):
        self.s.check_in(self.ali)
        self.s.delete_member(self.ali)
        self.assertEqual(self.s.attendance_on(), [])


class MigrationTests(unittest.TestCase):
    def test_version_1_database_gains_attendance(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "old.db")
        conn = sqlite3.connect(path)
        conn.executescript(db.SCHEMA)
        conn.execute("INSERT INTO members(name, created_on) VALUES ('Ali', '2026-01-01')")
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
        conn.close()

        s = Store(path)
        self.addCleanup(s.close)
        self.assertEqual(s.conn.execute("PRAGMA user_version").fetchone()[0],
                         db.SCHEMA_VERSION)
        member = s.list_members()[0]
        self.assertTrue(s.check_in(member["id"]))
        self.assertEqual(s.list_plans(), [])  # v1 data untouched, no re-seeding


if __name__ == "__main__":
    unittest.main()
