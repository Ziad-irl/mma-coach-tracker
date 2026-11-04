"""Main window. Switching language rebuilds every widget from scratch."""

import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from tkinter import ttk

from .. import export, i18n
from ..i18n import t
from ..store import ValidationError
from .widgets import confirm_danger, label, ordered, show_error, show_info

# Base font size, table row height and headline size per text-size setting.
TEXT_SIZES = {"normal": (10, 24, 16), "large": (12, 30, 19)}


class Tab(ttk.Frame):
    title_key = ""

    def __init__(self, master, app):
        ttk.Frame.__init__(self, master, padding=8)
        self.app = app
        self.store = app.store
        self.build()

    def build(self):
        raise NotImplementedError

    def refresh(self):
        pass


class App(object):
    def __init__(self, root, store):
        self.root = root
        self.store = store
        self.member_windows = {}
        root.minsize(760, 520)
        root.geometry("1000x660")
        i18n.set_language(store.get_setting("language", "en"))
        self._bind_keys()
        self.build()

    @property
    def currency(self):
        return self.store.get_setting("currency", "")

    def _setup_style(self):
        # Tahoma has good Arabic glyphs on every Windows version since XP.
        family = "Tahoma" if i18n.is_rtl() else "Segoe UI"
        size, row, big = TEXT_SIZES.get(self.store.get_setting("text_size"), TEXT_SIZES["normal"])
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(name).configure(family=family, size=size)
        style = ttk.Style(self.root)
        style.configure("Treeview", rowheight=row)
        style.configure("Treeview.Heading", font=(family, size, "bold"))
        style.configure("TButton", padding=(8, 3))
        style.configure("Big.TLabel", font=(family, big, "bold"))
        style.configure("Title.TLabel", font=(family, size + 2, "bold"))
        style.configure("Hint.TLabel", foreground="#666666")
        style.configure("Debt.TLabel", foreground="#b00020")
        style.configure("BigDebt.TLabel", font=(family, big, "bold"), foreground="#b00020")
        style.configure("Danger.TButton", foreground="#b00020")

        # Tk 8.6.9 (bundled with Python 3.8.10) ignores Treeview tag colours
        # unless these default state maps are removed.
        def fixed_map(option):
            return [e for e in style.map("Treeview", query_opt=option)
                    if e[:2] != ("!disabled", "!selected")]
        style.map("Treeview", foreground=fixed_map("foreground"),
                  background=fixed_map("background"))

    def _bind_keys(self):
        self.root.bind("<F5>", lambda e: self.refresh_current())
        for key in ("<Control-f>", "<Control-F>"):
            self.root.bind(key, lambda e: self.show_members(focus_search=True))
        for key in ("<Control-n>", "<Control-N>"):
            self.root.bind(key, lambda e: self.members_tab().add())

    def build(self):
        from .dashboard import DashboardTab
        from .debts import DebtsTab
        from .equipment import EquipmentTab
        from .members import MembersTab
        from .settings import SettingsTab
        tab_classes = [DashboardTab, MembersTab, EquipmentTab, DebtsTab, SettingsTab]

        for child in self.root.winfo_children():
            child.destroy()
        self.member_windows = {}
        self.root.title(t("app_title"))
        self._setup_style()

        hint = label(self.root, t("hint_main"), style="Hint.TLabel", padding=(8, 0, 8, 4))
        hint.pack(side=tk.BOTTOM, fill=tk.X)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 2))
        self.tabs = [cls(self.notebook, self) for cls in tab_classes]
        for tab in ordered(self.tabs):
            self.notebook.add(tab, text="  %s  " % t(tab.title_key))
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.refresh_current())
        self.notebook.select(self.tabs[0])
        self.refresh_current()

    def current_tab(self):
        return self.root.nametowidget(self.notebook.select())

    def refresh_current(self):
        self.current_tab().refresh()

    def data_changed(self):
        """Refresh the visible tab and any open member windows."""
        self.refresh_current()
        for win in list(self.member_windows.values()):
            win.refresh()

    def run(self, parent, func, *args, **kwargs):
        """Call func; show ValidationError messages; refresh if data changed."""
        try:
            changed = func(*args, **kwargs)
        except ValidationError as e:
            show_error(parent, str(e))
            return None
        if changed:
            self.data_changed()
        return changed

    def set_language(self, code):
        self.store.set_setting("language", code)
        i18n.set_language(code)
        self.build()

    def set_text_size(self, size):
        self.store.set_setting("text_size", size)
        self.build()

    # navigation ----------------------------------------------------------------

    def tab_of(self, cls_name):
        for tab in self.tabs:
            if type(tab).__name__ == cls_name:
                return tab

    def members_tab(self):
        tab = self.tab_of("MembersTab")
        self.notebook.select(tab)
        return tab

    def show_members(self, status=None, focus_search=False):
        tab = self.members_tab()
        if status is not None:
            tab.set_filter(status)
        if focus_search:
            tab.search_entry.focus_set()
            tab.search_entry.select_range(0, tk.END)

    def show_tab(self, cls_name):
        self.notebook.select(self.tab_of(cls_name))

    def open_member(self, member_id):
        from .members import MemberWindow
        win = self.member_windows.get(member_id)
        if win is None or not win.winfo_exists():
            win = MemberWindow(self, member_id)
            self.member_windows[member_id] = win
        win.deiconify()
        win.lift()
        win.focus_set()

    # shared actions --------------------------------------------------------------

    def delete_member(self, parent, member_id):
        member = self.store.get_member(member_id)
        if member is None:
            return False
        if not confirm_danger(parent, t("confirm_delete_member") % member["name"]):
            return False
        win = self.member_windows.pop(member_id, None)
        if win is not None:
            win.destroy()
        self.store.delete_member(member_id)
        self.data_changed()
        return True

    def export_excel(self, parent):
        path = filedialog.asksaveasfilename(
            parent=parent, defaultextension=".xlsx",
            initialfile="MMA-%s.xlsx" % datetime.date.today().isoformat(),
            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            export.export_all(self.store, path)
        except (IOError, OSError) as e:  # e.g. the file is open in Excel
            messagebox.showerror(t("error"), str(e), parent=parent)
            return
        if messagebox.askyesno(t("app_title"), t("export_done") % path + "\n\n" + t("open_file_now"),
                               parent=parent):
            try:
                os.startfile(path)
            except OSError:
                show_info(parent, t("export_done") % path)
