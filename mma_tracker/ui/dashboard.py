import tkinter as tk
from tkinter import ttk

from ..i18n import t
from .app import Tab
from .widgets import Table, button, days_status, fmt_money, label, ordered, side_end, side_start, toolbar


class DashboardTab(Tab):
    title_key = "tab_dashboard"

    # (summary key, title, is money, what clicking the card opens)
    CARDS = (
        ("active", "active_members", False, lambda app: app.show_members("active")),
        ("expired", "expired_members", False, lambda app: app.show_members("expiring")),
        ("total_debt", "total_debt", True, lambda app: app.show_tab("DebtsTab")),
        ("income_today", "income_today", True, None),
        ("income_month", "income_month", True, None),
    )

    def build(self):
        bar = toolbar(self)
        button(bar, "refresh", self.refresh, side=side_end())
        button(bar, "export_excel", lambda: self.app.export_excel(self), side=side_end())

        cards = ttk.Frame(self)
        cards.pack(fill=tk.X, pady=(0, 8))
        self.card_labels = {}
        for col, (key, title, _is_money, on_click) in enumerate(ordered(self.CARDS)):
            box = ttk.LabelFrame(cards, text=t(title), padding=8)
            box.grid(row=0, column=col, sticky="nsew", padx=4)
            cards.columnconfigure(col, weight=1)
            value = ttk.Label(box, text="-", style="Big.TLabel", anchor="center")
            value.pack(fill=tk.X)
            self.card_labels[key] = value
            if on_click:
                hint = ttk.Label(box, text=t("go_to_list"), style="Hint.TLabel", anchor="center")
                hint.pack(fill=tk.X)
                for widget in (box, value, hint):
                    widget.configure(cursor="hand2")
                    widget.bind("<Button-1>", lambda e, f=on_click: f(self.app))

        lists = ttk.Frame(self)
        lists.pack(fill=tk.BOTH, expand=True)

        expiring = ttk.Frame(lists)
        expiring.pack(side=side_start(), fill=tk.BOTH, expand=True, padx=(0, 4))
        label(expiring, t("expiring_soon"), style="Title.TLabel").pack(fill=tk.X, pady=(0, 4))
        self.expiring = Table(expiring, [
            ("name", "name", 180, "text"),
            ("phone", "phone", 110, "text"),
            ("end", "end_date", 90, "text"),
            ("left", "status", 170, "text"),
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
        for key, _title, is_money, _on_click in self.CARDS:
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
