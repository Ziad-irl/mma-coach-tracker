import datetime
import tkinter as tk
from tkinter import ttk

from ..i18n import t
from .app import Tab
from .visuals import BarChart, GREEN
from .widgets import (Table, button, days_status, fmt_last_visit, fmt_money, label,
                      ordered, side_end, side_start, toolbar)


def last_months(count):
    """['YYYY-MM', ...] for the last N months, oldest first."""
    today = datetime.date.today()
    index = today.year * 12 + today.month - 1
    return ["%04d-%02d" % (i // 12, i % 12 + 1) for i in range(index - count + 1, index + 1)]


class DashboardTab(Tab):
    title_key = "tab_dashboard"

    # (summary key, title, is money, what clicking the card opens)
    CARDS = (
        ("checked_in_today", "checked_in_today", False, lambda app: app.show_check_in()),
        ("active", "active_members", False, lambda app: app.show_members("active")),
        ("expired", "expired_members", False, lambda app: app.show_members("expiring")),
        ("total_debt", "total_debt", True, lambda app: app.show_tab("DebtsTab")),
        ("income_today", "income_today", True, None),
        ("income_month", "income_month", True, None),
    )

    def build(self):
        bar = toolbar(self)
        brand = self.app.brand
        if brand.logo:
            try:
                self.logo = tk.PhotoImage(file=brand.logo)  # keep a reference
                ttk.Label(bar, image=self.logo).pack(side=side_start(), padx=(0, 8))
            except tk.TclError:
                pass
        if brand.name:
            label(bar, brand.name, style="Big.TLabel").pack(side=side_start())
        button(bar, "refresh", self.refresh, side=side_end())
        button(bar, "export_excel", lambda: self.app.export_excel(self), side=side_end())

        cards = ttk.Frame(self)
        cards.pack(fill=tk.X, pady=(0, 8))
        self.card_labels = {}
        for col, (key, title, _is_money, on_click) in enumerate(ordered(self.CARDS)):
            box = ttk.LabelFrame(cards, text=t(title), padding=6)
            box.grid(row=0, column=col, sticky="nsew", padx=3)
            cards.columnconfigure(col, weight=1)
            value = ttk.Label(box, text="-", style="Card.TLabel", anchor="center")
            value.pack(fill=tk.X)
            self.card_labels[key] = value
            if on_click:
                hint = ttk.Label(box, text=t("go_to_list"), style="Hint.TLabel", anchor="center")
                hint.pack(fill=tk.X)
                for widget in (box, value, hint):
                    widget.configure(cursor="hand2")
                    widget.bind("<Button-1>", lambda e, f=on_click: f(self.app))

        charts = ttk.Frame(self)
        charts.pack(fill=tk.X, pady=(0, 8))
        att = ttk.LabelFrame(charts, text=t("attendance_chart"), padding=4)
        att.pack(side=side_start(), fill=tk.BOTH, expand=True, padx=(0, 4))
        self.attendance_chart = BarChart(att, height=130, colour="#1f6fb2", label_every=5)
        self.attendance_chart.pack(fill=tk.BOTH, expand=True)
        inc = ttk.LabelFrame(charts, text=t("income_chart"), padding=4)
        inc.pack(side=side_start(), fill=tk.BOTH, expand=True, padx=(4, 0))
        self.income_chart = BarChart(inc, height=130, colour=GREEN, fmt=fmt_money)
        self.income_chart.pack(fill=tk.BOTH, expand=True)

        lists = ttk.Frame(self)
        lists.pack(fill=tk.BOTH, expand=True)

        expiring = ttk.Frame(lists)
        expiring.pack(side=side_start(), fill=tk.BOTH, expand=True, padx=(0, 4))
        label(expiring, t("expiring_soon"), style="Title.TLabel").pack(fill=tk.X, pady=(0, 4))
        self.expiring = Table(expiring, [
            ("name", "name", 170, "text"),
            ("phone", "phone", 110, "text"),
            ("left", "status", 170, "text"),
        ], height=6, on_open=lambda iid: self.app.open_member(int(iid)))
        self.expiring.pack(fill=tk.BOTH, expand=True)

        inactive = ttk.Frame(lists)
        inactive.pack(side=side_start(), fill=tk.BOTH, expand=True, padx=(4, 0))
        label(inactive, t("inactive_title"), style="Title.TLabel").pack(fill=tk.X, pady=(0, 4))
        self.inactive = Table(inactive, [
            ("name", "name", 170, "text"),
            ("phone", "phone", 110, "text"),
            ("last", "last_visit", 120, "text"),
        ], height=6, on_open=lambda iid: self.app.open_member(int(iid)))
        self.inactive.pack(fill=tk.BOTH, expand=True)

    def refresh(self):
        summary = self.store.summary()
        cur = self.app.currency
        for key, _title, is_money, _on_click in self.CARDS:
            value = summary[key]
            self.card_labels[key].configure(
                text=fmt_money(value, cur) if is_money else str(value))
        self.card_labels["total_debt"].configure(
            style="Card.TLabel" if not summary["total_debt"] else "CardDebt.TLabel")

        self.attendance_chart.set_data(
            [(d.strftime("%d/%m"), count) for d, count in self.store.daily_attendance(30)])
        income = dict(self.store.monthly_income(12))
        self.income_chart.set_data(
            [(ym[5:] + "/" + ym[2:4], income.get(ym, 0)) for ym in last_months(12)])

        rows = []
        for r in self.store.expiring(7):
            text, tag = days_status(r["end_date"])
            rows.append((r["id"], {"name": r["name"], "phone": r["phone"], "left": text}, tag))
        self.expiring.set_rows(rows)
        self.inactive.set_rows(
            (r["id"], {"name": r["name"], "phone": r["phone"],
                       "last": fmt_last_visit(r["last_visit"])}, "warn")
            for r in self.store.inactive_members(14))
