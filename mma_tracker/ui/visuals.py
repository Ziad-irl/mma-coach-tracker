"""Lightweight visuals drawn on a Tk Canvas: bar chart, month calendar,
initials avatar and a coloured feedback banner. No images or extra
libraries, so they stay fast on old PCs."""

import calendar
import datetime
import tkinter as tk
import zlib
from tkinter import font as tkfont
from tkinter import ttk

from .. import i18n
from ..i18n import bidi, t_list
from .widgets import anchor_start, ordered, side_end, side_start

GREEN = "#2e7d32"
BLUE_LIGHT = "#d6e6f7"
RED = "#c62828"
GRID = "#e3e7ee"
MUTED = "#8a8f98"
AVATAR_COLOURS = ("#c62828", "#ad1457", "#6a1b9a", "#283593", "#1565c0",
                  "#00838f", "#2e7d32", "#ef6c00", "#4e342e", "#37474f")
SATURDAY = 5  # the gym's week starts on Saturday


def ui_font(size=None, weight="normal"):
    family = "Tahoma" if i18n.is_rtl() else "Segoe UI"
    base = tkfont.nametofont("TkDefaultFont").cget("size") if size is None else size
    return (family, base, weight)


def background(widget):
    return ttk.Style(widget).lookup("TFrame", "background") or "#f0f0f0"


# ------------------------------------------------------------------ chart

class BarChart(tk.Canvas):
    """Vertical bars with a hover read-out. Redraws itself on resize."""

    def __init__(self, parent, height=150, colour="#1f6fb2", fmt=str, label_every=1):
        tk.Canvas.__init__(self, parent, height=height, highlightthickness=0,
                           bg="white", bd=0)
        self.colour = colour
        self.fmt = fmt
        self.label_every = label_every
        self.points = []
        self.bind("<Configure>", lambda e: self.redraw())

    def set_data(self, points):
        """points: [(label, value)] oldest first."""
        self.points = ordered(points)
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or not self.points:
            return
        small = ui_font(8)
        top, bottom, side = 22, 20, 8
        n = len(self.points)
        peak = max(v for _l, v in self.points) or 1
        slot = float(w - 2 * side) / n
        bar = max(slot * 0.7, 2)
        self.create_line(side, h - bottom, w - side, h - bottom, fill=GRID)
        self.readout = self.create_text(w / 2, 4, anchor="n", text="", font=ui_font(9, "bold"),
                                        fill="#333333")
        newest = 0 if i18n.is_rtl() else n - 1
        for i, (label, value) in enumerate(self.points):
            x0 = side + i * slot + (slot - bar) / 2
            bar_h = (h - top - bottom) * value / float(peak)
            colour = self.colour if i == newest else self._tint(self.colour)
            item = self.create_rectangle(x0, h - bottom - max(bar_h, 1), x0 + bar,
                                         h - bottom, fill=colour, outline="")
            text = "%s:  %s" % (label, self.fmt(value))
            self.tag_bind(item, "<Enter>", lambda e, s=text: self.itemconfigure(self.readout, text=s))
            self.tag_bind(item, "<Leave>", lambda e: self.itemconfigure(self.readout, text=""))
            if n <= 12 and value:
                self.create_text(x0 + bar / 2, h - bottom - bar_h - 2, anchor="s",
                                 text=self.fmt(value), font=small, fill="#555555")
            if (n - 1 - i if i18n.is_rtl() else i) % self.label_every == 0 or i == newest:
                self.create_text(x0 + bar / 2, h - bottom + 3, anchor="n",
                                 text=label, font=small, fill=MUTED)

    @staticmethod
    def _tint(colour):
        """Lighter version of a #rrggbb colour for older bars."""
        r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
        return "#%02x%02x%02x" % tuple(int(c + (255 - c) * 0.45) for c in (r, g, b))


# --------------------------------------------------------------- calendar

