import tkinter as tk
from tkinter import ttk

from ..i18n import t
from .app import Tab
from .widgets import Table, button, days_status, fmt_money, label, ordered, side_end, side_start, toolbar


class DashboardTab(Tab):
    title_key = "tab_dashboard"

    CARDS = (
        ("active", "active_members", False),
        ("expired", "expired_members", False),
        ("total_debt", "total_debt", True),
        ("income_today", "income_today", True),
        ("income_month", "income_month", True),
    )

    def build(self):
        bar = toolbar(self)
        button(bar, "refresh", self.refresh, side=side_end())

        cards = ttk.Frame(self)
        cards.pack(fill=tk.X, pady=(0, 8))
        self.card_labels = {}
        for col, (key, title, _is_money) in enumerate(ordered(self.CARDS)):
            box = ttk.LabelFrame(cards, text=t(title), padding=8)
            box.grid(row=0, column=col, sticky="nsew", padx=4)
            cards.columnconfigure(col, weight=1)
            value = ttk.Label(box, text="-", style="Big.TLabel", anchor="center")
            value.pack(fill=tk.X)
            self.card_labels[key] = value

        lists = ttk.Frame(self)
        lists.pack(fill=tk.BOTH, expand=True)

        expiring = ttk.Frame(lists)
        expiring.pack(side=side_start(), fill=tk.BOTH, expand=True, padx=(0, 4))
        label(expiring, t("expiring_soon"), style="Title.TLabel").pack(fill=tk.X, pady=(0, 4))
        self.expiring = Table(expiring, [
            ("name", "name", 180, "text"),
            ("phone", "phone", 110, "text"),
            ("end", "end_date", 90, "text"),
            ("left", "days_left", 100, "text"),
        ], on_open=lambda iid: self.app.open_member(int(iid)))
        self.expiring.pack(fill=tk.BOTH, expand=True)

        income = ttk.Frame(lists)
        income.pack(side=side_start(), fill=tk.Y, padx=(4, 0))
        label(income, t("monthly_income"), style="Title.TLabel").pack(fill=tk.X, pady=(0, 4))
        self.income = Table(income, [
            ("month", "month", 90, "text"),
            ("amount", "amount", 110, "num"),
        ])
        self.income.pack(fill=tk.BOTH, expand=True)

    def refresh(self):
        summary = self.store.summary()
        cur = self.app.currency
        for key, _title, is_money in self.CARDS:
            value = summary[key]
            self.card_labels[key].configure(
                text=fmt_money(value, cur) if is_money else str(value))
        self.card_labels["total_debt"].configure(
            style="Big.TLabel" if not summary["total_debt"] else "BigDebt.TLabel")

        rows = []
        for r in self.store.expiring(7):
            text, tag = days_status(r["end_date"])
            rows.append((r["id"], {"name": r["name"], "phone": r["phone"],
                                   "end": r["end_date"], "left": text}, tag))
        self.expiring.set_rows(rows)
        self.income.set_rows(
            (ym, {"month": ym, "amount": fmt_money(amount)}, "")
            for ym, amount in self.store.monthly_income(12))
