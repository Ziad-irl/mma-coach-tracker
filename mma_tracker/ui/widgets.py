"""Small reusable Tk pieces that understand right-to-left layout."""

import datetime
import tkinter as tk
from tkinter import messagebox, ttk

from .. import i18n
from ..i18n import t
from ..store import ValidationError, money, parse_date


# ------------------------------------------------------------------ layout

def side_start():
    """Pack side where reading starts (left for English, right for Arabic)."""
    return tk.RIGHT if i18n.is_rtl() else tk.LEFT


def side_end():
    return tk.LEFT if i18n.is_rtl() else tk.RIGHT


def anchor_start():
    return "e" if i18n.is_rtl() else "w"


def justify():
    return tk.RIGHT if i18n.is_rtl() else tk.LEFT


def ordered(items):
    """Reverse a left-to-right sequence when the UI is right-to-left."""
    items = list(items)
    if i18n.is_rtl():
        items.reverse()
    return items


def toolbar(parent, pady=(0, 6)):
    bar = ttk.Frame(parent)
    bar.pack(fill=tk.X, pady=pady)
    return bar


def button(parent, key, command, side=None):
    b = ttk.Button(parent, text=t(key), command=command)
    b.pack(side=side or side_start(), padx=2)
    return b


def label(parent, text, **kw):
    kw.setdefault("anchor", anchor_start())
    kw.setdefault("justify", justify())
    return ttk.Label(parent, text=text, **kw)


# ------------------------------------------------------------- formatting

def fmt_money(value, currency=None):
    s = "{:,.2f}".format(money(value))
    if s.endswith(".00"):
        s = s[:-3]
    return "%s %s" % (s, currency) if currency else s


def days_status(end_date):
    """(text, tag) for a subscription end date (str/date/None)."""
    if not end_date:
        return t("status_none"), "expired"
    left = (parse_date(end_date) - datetime.date.today()).days
    if left < 0:
        return t("status_expired"), "expired"
    return str(left), ("warn" if left <= 7 else "")


# ---------------------------------------------------------------- dialogs

def show_error(parent, key):
    messagebox.showerror(t("error"), t(key), parent=parent)


def show_info(parent, text):
    messagebox.showinfo(t("app_title"), text, parent=parent)


def confirm(parent, key):
    return messagebox.askyesno(t("confirm"), t(key), parent=parent)


def center(win, parent):
    win.update_idletasks()
    top = parent.winfo_toplevel()
    x = top.winfo_rootx() + (top.winfo_width() - win.winfo_reqwidth()) // 2
    y = top.winfo_rooty() + (top.winfo_height() - win.winfo_reqheight()) // 3
    win.geometry("+%d+%d" % (max(x, 0), max(y, 0)))


# ------------------------------------------------------------------ table

