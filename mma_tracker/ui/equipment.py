import tkinter as tk
from tkinter import ttk

from ..i18n import t
from . import dialogs
from .app import Tab
from .widgets import Table, button, confirm, fmt_money, side_end, toolbar


class EquipmentTab(Tab):
    title_key = "tab_equipment"

    def build(self):
        products = ttk.LabelFrame(self, text=t("products"), padding=6)
        products.pack(fill=tk.BOTH, expand=True)
        bar = toolbar(products)
        button(bar, "sell", self.sell)
        button(bar, "add_product", self.add)
        button(bar, "edit", self.edit)
        button(bar, "delete", self.remove, side=side_end())
        self.products = Table(products, [
            ("name", "name", 260, "text"),
            ("price", "price", 110, "num"),
            ("stock", "stock", 80, "num"),
        ], height=8, on_open=lambda iid: self.edit())
        self.products.pack(fill=tk.BOTH, expand=True)

        sales = ttk.LabelFrame(self, text=t("recent_sales"), padding=6)
        sales.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        bar = toolbar(sales)
        button(bar, "undo_sale", self.undo_sale, side=side_end())
        self.sales = Table(sales, [
            ("date", "date", 100, "text"),
            ("product", "product", 200, "text"),
            ("qty", "qty", 70, "num"),
            ("total", "total", 100, "num"),
            ("member", "member", 200, "text"),
        ], height=8)
        self.sales.pack(fill=tk.BOTH, expand=True)

    def refresh(self):
        self.products.set_rows(
            (p["id"], {"name": p["name"], "price": fmt_money(p["price"]),
                       "stock": p["stock"]},
             "expired" if p["stock"] <= 0 else "")
            for p in self.store.list_products())
        self.sales.set_rows(
            (s["id"], {"date": s["on_date"], "product": s["product_name"],
                       "qty": s["qty"], "total": fmt_money(s["total"]),
                       "member": s["member_name"] or t("walk_in")}, "")
            for s in self.store.list_sales(limit=200))

    def _selected_product(self):
        iid = self.products.require_selected()
        return None if iid is None else self.store.get_product(int(iid))

    def add(self):
        self.app.run(self, dialogs.product_form, self, self.store)

    def edit(self):
        product = self._selected_product()
        if product is not None:
            self.app.run(self, dialogs.product_form, self, self.store, product)

    def remove(self):
        product = self._selected_product()
        if product is not None and confirm(self, "confirm_archive_product"):
            self.store.archive_product(product["id"])
            self.app.data_changed()

    def sell(self):
        iid = self.products.selected()
        self.app.run(self, dialogs.sell_form, self, self.store,
                     product_id=int(iid) if iid else None)

    def undo_sale(self):
        iid = self.sales.require_selected()
        if iid is not None and confirm(self, "confirm_undo_sale"):
            self.store.delete_sale(int(iid))
            self.app.data_changed()
