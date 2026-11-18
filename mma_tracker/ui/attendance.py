"""Front-desk check-in: type a name, press Enter, see a coloured banner."""

import datetime
import tkinter as tk
from tkinter import ttk

from ..export import status_text
from ..i18n import bidi, t
from ..store import member_status
from .app import Tab
from .visuals import Banner, ui_font
from .widgets import (Table, button, days_status, fmt_last_visit, fmt_money, justify,
                      label, side_end, side_start, toolbar)

MAX_RESULTS = 60


class AttendanceTab(Tab):
    title_key = "tab_attendance"

    def build(self):
        self.banner = Banner(self, idle_text=t("ready"))
        self.banner.pack(fill=tk.X, pady=(0, 8))

        right = ttk.Frame(self)
        right.pack(side=side_end(), fill=tk.Y, padx=(8, 0))
        left = ttk.Frame(self)
        left.pack(side=side_start(), fill=tk.BOTH, expand=True)

        # check-in search
        self.search = tk.StringVar(self)
        self.entry = tk.Entry(left, textvariable=self.search, font=ui_font(16),
                              justify=justify(), relief=tk.SOLID, bd=1)
        self.entry.pack(fill=tk.X, ipady=4)
        label(left, t("checkin_prompt"), style="Hint.TLabel").pack(fill=tk.X, pady=(2, 6))
        bar = toolbar(left)
        button(bar, "check_in", self.check_in_selected)
        button(bar, "open", self.open_selected)
        self.results = Table(left, [
            ("name", "name", 200, "text"),
            ("status", "status", 170, "text"),
            ("last", "last_visit", 110, "text"),
        ], height=12, on_open=lambda iid: self.check_in(int(iid)))
        self.results.pack(fill=tk.BOTH, expand=True)

        # today
        self.today_count = ttk.Label(right, text="", style="Big.TLabel")
        self.today_count.pack(fill=tk.X)
        self.today = Table(right, [
            ("time", "time", 60, "text"),
            ("name", "name", 200, "text"),
        ], height=9, on_open=lambda iid: self.app.open_member(int(iid)))
        self.today.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        tbar = toolbar(right, pady=(4, 8))
        button(tbar, "undo_check_in", self.undo, side=side_end())
        label(right, t("top_this_month"), style="Title.TLabel").pack(fill=tk.X)
        self.top = Table(right, [
            ("name", "name", 200, "text"),
            ("visits", "visits", 70, "num"),
        ], height=6, on_open=lambda iid: self.app.open_member(int(iid)))
        self.top.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self._job = None
        self.search.trace_add("write", self._on_type)
        self.entry.bind("<Return>", lambda e: self.check_in_selected())
        self.entry.bind("<Down>", lambda e: self._move(1))
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Escape>", lambda e: self.search.set(""))

    def focus(self):
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

    def _on_type(self, *_):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(150, self.refresh_results)

    def _move(self, step):
        rows = self.results.tree.get_children()
        if not rows:
            return "break"
        current = self.results.selected()
        index = rows.index(current) + step if current in rows else 0
        index = max(0, min(index, len(rows) - 1))
        self.results.tree.selection_set(rows[index])
        self.results.tree.see(rows[index])
        return "break"

    def refresh(self):
        self.refresh_results()
        self.refresh_today()
        self.focus()

    def refresh_results(self):
        self._job = None
        rows = []
        for m in self.store.list_members(self.search.get())[:MAX_RESULTS]:
            text, tag = days_status(m["end_date"])
            rows.append((m["id"], {"name": m["name"], "status": text,
                                   "last": fmt_last_visit(m["last_visit"])}, tag))
        self.results.set_rows(rows)
        children = self.results.tree.get_children()
        if children and self.results.selected() is None:
            self.results.tree.selection_set(children[0])

    def refresh_today(self):
        rows = self.store.attendance_on()
        self.today_count.configure(text=bidi("%s: %d" % (t("checked_in_today"), len(rows))))
        self.today.set_rows((r["member_id"], {"time": r["checked_at"], "name": r["name"]}, "")
                            for r in rows)
        first = datetime.date.today().replace(day=1)
        self.top.set_rows((r["id"], {"name": r["name"], "visits": r["visits"]}, "")
                          for r in self.store.top_attendees(first, datetime.date.today()))

    # actions -----------------------------------------------------------------

    def check_in_selected(self):
        iid = self.results.selected()
        if iid is not None:
            self.check_in(int(iid))

    def open_selected(self):
        iid = self.results.require_selected()
        if iid is not None:
            self.app.open_member(int(iid))

    def check_in(self, member_id):
        member = self.store.get_member(member_id)
        added = self.store.check_in(member_id)
        stats = self.store.attendance_stats(member_id)
        end = self.store.member_end_date(member_id)
        balance = self.store.member_balance(member_id)

        lines = [t("checked_in_ok" if added else "already_checked_in") % member["name"],
                 t("checkin_counts") % (stats["month"], stats["week"])]
        code, days = member_status(end)
        warnings = []
        if code != "active" or days <= 7:
            warnings.append(t("warn_subscription") % status_text(end))
        if balance > 0:
            warnings.append(t("warn_owes") % fmt_money(balance, self.app.currency))
        if warnings:
            lines.append(bidi("   |   ".join(warnings)))

        if code in ("none", "expired"):
            kind = "danger"
        elif warnings:
            kind = "warn"
        else:
            kind = "success" if added else "info"
        self.banner.show("\n".join(lines), kind)
        self.search.set("")
        self.app.data_changed()

    def undo(self):
        iid = self.today.require_selected()
        if iid is not None:
            self.store.remove_check_in(int(iid), datetime.date.today())
            self.app.data_changed()
