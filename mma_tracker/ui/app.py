"""Main window. Switching language rebuilds every widget from scratch."""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from .. import i18n
from ..i18n import t
from ..store import ValidationError
from .widgets import ordered, show_error


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
        root.geometry("980x640")
        i18n.set_language(store.get_setting("language", "en"))
        self.build()

    @property
    def currency(self):
        return self.store.get_setting("currency", "")

    def _setup_fonts(self):
        # Tahoma has good Arabic glyphs on every Windows version since XP.
        family = "Tahoma" if i18n.is_rtl() else "Segoe UI"
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(name).configure(family=family, size=10)
        style = ttk.Style(self.root)
        style.configure("Treeview", rowheight=22)
        style.configure("Big.TLabel", font=(family, 16, "bold"))
        style.configure("Title.TLabel", font=(family, 12, "bold"))
        style.configure("Debt.TLabel", foreground="#b00020")
        style.configure("BigDebt.TLabel", font=(family, 16, "bold"), foreground="#b00020")

    def build(self):
        from .dashboard import DashboardTab
        from .debts import DebtsTab
        from .equipment import EquipmentTab
        from .members import MembersTab
        tab_classes = [DashboardTab, MembersTab, EquipmentTab, DebtsTab]

        for child in self.root.winfo_children():
            child.destroy()
        self.member_windows = {}
        self.root.title(t("app_title"))
        self._setup_fonts()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
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

    def open_member(self, member_id):
        from .members import MemberWindow
        win = self.member_windows.get(member_id)
        if win is None or not win.winfo_exists():
            win = MemberWindow(self, member_id)
            self.member_windows[member_id] = win
        win.deiconify()
        win.lift()
        win.focus_set()
