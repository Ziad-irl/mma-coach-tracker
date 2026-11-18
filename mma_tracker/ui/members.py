import datetime
import tkinter as tk
from tkinter import ttk

from ..i18n import bidi, t
from ..store import member_status
from . import dialogs
from .app import Tab
from .visuals import Avatar, MonthCalendar
from .widgets import (Table, button, center, confirm, days_status, fmt_last_visit,
                      fmt_money, label, ordered, show_error, side_end, side_start,
                      toolbar)

FILTERS = ("all", "active", "expiring", "owing", "inactive")
INACTIVE_DAYS = 14
STAT_TILES = (
    ("week", "stat_week"),
    ("month", "stat_month"),
    ("last_30", "stat_30"),
    ("avg_week", "stat_avg"),
    ("streak_weeks", "stat_streak"),
    ("last_visit", "last_visit"),
)


def matches(status_filter, member):
    if status_filter == "owing":
        return member["balance"] > 0
    code, days = member_status(member["end_date"])
    if status_filter == "inactive":
        cutoff = (datetime.date.today() - datetime.timedelta(days=INACTIVE_DAYS)).isoformat()
        return code in ("active", "today") and (
            not member["last_visit"] or member["last_visit"] <= cutoff)
    if status_filter == "active":
        return code in ("active", "today")
    if status_filter == "expiring":
        return code != "active" or days <= 7
    return True


class MembersTab(Tab):
    title_key = "tab_members"

    def build(self):
        bar = toolbar(self)
        ttk.Label(bar, text=t("search")).pack(side=side_start(), padx=2)
        self.search = tk.StringVar(self)
        self.search_entry = ttk.Entry(bar, textvariable=self.search, width=26)
        self.search_entry.pack(side=side_start(), padx=2)
        ttk.Label(bar, text=t("filter_show")).pack(side=side_start(), padx=(12, 2))
        self.filter = ttk.Combobox(bar, state="readonly", width=20,
                                   values=[t("filter_" + f) for f in FILTERS])
        self.filter.current(0)
        self.filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.filter.pack(side=side_start(), padx=2)
        self.show_archived = tk.BooleanVar(self, value=False)
        ttk.Checkbutton(bar, text=t("show_archived"), variable=self.show_archived,
                        command=self.refresh).pack(side=side_start(), padx=12)

        actions = toolbar(self)
        button(actions, "add_member", self.add)
        button(actions, "open", self.open_selected)
        button(actions, "new_subscription", lambda: self.on_selected(self.subscribe))
        button(actions, "record_payment", lambda: self.on_selected(self.pay))
        ttk.Button(actions, text=t("delete_member"), style="Danger.TButton",
                   command=lambda: self.on_selected(self.delete)).pack(side=side_end(), padx=2)

        self.table = Table(self, [
            ("name", "name", 190, "text"),
            ("phone", "phone", 110, "text"),
            ("end", "end_date", 90, "text"),
            ("status", "status", 170, "text"),
            ("visits", "visits_30", 100, "num"),
            ("last", "last_visit", 95, "text"),
            ("balance", "balance", 80, "num"),
        ], height=18, on_open=lambda iid: self.app.open_member(int(iid)),
            on_menu=self.show_menu)
        self.table.pack(fill=tk.BOTH, expand=True)
        self.table.tree.bind("<Delete>", lambda e: self.on_selected(self.delete))
        self.count = label(self, "", style="Hint.TLabel")
        self.count.pack(fill=tk.X, pady=(4, 0))

        # Debounce typing so a slow PC does not query on every key press.
        self._search_job = None
        self.search.trace_add("write", self._on_search)
        self.search_entry.focus_set()

    def _on_search(self, *_):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(250, self.refresh)

    def set_filter(self, status_filter):
        self.filter.current(FILTERS.index(status_filter))
        self.refresh()

    def refresh(self):
        self._search_job = None
        status_filter = FILTERS[max(self.filter.current(), 0)]
        rows = []
        for m in self.store.list_members(self.search.get(), self.show_archived.get()):
            if not matches(status_filter, m):
                continue
            text, tag = days_status(m["end_date"])
            if m["archived"]:
                text, tag = "%s (%s)" % (text, t("archived")), "muted"
            rows.append((m["id"], {
                "name": m["name"], "phone": m["phone"],
                "end": m["end_date"] or "", "status": text,
                "visits": m["visits_30"] or "", "last": fmt_last_visit(m["last_visit"]),
                "balance": fmt_money(m["balance"]) if m["balance"] else "",
            }, tag))
        self.table.set_rows(rows)
        self.count.configure(text=t("count_rows") % len(rows))

    # actions ---------------------------------------------------------------

    def on_selected(self, action):
        iid = self.table.require_selected()
        if iid is not None:
            action(int(iid))

    def show_menu(self, iid, event):
        member_id = int(iid)
        member = self.store.get_member(member_id)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=t("open"), command=lambda: self.app.open_member(member_id))
        menu.add_command(label=t("check_in_today"), command=lambda: self.check_in(member_id))
        menu.add_separator()
        menu.add_command(label=t("new_subscription"), command=lambda: self.subscribe(member_id))
        menu.add_command(label=t("record_payment"), command=lambda: self.pay(member_id))
        menu.add_command(label=t("add_debt"),
                         command=lambda: self.app.run(self, dialogs.debt_form, self,
                                                      self.store, member_id))
        menu.add_command(label=t("sell"),
                         command=lambda: self.app.run(self, dialogs.sell_form, self,
                                                      self.store, member_id=member_id))
        menu.add_separator()
        archived = bool(member["archived"])
        menu.add_command(label=t("unarchive" if archived else "archive"),
                         command=lambda: self.toggle_archive(member_id, archived))
        menu.add_command(label=t("delete_member"), command=lambda: self.delete(member_id))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def add(self):
        member_id = self.app.run(self, dialogs.member_form, self, self.store)
        if member_id:
            self.app.open_member(member_id)

    def open_selected(self):
        self.on_selected(self.app.open_member)

    def subscribe(self, member_id):
        self.app.run(self, dialogs.subscribe_form, self, self.store, member_id)

    def check_in(self, member_id):
        self.app.show_check_in()
        self.app.tab_of("AttendanceTab").check_in(member_id)

    def pay(self, member_id):
        self.app.run(self, dialogs.payment_form, self, self.store, member_id)

    def toggle_archive(self, member_id, archived):
        if not archived and not confirm(self, "confirm_archive"):
            return
        self.store.set_member_archived(member_id, not archived)
        self.app.data_changed()

    def delete(self, member_id):
        self.app.delete_member(self, member_id)