class MonthCalendar(ttk.Frame):
    """Month grid: attended days green, subscribed days light blue.
    Clicking a day calls on_click(date)."""

    CELL_W, CELL_H = 44, 30

    def __init__(self, parent, on_click=None, on_month=None):
        ttk.Frame.__init__(self, parent)
        self.on_click = on_click
        self.on_month = on_month
        today = datetime.date.today()
        self.year, self.month = today.year, today.month
        head = ttk.Frame(self)
        head.pack(fill=tk.X)
        prev_text, next_text = ("<", ">") if not i18n.is_rtl() else (">", "<")
        ttk.Button(head, text=prev_text, width=3, command=lambda: self.shift(-1)).pack(side=side_start())
        ttk.Button(head, text=next_text, width=3, command=lambda: self.shift(1)).pack(side=side_end())
        self.title_label = ttk.Label(head, text="", style="Title.TLabel", anchor="center")
        self.title_label.pack(fill=tk.X, expand=True)
        self.canvas = tk.Canvas(self, width=self.CELL_W * 7, height=self.CELL_H * 7,
                                highlightthickness=0, bg="white")
        self.canvas.pack(pady=(4, 0))
        self.attended = set()
        self.subscribed = set()

    def shift(self, months):
        index = self.year * 12 + self.month - 1 + months
        self.year, self.month = divmod(index, 12)
        self.month += 1
        if self.on_month:
            self.on_month()

    def month_range(self):
        last = calendar.monthrange(self.year, self.month)[1]
        return datetime.date(self.year, self.month, 1), datetime.date(self.year, self.month, last)

    def show(self, attended, subscribed):
        self.attended, self.subscribed = set(attended), set(subscribed)
        names = t_list("month_names")
        self.title_label.configure(text=bidi("%s %d" % (names[self.month - 1], self.year)))
        c = self.canvas
        c.delete("all")
        cw, ch = self.CELL_W, self.CELL_H
        for i, name in enumerate(t_list("weekday_names")):
            col = 6 - i if i18n.is_rtl() else i
            c.create_text(col * cw + cw / 2, ch / 2, text=name, font=ui_font(8, "bold"), fill=MUTED)
        first, last = self.month_range()
        today = datetime.date.today()
        offset = (first.weekday() - SATURDAY) % 7
        for day in range(1, last.day + 1):
            date = datetime.date(self.year, self.month, day)
            cell = offset + day - 1
            row, col = divmod(cell, 7)
            if i18n.is_rtl():
                col = 6 - col
            x0, y0 = col * cw + 2, (row + 1) * ch + 2
            iso = date.isoformat()
            if iso in self.attended:
                fill, fg = GREEN, "white"
            elif iso in self.subscribed:
                fill, fg = BLUE_LIGHT, "#1d3557"
            else:
                fill, fg = "white", (MUTED if date > today else "#333333")
            outline, width = (RED, 2) if date == today else (GRID, 1)
            rect = c.create_rectangle(x0, y0, x0 + cw - 4, y0 + ch - 4, fill=fill,
                                      outline=outline, width=width)
            text = c.create_text(x0 + (cw - 4) / 2, y0 + (ch - 4) / 2, text=str(day),
                                 fill=fg, font=ui_font(9, "bold" if iso in self.attended else "normal"))
            if self.on_click and date <= today:
                for item in (rect, text):
                    c.tag_bind(item, "<Button-1>", lambda e, d=date: self.on_click(d))
                    c.tag_bind(item, "<Enter>", lambda e: c.configure(cursor="hand2"))
                    c.tag_bind(item, "<Leave>", lambda e: c.configure(cursor=""))


# ----------------------------------------------------------------- avatar

def initials(name):
    words = [w for w in (name or "?").split() if w]
    return "".join(w[0] for w in words[:2]).upper() or "?"


def avatar_colour(name):
    return AVATAR_COLOURS[zlib.crc32((name or "").encode("utf-8")) % len(AVATAR_COLOURS)]


class Avatar(tk.Canvas):
    def __init__(self, parent, size=56):
        tk.Canvas.__init__(self, parent, width=size, height=size, highlightthickness=0,
                           bg=background(parent), bd=0)
        self.size = size

    def show(self, name):
        s = self.size
        self.delete("all")
        self.create_oval(2, 2, s - 2, s - 2, fill=avatar_colour(name), outline="")
        self.create_text(s / 2, s / 2, text=initials(name), fill="white",
                         font=ui_font(int(s / 3.2), "bold"))


# ----------------------------------------------------------------- banner

class Banner(tk.Label):
    """Big coloured message. Flashes brighter for a moment, then settles,
    then returns to the idle text after a few seconds."""

    KINDS = {
        # kind: (flash background, background, text colour)
        "success": ("#b9e4c4", "#e3f4e8", "#145c2c"),
        "warn": ("#ffe1a8", "#fff3dc", "#7a4a00"),
        "danger": ("#f8b9b9", "#fde4e4", "#9b1020"),
        "info": ("#c9daf6", "#e6eefb", "#1d4f91"),
        "idle": ("#eeeeee", "#f4f4f4", "#666666"),
    }

    def __init__(self, parent, idle_text="", **kw):
        tk.Label.__init__(self, parent, text=idle_text, padx=14, pady=10,
                          justify=tk.RIGHT if i18n.is_rtl() else tk.LEFT,
                          anchor=anchor_start(), font=ui_font(13, "bold"), **kw)
        self.idle_text = idle_text
        self._jobs = []
        self._paint("idle", 1)

    def _paint(self, kind, stage):
        colours = self.KINDS[kind]
        self.configure(bg=colours[stage], fg=colours[2])

    def show(self, text, kind="success", seconds=8):
        for job in self._jobs:
            self.after_cancel(job)
        self.configure(text=text)
        self._paint(kind, 0)
        self._jobs = [self.after(180, lambda: self._paint(kind, 1)),
                      self.after(seconds * 1000, self.reset)]

    def reset(self):
        self._jobs = []
        self.configure(text=self.idle_text)
        self._paint("idle", 1)
