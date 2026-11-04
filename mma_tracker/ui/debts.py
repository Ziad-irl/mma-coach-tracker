import tkinter as tk

from ..i18n import t
from . import dialogs
from .app import Tab
from .widgets import Table, button, fmt_money, label, side_end, side_start, toolbar


class DebtsTab(Tab):
    title_key = "tab_debts"

    def build(self):
        bar = toolbar(self)
        self.total = label(bar, "", style="Title.TLabel")
        self.total.pack(side=side_start(), padx=2)
        button(bar, "open", self.open_selected, side=side_end())
        button(bar, "record_payment", self.pay, side=side_end())
        self.table = Table(self, [
            ("name", "name", 260, "text"),
            ("phone", "phone", 140, "text"),
            ("balance", "balance", 120, "num"),
        ], height=18, on_open=lambda iid: self.app.open_member(int(iid)))
        self.table.pack(fill=tk.BOTH, expand=True)

    def refresh(self):
        rows = self.store.debtors()
        self.table.set_rows(
            (r["id"], {"name": r["name"], "phone": r["phone"],
                       "balance": fmt_money(r["balance"])}, "expired")
            for r in rows)
        total = sum(r["balance"] for r in rows)
        self.total.configure(text="%s: %s   (%d)" % (
            t("total_debt"), fmt_money(total, self.app.currency), len(rows)))

    def pay(self):
        iid = self.table.require_selected()
        if iid is not None:
            self.app.run(self, dialogs.payment_form, self, self.store, int(iid))

    def open_selected(self):
        iid = self.table.require_selected()
        if iid is not None:
            self.app.open_member(int(iid))
