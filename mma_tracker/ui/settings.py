import datetime
import os
import tkinter as tk
from tkinter import filedialog, ttk

from .. import __version__, backup, i18n
from ..i18n import t
from . import dialogs
from .app import Tab
from .widgets import (Table, button, confirm, fmt_money, label, show_info,
                      side_end, side_start, toolbar)


class SettingsTab(Tab):
    title_key = "tab_settings"

    def build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X)

        lang = ttk.LabelFrame(top, text=t("language"), padding=8)
        lang.pack(side=side_start(), fill=tk.Y, padx=(0, 8))
        self.lang = tk.StringVar(self, value=i18n.language())
        for code, name in i18n.LANGUAGES:
            ttk.Radiobutton(lang, text=name, value=code, variable=self.lang,
                            command=self.change_language).pack(side=side_start(), padx=6)

        size = ttk.LabelFrame(top, text=t("text_size"), padding=8)
        size.pack(side=side_start(), fill=tk.Y, padx=(0, 8))
        self.text_size = tk.StringVar(self, value=self.store.get_setting("text_size", "normal"))
        for code in ("normal", "large"):
            ttk.Radiobutton(size, text=t("size_" + code), value=code, variable=self.text_size,
                            command=self.change_text_size).pack(side=side_start(), padx=6)

        cur = ttk.LabelFrame(top, text=t("currency"), padding=8)
        cur.pack(side=side_start(), fill=tk.Y, padx=(0, 8))
        self.currency = tk.StringVar(self, value=self.app.currency)
        ttk.Entry(cur, textvariable=self.currency, width=8).pack(side=side_start(), padx=4)
        button(cur, "save", self.save_currency)

        data = ttk.Frame(self)
        data.pack(fill=tk.X, pady=(8, 0))
        bk = ttk.LabelFrame(data, text=t("backup"), padding=8)
        bk.pack(side=side_start(), fill=tk.BOTH, expand=True, padx=(0, 8))
        label(bk, t("auto_backup_info"), wraplength=380).pack(fill=tk.X)
        bar = toolbar(bk, pady=(6, 0))
        button(bar, "backup_now", self.backup_now)
        button(bar, "open_data_folder", self.open_data_folder)

        ex = ttk.LabelFrame(data, text=t("export"), padding=8)
        ex.pack(side=side_start(), fill=tk.BOTH, expand=True)
        label(ex, t("export_info"), wraplength=380).pack(fill=tk.X)
        bar = toolbar(ex, pady=(6, 0))
        button(bar, "export_excel", lambda: self.app.export_excel(self))

        plans = ttk.LabelFrame(self, text=t("plans"), padding=6)
        plans.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        bar = toolbar(plans)
        button(bar, "add_plan", self.add_plan)
        button(bar, "edit", self.edit_plan)
        button(bar, "delete", self.remove_plan, side=side_end())
        self.plans = Table(plans, [
            ("name", "name", 260, "text"),
            ("days", "days", 80, "num"),
            ("price", "price", 110, "num"),
        ], height=8, on_open=lambda iid: self.edit_plan())
        self.plans.pack(fill=tk.BOTH, expand=True)

        label(self, "%s %s   |   %s" % (t("version"), __version__, self.store.path),
              style="TLabel").pack(fill=tk.X, pady=(6, 0))

    def refresh(self):
        self.plans.set_rows(
            (p["id"], {"name": p["name"], "days": p["days"],
                       "price": fmt_money(p["price"])}, "")
            for p in self.store.list_plans())

    # language & currency -----------------------------------------------------

    def change_language(self):
        # Rebuilding destroys this tab, so defer until the click has finished.
        self.after_idle(self.app.set_language, self.lang.get())

    def change_text_size(self):
        self.after_idle(self.app.set_text_size, self.text_size.get())

    def save_currency(self):
        self.store.set_setting("currency", self.currency.get().strip())
        show_info(self, t("saved"))

    # plans -------------------------------------------------------------------

    def _selected_plan(self):
        iid = self.plans.require_selected()
        return None if iid is None else self.store.get_plan(int(iid))

    def add_plan(self):
        self.app.run(self, dialogs.plan_form, self, self.store)

    def edit_plan(self):
        plan = self._selected_plan()
        if plan is not None:
            self.app.run(self, dialogs.plan_form, self, self.store, plan)

    def remove_plan(self):
        plan = self._selected_plan()
        if plan is not None and confirm(self, "confirm_archive_plan"):
            self.store.archive_plan(plan["id"])
            self.app.data_changed()

    # backup ------------------------------------------------------------------

    def backup_now(self):
        name = "tracker-backup-%s.db" % datetime.datetime.now().strftime("%Y%m%d-%H%M")
        path = filedialog.asksaveasfilename(
            parent=self, initialfile=name, defaultextension=".db",
            filetypes=[("SQLite database", "*.db")])
        if path:
            backup.backup_to(self.store, path)
            show_info(self, t("backup_done") % path)

    def open_data_folder(self):
        os.startfile(os.path.dirname(os.path.abspath(self.store.path)))
