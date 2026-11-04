import datetime
import unittest
from unittest import mock

from mma_tracker import store as store_mod
from mma_tracker.store import Store, ValidationError

TODAY = datetime.date(2026, 3, 10)


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(store_mod, "today", return_value=TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.s = Store(":memory:")
        self.addCleanup(self.s.close)
        self.monthly = self.s.list_plans()[0]["id"]
        self.s.update_plan(self.monthly, "Monthly", 30, 500)
        self.ali = self.s.add_member("Ali", "0100")


class MemberTests(StoreTestCase):
    def test_name_required(self):
        with self.assertRaises(ValidationError):
            self.s.add_member("   ")

    def test_search_and_archive(self):
        self.s.add_member("Omar", "0111")
        self.assertEqual([r["name"] for r in self.s.list_members("om")], ["Omar"])
        self.assertEqual(len(self.s.list_members("0100")), 1)
        self.s.set_member_archived(self.ali, True)
        self.assertEqual([r["name"] for r in self.s.list_members()], ["Omar"])
        self.assertEqual(len(self.s.list_members(include_archived=True)), 2)


    def test_delete_member_removes_everything(self):
        omar = self.s.add_member("Omar")
        gloves = self.s.add_product("Gloves", 800, stock=5)
        self.s.subscribe(self.ali, self.monthly, paid_now=100)
        self.s.sell(gloves, 1, member_id=self.ali, paid_now=0)
        self.s.subscribe(omar, self.monthly, paid_now=500)
        self.s.delete_member(self.ali)
        self.assertIsNone(self.s.get_member(self.ali))
        self.assertEqual(self.s.member_history(self.ali), [])
        self.assertEqual(self.s.list_sales(), [])
        self.assertEqual(self.s.get_product(gloves)["stock"], 4)
        self.assertEqual(self.s.total_debt(), 0)
        self.assertEqual(self.s.income(TODAY, TODAY), 500)  # Omar's money stays


class SubscriptionTests(StoreTestCase):
    def test_new_subscription_starts_today(self):
        self.s.subscribe(self.ali, self.monthly)
        sub = self.s.list_subscriptions(self.ali)[0]
        self.assertEqual(sub["start_date"], "2026-03-10")
        self.assertEqual(sub["end_date"], "2026-04-08")
        self.assertEqual(self.s.member_balance(self.ali), 500)

    def test_renewal_continues_from_end_date(self):
        self.s.subscribe(self.ali, self.monthly, paid_now=500)
        self.s.subscribe(self.ali, self.monthly, paid_now=200)
        subs = self.s.list_subscriptions(self.ali)
        self.assertEqual(subs[0]["start_date"], "2026-04-09")
        self.assertEqual(self.s.member_balance(self.ali), 300)

    def test_expired_member_restarts_today(self):
        self.s.subscribe(self.ali, self.monthly, start_date="2026-01-01")
        self.assertEqual(self.s.next_start_date(self.ali), TODAY)

    def test_custom_plan_and_overrides(self):
        plan = self.s.add_plan("10 days", 10, 200)
        self.s.subscribe(self.ali, plan, price=150, days=14, paid_now=150)
        sub = self.s.list_subscriptions(self.ali)[0]
        self.assertEqual(sub["end_date"], "2026-03-23")
        self.assertEqual(self.s.member_balance(self.ali), 0)

    def test_delete_subscription_removes_charge(self):
        sub = self.s.subscribe(self.ali, self.monthly)
        self.s.delete_subscription(sub)
        self.assertEqual(self.s.member_balance(self.ali), 0)
        self.assertIsNone(self.s.member_end_date(self.ali))

    def test_expiring(self):
        omar = self.s.add_member("Omar")
        self.s.subscribe(self.ali, self.monthly, start_date="2026-02-12")  # ends 03-13
        self.s.subscribe(omar, self.monthly)  # ends 04-08
        self.assertEqual([r["name"] for r in self.s.expiring(7)], ["Ali"])


class SalesTests(StoreTestCase):
    def setUp(self):
        super(SalesTests, self).setUp()
        self.gloves = self.s.add_product("Gloves", 800, stock=5)

    def test_walk_in_sale_counts_as_income(self):
        self.s.sell(self.gloves, 2)
        self.assertEqual(self.s.get_product(self.gloves)["stock"], 3)
        self.assertEqual(self.s.income(TODAY, TODAY), 1600)

    def test_member_sale_on_credit(self):
        self.s.sell(self.gloves, 1, member_id=self.ali, paid_now=300)
        self.assertEqual(self.s.member_balance(self.ali), 500)
        self.assertEqual(self.s.income(TODAY, TODAY), 300)

    def test_not_enough_stock(self):
        with self.assertRaises(ValidationError):
            self.s.sell(self.gloves, 6)
        self.assertEqual(self.s.get_product(self.gloves)["stock"], 5)

    def test_delete_sale_restores_stock_and_debt(self):
        sale = self.s.sell(self.gloves, 2, member_id=self.ali, paid_now=0)
        self.s.delete_sale(sale)
        self.assertEqual(self.s.get_product(self.gloves)["stock"], 5)
        self.assertEqual(self.s.member_balance(self.ali), 0)


class DebtTests(StoreTestCase):
    def test_manual_debt_and_payment(self):
        charge = self.s.add_charge(self.ali, 250, "Old balance")
        self.s.add_payment(self.ali, 100)
        self.assertEqual(self.s.member_balance(self.ali), 150)
        self.assertEqual(self.s.total_debt(), 150)
        self.assertEqual([r["name"] for r in self.s.debtors()], ["Ali"])
        self.s.delete_charge(charge)
        self.assertEqual(self.s.member_balance(self.ali), -100)
        self.assertEqual(self.s.total_debt(), 0)

    def test_payment_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.s.add_payment(self.ali, 0)

    def test_history_has_both_sides(self):
        self.s.subscribe(self.ali, self.monthly, paid_now=200)
        types = sorted(r["type"] for r in self.s.member_history(self.ali))
        self.assertEqual(types, ["charge", "payment"])

    def test_monthly_income(self):
        self.s.add_payment(self.ali, 100, on_date="2026-03-01")
        self.s.add_payment(self.ali, 50, on_date="2026-01-15")
        self.s.add_payment(self.ali, 999, on_date="2025-01-15")  # too old
        self.assertEqual(self.s.monthly_income(12),
                         [("2026-03", 100), ("2026-01", 50)])

    def test_summary(self):
        self.s.add_member("Omar")
        self.s.subscribe(self.ali, self.monthly, paid_now=400)
        summary = self.s.summary()
        self.assertEqual(summary["members"], 2)
        self.assertEqual(summary["active"], 1)
        self.assertEqual(summary["expired"], 1)
        self.assertEqual(summary["total_debt"], 100)
        self.assertEqual(summary["income_month"], 400)


if __name__ == "__main__":
    unittest.main()
