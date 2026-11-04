"""Dialogs shared by several tabs. Each returns a truthy value if data changed."""

import datetime

from ..i18n import t
from ..store import ValidationError, money
from .widgets import FormDialog


def member_form(parent, store, member=None):
    def submit(v):
        if member is None:
            return store.add_member(v["name"], v["phone"], v["notes"])
        store.update_member(member["id"], v["name"], v["phone"], v["notes"])
        return member["id"]

    d = FormDialog(parent, t("edit_member" if member else "add_member"), submit)
    d.add_field("name", "name", member["name"] if member else "")
    d.add_field("phone", "phone", member["phone"] if member else "")
    d.add_field("notes", "notes", member["notes"] if member else "")
    return d.show()


def subscribe_form(parent, store, member_id):
    plans = store.list_plans()
    if not plans:
        raise ValidationError("err_pick_plan")
    by_id = dict((p["id"], p) for p in plans)

    def submit(v):
        return store.subscribe(member_id, v["plan"], start_date=v["start"],
                               price=v["price"], paid_now=v["paid"], days=v["days"])

    d = FormDialog(parent, t("new_subscription"), submit)
    first = plans[0]
    d.add_field("plan", "plan", first["id"], "choice",
                [(p["id"], "%s (%d %s)" % (p["name"], p["days"], t("days")))
                 for p in plans])
    d.add_field("start", "start_date", store.next_start_date(member_id).isoformat(), "date")
    d.add_field("days", "days", str(first["days"]), "int")
    d.add_field("price", "price", float(first["price"]), "money")
    d.add_field("paid", "paid_now", float(first["price"]), "money")

    def on_plan(_event):
        plan = by_id[d.choice_value("plan")]
        d.set_raw("days", str(plan["days"]))
        d.set_raw("price", float(plan["price"]))
        d.set_raw("paid", float(plan["price"]))

    d.widgets["plan"].bind("<<ComboboxSelected>>", on_plan)
    return d.show()


def payment_form(parent, store, member_id):
    balance = store.member_balance(member_id)

    def submit(v):
        return store.add_payment(member_id, v["amount"], v["date"], v["note"])

    d = FormDialog(parent, t("record_payment"), submit)
    d.add_field("amount", "amount", float(max(balance, 0)) or "", "money")
    d.add_field("date", "date", datetime.date.today().isoformat(), "date")
    d.add_field("note", "payment_note", "")
    return d.show()


def debt_form(parent, store, member_id):
    def submit(v):
        return store.add_charge(member_id, v["amount"], v["description"], v["date"])

    d = FormDialog(parent, t("add_debt"), submit)
    d.add_field("amount", "amount", "", "money")
    d.add_field("description", "description", "")
    d.add_field("date", "date", datetime.date.today().isoformat(), "date")
    return d.show()


def sell_form(parent, store, member_id=None, product_id=None):
    products = [p for p in store.list_products() if p["stock"] > 0]
    if not products:
        raise ValidationError("err_not_enough_stock")
    by_id = dict((p["id"], p) for p in products)
    members = [(None, t("walk_in"))] + [
        (m["id"], m["name"]) for m in store.list_members()]

    def submit(v):
        return store.sell(v["product"], v["qty"], member_id=v["member"],
                          unit_price=v["price"], paid_now=v["paid"])

    d = FormDialog(parent, t("sell_title"), submit)
    start = by_id.get(product_id, products[0])
    d.add_field("product", "product", start["id"], "choice",
                [(p["id"], "%s  [%d]" % (p["name"], p["stock"])) for p in products])
    d.add_field("qty", "qty", "1", "int")
    d.add_field("price", "unit_price", float(start["price"]), "money")
    d.add_field("member", "member", member_id, "choice", members)
    d.add_field("paid", "paid_now", float(start["price"]), "money")

    def update_paid(*_):
        try:
            total = money(d.get_raw("price") or 0) * int(d.get_raw("qty") or 0)
        except ValueError:
            return
        d.set_raw("paid", float(total))

    def on_product(_event):
        d.set_raw("price", float(by_id[d.choice_value("product")]["price"]))

    d.widgets["product"].bind("<<ComboboxSelected>>", on_product)
    d.vars["qty"].trace_add("write", update_paid)
    d.vars["price"].trace_add("write", update_paid)
    return d.show()


def product_form(parent, store, product=None):
    def submit(v):
        if product is None:
            return store.add_product(v["name"], v["price"], v["stock"])
        store.update_product(product["id"], v["name"], v["price"], v["stock"])
        return product["id"]

    d = FormDialog(parent, t("edit_product" if product else "add_product"), submit)
    d.add_field("name", "name", product["name"] if product else "")
    d.add_field("price", "price", float(product["price"]) if product else "", "money")
    d.add_field("stock", "stock", str(product["stock"]) if product else "0", "int")
    return d.show()


def plan_form(parent, store, plan=None):
    def submit(v):
        if plan is None:
            return store.add_plan(v["name"], v["days"], v["price"])
        store.update_plan(plan["id"], v["name"], v["days"], v["price"])
        return plan["id"]

    d = FormDialog(parent, t("edit_plan" if plan else "add_plan"), submit)
    d.add_field("name", "name", plan["name"] if plan else "")
    d.add_field("days", "days", str(plan["days"]) if plan else "30", "int")
    d.add_field("price", "price", float(plan["price"]) if plan else "", "money")
    return d.show()
