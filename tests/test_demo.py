import datetime
import unittest

from mma_tracker import demo
from mma_tracker.store import Store, member_status


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.s = Store(":memory:")
        self.addCleanup(self.s.close)
        demo.seed(self.s)

    def statuses(self):
        return [member_status(m["end_date"])[0] for m in self.s.list_members()]

    def test_covers_every_situation(self):
        members = self.s.list_members()
        self.assertEqual(len(members), len(demo.NAMES))
        codes = self.statuses()
        for code in ("active", "expired", "none"):
            self.assertIn(code, codes)
        self.assertTrue(self.s.expiring(7))
        self.assertTrue(self.s.inactive_members(14))
        self.assertTrue(self.s.debtors())
        self.assertGreater(sum(m["visits_30"] for m in members), 50)
        self.assertEqual(len(self.s.list_plans()), len(demo.PLANS))
        stock = dict((p["name"], p["stock"]) for p in self.s.list_products())
        self.assertEqual(stock["MMA shorts"], 0)
        self.assertEqual(len(self.s.list_sales()), 28)

    def test_dates_are_never_in_the_future(self):
        today = datetime.date.today().isoformat()
        for table in ("payments", "charges", "sales", "attendance"):
            latest = self.s.conn.execute("SELECT MAX(on_date) FROM %s" % table).fetchone()[0]
            self.assertLessEqual(latest, today, table)
        latest_start = self.s.conn.execute("SELECT MAX(start_date) FROM subscriptions").fetchone()[0]
        self.assertLessEqual(latest_start, today)

    def test_income_spans_many_months(self):
        self.assertGreaterEqual(len(self.s.monthly_income(12)), 8)

    def test_reset_gives_the_same_data(self):
        before = [(m["name"], m["end_date"], m["balance"]) for m in self.s.list_members()]
        demo.reset(self.s)
        after = [(m["name"], m["end_date"], m["balance"]) for m in self.s.list_members()]
        self.assertEqual(before, after)
        self.assertFalse(demo.is_empty(self.s))


if __name__ == "__main__":
    unittest.main()
