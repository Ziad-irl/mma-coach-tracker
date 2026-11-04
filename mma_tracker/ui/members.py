import tkinter as tk
from tkinter import ttk

from ..i18n import t
from . import dialogs
from .app import Tab
from .widgets import (Table, button, center, confirm, days_status, fmt_money,
                      label, show_error, side_end, side_start, toolbar)


class MembersTab(Tab):
    title_key = "tab_members"

    def build(self):
        bar = toolbar(self)
        ttk.Label(bar, text=t("search")).pack(side=side_start(), padx=2)
        self.search = tk.StringVar(self)
        entry = ttk.Entry(bar, textvariable=self.search, width=28)
        entry.pack(side=side_start(), padx=2)
        self.show_archived = tk.BooleanVar(self, value=False)
        ttk.Checkbutton(bar, text=t("show_archived"), variable=self.show_archived,
                        command=self.refresh).pack(side=side_start(), padx=8)
        button(bar, "add_member", self.add, side=side_end())
        button(bar, "open", self.open_selected, side=side_end())

        self.table = Table(self, [
            ("name", "name", 220, "text"),
            ("phone", "phone", 130, "text"),
            ("end", "end_date", 100, "text"),
            ("left", "days_left", 110, "text"),
            ("balance", "balance", 100, "num"),
        ], height=18, on_open=lambda iid: self.app.open_member(int(iid)))
        self.table.pack(fill=tk.BOTH, expand=True)

        # Debounce typing so a slow PC does not query on every key press.
        self._search_job = None
        self.search.trace_add("write", self._on_search)
        entry.focus_set()

    def _on_search(self, *_):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(250, self.refresh)

    def refresh(self):
        self._search_job = None
        rows = []
        for m in self.store.list_members(self.search.get(), self.show_archived.get()):
            text, tag = days_status(m["end_date"])
            if m["archived"]:
                tag = "muted"
            rows.append((m["id"], {
                "name": m["name"], "phone": m["phone"],
                "end": m["end_date"] or "", "left": text,
                "balance": fmt_money(m["balance"]) if m["balance"] else "",
            }, tag))
        self.table.set_rows(rows)

    def add(self):
        member_id = self.app.run(self, dialogs.member_form, self, self.store)
        if member_id:
            self.app.open_member(member_id)

    def open_selected(self):
        iid = self.table.require_selected()
        if iid is not None:
            self.app.open_member(int(iid))


class MemberWindow(tk.Toplevel):
    """Everything about one member: status, subscriptions and account."""

    def __init__(self, app, member_id):
        tk.Toplevel.__init__(self, app.root)
        self.withdraw()
        self.app = app
        self.store = app.store
        self.member_id = member_id
        self.geometry("820x560")
        self.minsize(640, 460)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())

        body = ttk.Frame(self, padding=10)
        body.pack(fill=tk.BOTH, expand=True)

        head = ttk.Frame(body)
        head.pack(fill=tk.X)
        info = ttk.Frame(head)
        info.pack(side=side_start(), fill=tk.X, expand=True)
        self.name_label = label(info, "", style="Big.TLabel")
        self.name_label.pack(fill=tk.X)
        self.info_label = label(info, "")
        self.info_label.pack(fill=tk.X)
        self.balance_label = ttk.Label(head, text="", style="Big.TLabel")
        self.balance_label.pack(side=side_end(), padx=6)

        bar = toolbar(body, pady=8)
        button(bar, "new_subscription", self.subscribe)
        button(bar, "record_payment", self.pay)
        button(bar, "add_debt", self.add_debt)
        button(bar, "sell", self.sell)
        button(bar, "edit", self.edit)
        self.archive_btn = button(bar, "archive", self.toggle_archive, side=side_end())

        subs = ttk.LabelFrame(body, text=t("subscriptions"), padding=6)
        subs.pack(fill=tk.BOTH, expand=False)
        self.subs = Table(subs, [
            ("plan", "plan", 200, "text"),
            ("start", "start", 100, "text"),
            ("end", "end_date", 100, "text"),
            ("price", "price", 90, "num"),
        ], height=5)
        self.subs.pack(fill=tk.BOTH, expand=True)
        sbar = toolbar(subs, pady=(4, 0))
        button(sbar, "delete", self.delete_subscription, side=side_end())

        hist = ttk.LabelFrame(body, text=t("history"), padding=6)
        hist.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
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
        self.name_label.configure(text=m["name"])
        end = self.store.member_end_date(self.member_id)
        status, _tag = days_status(end)
        parts = [m["phone"], "%s: %s" % (t("end_date"), end or "-"),
                 "%s: %s" % (t("days_left"), status), m["notes"]]
        self.info_label.configure(text="   |   ".join(p for p in parts if p))
        balance = self.store.member_balance(self.member_id)
        self.balance_label.configure(
            text="%s: %s" % (t("balance"), fmt_money(balance, self.app.currency)),
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
            }, "expired" if is_charge else ""))
        self.hist.set_rows(rows)

    # actions ---------------------------------------------------------------

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