class Table(ttk.Frame):
    """Treeview with a scrollbar.

    columns: [(key, heading_i18n_key, width, kind)] where kind is
    "text" or "num" (numbers are always right-aligned).
    rows for set_rows(): [(iid, {key: value}, tag)].
    """

    def __init__(self, parent, columns, height=10, on_open=None):
        ttk.Frame.__init__(self, parent)
        cols = ordered(columns)
        self.keys = [c[0] for c in cols]  # display order, values follow it
        self.tree = ttk.Treeview(self, columns=[c[0] for c in cols],
                                 show="headings", height=height,
                                 selectmode="browse")
        sb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        for key, head, width, kind in cols:
            anchor = "e" if kind == "num" else anchor_start()
            self.tree.heading(key, text=t(head), anchor=anchor)
            self.tree.column(key, width=width, minwidth=40, anchor=anchor)
        self.tree.tag_configure("expired", foreground="#b00020")
        self.tree.tag_configure("warn", foreground="#b36b00")
        self.tree.tag_configure("muted", foreground="#777777")
        sb.pack(side=side_end(), fill=tk.Y)
        self.tree.pack(side=side_start(), fill=tk.BOTH, expand=True)
        if on_open:
            self.tree.bind("<Double-1>", lambda e: self._open(on_open))
            self.tree.bind("<Return>", lambda e: self._open(on_open))

    def _open(self, callback):
        iid = self.selected()
        if iid is not None:
            callback(iid)

    def set_rows(self, rows):
        selected = self.selected()
        self.tree.delete(*self.tree.get_children())
        for iid, values, tag in rows:
            self.tree.insert("", tk.END, iid=str(iid),
                             values=[values.get(k, "") for k in self.keys],
                             tags=(tag,) if tag else ())
        if selected is not None and self.tree.exists(selected):
            self.tree.selection_set(selected)

    def selected(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def require_selected(self):
        iid = self.selected()
        if iid is None:
            show_error(self, "select_row_first")
        return iid


# ------------------------------------------------------------ form dialog

class FormDialog(tk.Toplevel):
    """Modal form. Fields are added with add_field(); on Save the values
    are converted and passed to on_submit(values). If on_submit raises
    ValidationError the message is shown and the dialog stays open."""

    def __init__(self, parent, title, on_submit):
        tk.Toplevel.__init__(self, parent)
        self.withdraw()
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.on_submit = on_submit
        self.result = None
        self.fields = []
        self.vars = {}
        self.widgets = {}
        self.body = ttk.Frame(self, padding=12)
        self.body.pack(fill=tk.BOTH, expand=True)
        lc, wc = (1, 0) if i18n.is_rtl() else (0, 1)
        self._label_col, self._widget_col = lc, wc
        self.body.columnconfigure(wc, weight=1)
        bar = ttk.Frame(self, padding=(12, 0, 12, 12))
        bar.pack(fill=tk.X)
        ttk.Button(bar, text=t("cancel"), command=self.destroy).pack(side=side_end(), padx=2)
        ttk.Button(bar, text=t("save"), command=self._submit).pack(side=side_end(), padx=2)
        self.bind("<Return>", lambda e: self._submit())
        self.bind("<Escape>", lambda e: self.destroy())

    def add_field(self, key, label_key, value="", kind="text", choices=None, width=30):
        """kind: text, money, int, date, or choice (choices = [(value, label)])."""
        row = len(self.fields)
        ttk.Label(self.body, text=t(label_key)).grid(
            row=row, column=self._label_col, sticky=anchor_start(), padx=6, pady=3)
        if kind == "choice":
            labels = [c[1] for c in choices]
            widget = ttk.Combobox(self.body, values=labels, state="readonly",
                                  width=width - 2, justify=justify())
            values = [c[0] for c in choices]
            if value in values:
                widget.current(values.index(value))
            elif labels:
                widget.current(0)
            var = widget
        else:
            if isinstance(value, float):
                value = fmt_money(value).replace(",", "")
            var = tk.StringVar(self, value="" if value is None else str(value))
            entry_justify = tk.RIGHT if kind in ("money", "int") else justify()
            widget = ttk.Entry(self.body, textvariable=var, width=width,
                               justify=entry_justify)
        widget.grid(row=row, column=self._widget_col, sticky="ew", padx=6, pady=3)
        self.fields.append((key, kind, choices))
        self.vars[key] = var
        self.widgets[key] = widget
        return widget

    def get_raw(self, key):
        return self.vars[key].get()

    def set_raw(self, key, value):
        if isinstance(value, float):
            value = fmt_money(value).replace(",", "")
        self.vars[key].set(value)

    def choice_value(self, key):
        for k, kind, choices in self.fields:
            if k == key:
                index = self.widgets[key].current()
                return choices[index][0] if index >= 0 else None
        raise KeyError(key)

    def values(self):
        out = {}
        for key, kind, choices in self.fields:
            if kind == "choice":
                out[key] = self.choice_value(key)
                continue
            raw = self.vars[key].get().strip()
            if kind == "money":
                try:
                    out[key] = money(raw.replace(",", "") or 0)
                except ValueError:
                    raise ValidationError("err_bad_number")
            elif kind == "int":
                try:
                    out[key] = int(raw or 0)
                except ValueError:
                    raise ValidationError("err_bad_number")
            elif kind == "date":
                try:
                    out[key] = parse_date(raw)
                except ValueError:
                    raise ValidationError("err_bad_date")
            else:
                out[key] = raw
        return out

    def _submit(self):
        try:
            values = self.values()
            self.result = self.on_submit(values)
            if self.result is None:
                self.result = True
        except ValidationError as e:
            show_error(self, str(e))
            return
        self.destroy()

    def show(self):
        center(self, self.master)
        self.deiconify()
        self.grab_set()
        if self.fields:
            self.widgets[self.fields[0][0]].focus_set()
        self.wait_window()
        return self.result
