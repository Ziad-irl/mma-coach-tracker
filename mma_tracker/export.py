"""Export all data to one Excel workbook, one sheet per kind of record.
Headers and status words follow the current UI language."""

from . import i18n
from .i18n import t
from .store import member_status
from .xlsx import write_xlsx


def status_text(end_date):
    code, days = member_status(end_date)
    if code == "none":
        return t("status_none")
    if code == "expired":
        return t("status_expired_ago") % days
    if code == "today":
        return t("status_ends_today")
    return t("status_active_days") % days


def _members_sheet(store):
    rows = [(m["name"], m["phone"], m["notes"], m["end_date"] or "",
             status_text(m["end_date"]), m["balance"],
             t("yes") if m["archived"] else t("no"))
            for m in store.list_members(include_archived=True)]
    return (t("tab_members"), [
        (t("name"), "text", 24), (t("phone"), "text", 15), (t("notes"), "text", 24),
        (t("end_date"), "text", 12), (t("status"), "text", 22),
        (t("balance"), "money", 12), (t("archived"), "text", 10),
    ], rows)


def build_sheets(store):
    kinds = {"sub": t("type_sub"), "sale": t("type_sale"), "other": t("type_other")}
    return [
        _members_sheet(store),
        (t("tab_debts"), [
            (t("name"), "text", 24), (t("phone"), "text", 15), (t("balance"), "money", 12),
        ], [(r["name"], r["phone"], r["balance"]) for r in store.debtors()]),
        (t("subscriptions"), [
            (t("member"), "text", 24), (t("plan"), "text", 18), (t("start"), "text", 12),
            (t("end_date"), "text", 12), (t("price"), "money", 12),
        ], [(s["member_name"], s["plan_name"], s["start_date"], s["end_date"], s["price"])
            for s in store.all_subscriptions()]),
        (t("payments"), [
            (t("date"), "text", 12), (t("member"), "text", 24),
            (t("amount"), "money", 12), (t("payment_note"), "text", 30),
        ], [(p["on_date"], p["member_name"], p["amount"], p["note"])
            for p in store.all_payments()]),
        (t("charges"), [
            (t("date"), "text", 12), (t("member"), "text", 24), (t("type"), "text", 14),
            (t("description"), "text", 36), (t("amount"), "money", 12),
        ], [(c["on_date"], c["member_name"], kinds.get(c["kind"], c["kind"]),
             c["description"], c["amount"]) for c in store.all_charges()]),
        (t("sales"), [
            (t("date"), "text", 12), (t("product"), "text", 22), (t("qty"), "int", 9),
            (t("unit_price"), "money", 12), (t("total"), "money", 12),
            (t("member"), "text", 24),
        ], [(s["on_date"], s["product_name"], s["qty"], s["unit_price"], s["total"],
             s["member_name"] or t("walk_in"))
            for s in store.list_sales(limit=1000000)]),
        (t("products"), [
            (t("name"), "text", 24), (t("price"), "money", 12), (t("stock"), "int", 9),
        ], [(p["name"], p["price"], p["stock"]) for p in store.list_products()]),
        (t("monthly_income"), [
            (t("month"), "text", 12), (t("amount"), "money", 14),
        ], store.monthly_income(120)),
    ]


def export_all(store, path):
    return write_xlsx(path, build_sheets(store), rtl=i18n.is_rtl())