class MemberWindow(tk.Toplevel):
    """Everything about one member: status, subscriptions and account."""

    def __init__(self, app, member_id):
        tk.Toplevel.__init__(self, app.root)
        self.withdraw()
        self.app = app
        self.store = app.store
        self.member_id = member_id
        self.geometry("900x660")
        self.minsize(700, 520)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())
        self.bind("<F5>", lambda e: self.refresh())

        body = ttk.Frame(self, padding=10)
        body.pack(fill=tk.BOTH, expand=True)

        head = ttk.Frame(body)
        head.pack(fill=tk.X)
        self.avatar = Avatar(head, size=60)
        self.avatar.pack(side=side_start(), padx=(0, 10))
        info = ttk.Frame(head)
        info.pack(side=side_start(), fill=tk.X, expand=True)
        self.name_label = label(info, "", style="Big.TLabel")
        self.name_label.pack(fill=tk.X)
        self.status_label = label(info, "", style="Title.TLabel")
        self.status_label.pack(fill=tk.X)
        self.info_label = label(info, "")
        self.info_label.pack(fill=tk.X)
        # Balance with the less frequent actions under it, so the main
        # toolbar fits on a 1024-pixel-wide screen.
        side_box = ttk.Frame(head)
        side_box.pack(side=side_end(), padx=6, before=info)
        self.balance_label = ttk.Label(side_box, text="", style="Big.TLabel", anchor="e")
        self.balance_label.pack(fill=tk.X)
        manage = ttk.Frame(side_box)
        manage.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(manage, text=t("delete_member"), style="Danger.TButton",
                   command=self.delete).pack(side=side_end(), padx=2)
        self.archive_btn = button(manage, "archive", self.toggle_archive, side=side_end())
        button(manage, "edit", self.edit, side=side_end())

        bar = toolbar(body, pady=8)
        button(bar, "check_in_today", self.check_in)
        button(bar, "new_subscription", self.subscribe)
        button(bar, "record_payment", self.pay)
        button(bar, "add_debt", self.add_debt)
        button(bar, "sell", self.sell)

        stats = ttk.Frame(body)
        stats.pack(fill=tk.X, pady=(0, 8))
        self.stat_labels = {}
        for col, (key, title) in enumerate(ordered(STAT_TILES)):
            box = ttk.LabelFrame(stats, text=t(title), padding=(6, 2))
            box.grid(row=0, column=col, sticky="nsew", padx=2)
            stats.columnconfigure(col, weight=1)
            value = ttk.Label(box, text="-", style="Title.TLabel", anchor="center")
            value.pack(fill=tk.X)
            self.stat_labels[key] = value

        tabs = ttk.Notebook(body)
        tabs.pack(fill=tk.BOTH, expand=True)
        att = ttk.Frame(tabs, padding=8)
        self.calendar = MonthCalendar(att, on_click=self.toggle_day,
                                      on_month=self.refresh_calendar)
        self.calendar.pack()
        label(att, t("calendar_hint"), style="Hint.TLabel", wraplength=640).pack(pady=(6, 0))
        subs = ttk.Frame(tabs, padding=6)
        hist = ttk.Frame(tabs, padding=6)
        pages = [(att, "tab_attendance"), (subs, "subscriptions"), (hist, "history")]
        for page, key in ordered(pages):
            tabs.add(page, text="  %s  " % t(key))
        tabs.select(att)

        self.subs = Table(subs, [
            ("plan", "plan", 200, "text"),
            ("start", "start", 100, "text"),
            ("end", "end_date", 100, "text"),
            ("price", "price", 90, "num"),
        ], height=8)
        self.subs.pack(fill=tk.BOTH, expand=True)
        sbar = toolbar(subs, pady=(4, 0))
        button(sbar, "delete", self.delete_subscription, side=side_end())

        self.hist = Table(hist, [
            ("date", "date", 100, "text"),
            ("type", "type", 90, "text"),
            ("desc", "description", 300, "text"),
            ("amount", "amount", 100, "num"),
        ], height=8)
        self.hist.pack(fill=tk.BOTH, expand=True)
        hbar = toolbar(hist, pady=(4, 0))
        button(hbar, "delete_entry", self.delete_entry, side=side_end())

        self.refresh()
        center(self, app.root)
        self.deiconify()

    def close(self):
        self.app.member_windows.pop(self.member_id, None)
        self.destroy()

    def refresh(self):
        m = self.store.get_member(self.member_id)
        if m is None:
            self.close()
            return
        self.member = m
        self.title(m["name"])
        self.avatar.show(m["name"])
        self.name_label.configure(text=m["name"])
        end = self.store.member_end_date(self.member_id)
        status, tag = days_status(end)
        colours = {"ok": "#1b7f3b", "warn": "#b36b00", "expired": "#b00020"}
        self.status_label.configure(text=status, foreground=colours.get(tag, ""))
        parts = [m["phone"], "%s: %s" % (t("end_date"), end or "-"), m["notes"]]
        self.info_label.configure(text=bidi("   |   ".join(p for p in parts if p)))
        balance = self.store.member_balance(self.member_id)
        self.balance_label.configure(
            text=bidi("%s: %s" % (t("balance"), fmt_money(balance, self.app.currency))),
            style="BigDebt.TLabel" if balance > 0 else "Big.TLabel")
        self.archive_btn.configure(text=t("unarchive" if m["archived"] else "archive"))

        self.subs.set_rows(
            (s["id"], {"plan": s["plan_name"], "start": s["start_date"],
                       "end": s["end_date"], "price": fmt_money(s["price"])}, "")
            for s in self.store.list_subscriptions(self.member_id))

        rows = []
        for h in self.store.member_history(self.member_id):
            is_charge = h["type"] == "charge"
            rows.append(("%s%d" % (h["type"][0], h["id"]), {
                "date": h["on_date"],
                "type": t("type_charge" if is_charge else "type_payment"),
                "desc": h["description"],
                "amount": fmt_money(h["amount"] if is_charge else -h["amount"]),
            }, "expired" if is_charge else "ok"))
        self.hist.set_rows(rows)

        stats = self.store.attendance_stats(self.member_id)
        for key, _title in STAT_TILES:
            value = stats[key]
            if key == "last_visit":
                value = fmt_last_visit(value)
            elif key == "streak_weeks":
                value = "%d" % value
            self.stat_labels[key].configure(text=str(value))
        self.refresh_calendar()

    def refresh_calendar(self):
        first, last = self.calendar.month_range()
        self.calendar.show(self.store.attendance_dates(self.member_id, first, last),
                           self.store.subscription_days(self.member_id, first, last))

    # actions ---------------------------------------------------------------

    def check_in(self):
        self.app.show_check_in()
        self.app.tab_of("AttendanceTab").check_in(self.member_id)

    def toggle_day(self, date):
        self.store.toggle_check_in(self.member_id, date)
        self.app.data_changed()

    def subscribe(self):
        self.app.run(self, dialogs.subscribe_form, self, self.store, self.member_id)

    def pay(self):
        self.app.run(self, dialogs.payment_form, self, self.store, self.member_id)

    def add_debt(self):
        self.app.run(self, dialogs.debt_form, self, self.store, self.member_id)

    def sell(self):
        self.app.run(self, dialogs.sell_form, self, self.store, member_id=self.member_id)

    def edit(self):
        self.app.run(self, dialogs.member_form, self, self.store, self.member)

    def delete(self):
        self.app.delete_member(self, self.member_id)

    def toggle_archive(self):
        archived = bool(self.member["archived"])
        if not archived and not confirm(self, "confirm_archive"):
            return
        self.store.set_member_archived(self.member_id, not archived)
        self.app.data_changed()

    def delete_subscription(self):
        iid = self.subs.require_selected()
        if iid is not None and confirm(self, "confirm_delete"):
            self.store.delete_subscription(int(iid))
            self.app.data_changed()

    def delete_entry(self):
        iid = self.hist.require_selected()
        if iid is None:
            return
        kind, entry_id = iid[0], int(iid[1:])
        if kind == "c":
            charge = self.store.get_charge(entry_id)
            if charge is not None and charge["kind"] != "other":
                show_error(self, "cannot_delete_linked")
                return
        if not confirm(self, "confirm_delete"):
            return
        if kind == "c":
            self.store.delete_charge(entry_id)
        else:
            self.store.delete_payment(entry_id)
        self.app.data_changed()
