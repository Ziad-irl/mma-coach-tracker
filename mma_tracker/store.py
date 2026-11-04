"""Business logic on top of the SQLite database.

Money model: every amount a member owes is a row in `charges`
(subscription, equipment bought on credit, or a manual debt) and every
amount they hand over is a row in `payments`. Balance = charges - payments.
Walk-in cash sales have no member and are paid in full on the spot.
"""

import datetime

from . import db


def today():
    return datetime.date.today()


def parse_date(value):
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value).strip())


def money(value):
    return round(float(value or 0), 2)


class ValidationError(ValueError):
    """Raised for bad user input; the message is an i18n key."""


class Store(object):
    def __init__(self, path=None):
        self.path = path or db.default_db_path()
        self.conn = db.connect(self.path)

    def close(self):
        self.conn.close()

    # ---------------------------------------------------------------- settings

    def get_setting(self, key, default=None):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)",
                (key, str(value)),
            )

    # ----------------------------------------------------------------- members

    def add_member(self, name, phone="", notes=""):
        name = (name or "").strip()
        if not name:
            raise ValidationError("err_name_required")
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO members(name, phone, notes, created_on) "
                "VALUES (?, ?, ?, ?)",
                (name, phone.strip(), notes.strip(), today().isoformat()),
            )
        return cur.lastrowid

    def update_member(self, member_id, name, phone="", notes=""):
        name = (name or "").strip()
        if not name:
            raise ValidationError("err_name_required")
        with self.conn:
            self.conn.execute(
                "UPDATE members SET name = ?, phone = ?, notes = ? WHERE id = ?",
                (name, phone.strip(), notes.strip(), member_id),
            )

    def set_member_archived(self, member_id, archived):
        with self.conn:
            self.conn.execute(
                "UPDATE members SET archived = ? WHERE id = ?",
                (1 if archived else 0, member_id),
            )

    def get_member(self, member_id):
        return self.conn.execute(
            "SELECT * FROM members WHERE id = ?", (member_id,)
        ).fetchone()

    def list_members(self, search="", include_archived=False):
        """Members with their latest subscription end date and balance."""
        sql = """
            SELECT m.id, m.name, m.phone, m.archived,
                   (SELECT MAX(end_date) FROM subscriptions s
                     WHERE s.member_id = m.id) AS end_date,
                   ROUND(
                     IFNULL((SELECT SUM(amount) FROM charges c
                              WHERE c.member_id = m.id), 0)
                   - IFNULL((SELECT SUM(amount) FROM payments p
                              WHERE p.member_id = m.id), 0), 2) AS balance
              FROM members m
             WHERE 1 = 1
        """
        args = []
        if not include_archived:
            sql += " AND m.archived = 0"
        search = (search or "").strip()
        if search:
            sql += " AND (m.name LIKE ? OR m.phone LIKE ?)"
            like = "%" + search + "%"
            args += [like, like]
        sql += " ORDER BY m.name COLLATE NOCASE"
        return self.conn.execute(sql, args).fetchall()

    def member_balance(self, member_id):
        row = self.conn.execute(
            """SELECT
                 IFNULL((SELECT SUM(amount) FROM charges  WHERE member_id = ?), 0)
               - IFNULL((SELECT SUM(amount) FROM payments WHERE member_id = ?), 0)
            """,
            (member_id, member_id),
        ).fetchone()
        return money(row[0])

    def member_end_date(self, member_id):
        row = self.conn.execute(
            "SELECT MAX(end_date) FROM subscriptions WHERE member_id = ?",
            (member_id,),
        ).fetchone()
        return parse_date(row[0]) if row[0] else None

    def member_history(self, member_id):
        """Charges and payments for one member, newest first."""
        return self.conn.execute(
            """SELECT 'charge' AS type, id, on_date, description, amount
                 FROM charges WHERE member_id = ?
               UNION ALL
               SELECT 'payment' AS type, id, on_date, note AS description, amount
                 FROM payments WHERE member_id = ?
               ORDER BY on_date DESC, id DESC""",
            (member_id, member_id),
        ).fetchall()

    # ------------------------------------------------------------------- plans

    def add_plan(self, name, days, price):
        name = (name or "").strip()
        days = int(days)
        if not name:
            raise ValidationError("err_name_required")
        if days <= 0:
            raise ValidationError("err_days_positive")
        if money(price) < 0:
            raise ValidationError("err_amount_negative")
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO plans(name, days, price) VALUES (?, ?, ?)",
                (name, days, money(price)),
            )
        return cur.lastrowid

    def update_plan(self, plan_id, name, days, price):
        name = (name or "").strip()
        days = int(days)
        if not name:
            raise ValidationError("err_name_required")
        if days <= 0:
            raise ValidationError("err_days_positive")
        if money(price) < 0:
            raise ValidationError("err_amount_negative")
        with self.conn:
            self.conn.execute(
                "UPDATE plans SET name = ?, days = ?, price = ? WHERE id = ?",
                (name, days, money(price), plan_id),
            )

    def archive_plan(self, plan_id):
        with self.conn:
            self.conn.execute("UPDATE plans SET archived = 1 WHERE id = ?", (plan_id,))

    def list_plans(self):
        return self.conn.execute(
            "SELECT * FROM plans WHERE archived = 0 ORDER BY days, name"
        ).fetchall()

    def get_plan(self, plan_id):
        return self.conn.execute(
            "SELECT * FROM plans WHERE id = ?", (plan_id,)
        ).fetchone()

    # ----------------------------------------------------------- subscriptions

    def next_start_date(self, member_id):
        """Renewals continue from the current end date if still active."""
        end = self.member_end_date(member_id)
        if end is not None and end >= today():
            return end + datetime.timedelta(days=1)
        return today()

    def subscribe(self, member_id, plan_id, start_date=None, price=None,
                  paid_now=0, days=None):
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValidationError("err_pick_plan")
        start = parse_date(start_date) if start_date else self.next_start_date(member_id)
        days = int(days if days is not None else plan["days"])
        if days <= 0:
            raise ValidationError("err_days_positive")
        price = money(plan["price"] if price is None else price)
        paid_now = money(paid_now)
        if price < 0 or paid_now < 0:
            raise ValidationError("err_amount_negative")
        end = start + datetime.timedelta(days=days - 1)
        desc = "%s (%s - %s)" % (plan["name"], start.isoformat(), end.isoformat())
        with self.conn:
            charge_id = self.conn.execute(
                "INSERT INTO charges(member_id, kind, description, amount, on_date) "
                "VALUES (?, 'sub', ?, ?, ?)",
                (member_id, desc, price, today().isoformat()),
            ).lastrowid
            sub_id = self.conn.execute(
                "INSERT INTO subscriptions(member_id, plan_id, plan_name, "
                "start_date, end_date, price, charge_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (member_id, plan_id, plan["name"], start.isoformat(),
                 end.isoformat(), price, charge_id),
            ).lastrowid
            if paid_now > 0:
                self._insert_payment(member_id, paid_now, today(), plan["name"])
        return sub_id

    def list_subscriptions(self, member_id):
        return self.conn.execute(
            "SELECT * FROM subscriptions WHERE member_id = ? "
            "ORDER BY end_date DESC, id DESC",
            (member_id,),
        ).fetchall()

    def delete_subscription(self, sub_id):
        row = self.conn.execute(
            "SELECT charge_id FROM subscriptions WHERE id = ?", (sub_id,)
        ).fetchone()
        if row is None:
            return
        with self.conn:
            self.conn.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
            if row["charge_id"]:
                self.conn.execute("DELETE FROM charges WHERE id = ?", (row["charge_id"],))

    def expiring(self, within_days=7):
        """Active members whose latest subscription ends within N days,
        plus members whose subscription has already ended."""
        limit = (today() + datetime.timedelta(days=within_days)).isoformat()
        return self.conn.execute(
            """SELECT m.id, m.name, m.phone, MAX(s.end_date) AS end_date
                 FROM members m JOIN subscriptions s ON s.member_id = m.id
                WHERE m.archived = 0
                GROUP BY m.id
               HAVING MAX(s.end_date) <= ?
                ORDER BY end_date""",
            (limit,),
        ).fetchall()

    # ---------------------------------------------------------------- payments

    def _insert_payment(self, member_id, amount, on_date, note):
        return self.conn.execute(
            "INSERT INTO payments(member_id, amount, on_date, note) VALUES (?, ?, ?, ?)",
            (member_id, money(amount), parse_date(on_date).isoformat(), note.strip()),
        ).lastrowid

    def add_payment(self, member_id, amount, on_date=None, note=""):
        if money(amount) <= 0:
            raise ValidationError("err_amount_positive")
        with self.conn:
            return self._insert_payment(member_id, amount, on_date or today(), note)

    def delete_payment(self, payment_id):
        with self.conn:
            self.conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))

    def add_charge(self, member_id, amount, description, on_date=None):
        """A manual debt, e.g. 'borrowed 100' or an old balance."""
        if money(amount) <= 0:
            raise ValidationError("err_amount_positive")
        description = (description or "").strip()
        if not description:
            raise ValidationError("err_description_required")
        with self.conn:
            return self.conn.execute(
                "INSERT INTO charges(member_id, kind, description, amount, on_date) "
                "VALUES (?, 'other', ?, ?, ?)",
                (member_id, description, money(amount),
                 parse_date(on_date or today()).isoformat()),
            ).lastrowid

    def delete_charge(self, charge_id):
        """Delete a manual charge. Subscription and sale charges must be
        removed through delete_subscription / delete_sale."""
        with self.conn:
            self.conn.execute(
                "DELETE FROM charges WHERE id = ? AND kind = 'other'", (charge_id,)
            )

    def debtors(self):
        return self.conn.execute(
            """SELECT * FROM (
                 SELECT m.id, m.name, m.phone,
                        ROUND(
                          IFNULL((SELECT SUM(amount) FROM charges c
                                   WHERE c.member_id = m.id), 0)
                        - IFNULL((SELECT SUM(amount) FROM payments p
                                   WHERE p.member_id = m.id), 0), 2) AS balance
                   FROM members m)
                WHERE balance > 0
                ORDER BY balance DESC"""
        ).fetchall()

    def total_debt(self):
        row = self.conn.execute(
            "SELECT IFNULL(SUM(balance), 0) FROM ("
            "  SELECT IFNULL((SELECT SUM(amount) FROM charges c WHERE c.member_id = m.id), 0)"
            "       - IFNULL((SELECT SUM(amount) FROM payments p WHERE p.member_id = m.id), 0)"
            "         AS balance FROM members m) WHERE balance > 0"
        ).fetchone()
        return money(row[0])

    # --------------------------------------------------------- products, sales

    def add_product(self, name, price, stock=0):
        name = (name or "").strip()
        if not name:
            raise ValidationError("err_name_required")
        if money(price) < 0 or int(stock) < 0:
            raise ValidationError("err_amount_negative")
        with self.conn:
            return self.conn.execute(
                "INSERT INTO products(name, price, stock) VALUES (?, ?, ?)",
                (name, money(price), int(stock)),
            ).lastrowid

    def update_product(self, product_id, name, price, stock):
        name = (name or "").strip()
        if not name:
            raise ValidationError("err_name_required")
        if money(price) < 0 or int(stock) < 0:
            raise ValidationError("err_amount_negative")
        with self.conn:
            self.conn.execute(
                "UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?",
                (name, money(price), int(stock), product_id),
            )

    def archive_product(self, product_id):
        with self.conn:
            self.conn.execute(
                "UPDATE products SET archived = 1 WHERE id = ?", (product_id,)
            )

    def list_products(self):
        return self.conn.execute(
            "SELECT * FROM products WHERE archived = 0 ORDER BY name COLLATE NOCASE"
        ).fetchall()

    def get_product(self, product_id):
        return self.conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()

    def sell(self, product_id, qty, member_id=None, unit_price=None, paid_now=None):
        """Sell equipment. Walk-in sales (no member) are always paid in full.
        For a member, whatever is not paid now is added to their debt."""
        product = self.get_product(product_id)
        if product is None:
            raise ValidationError("err_pick_product")
        qty = int(qty)
        if qty <= 0:
            raise ValidationError("err_qty_positive")
        if qty > product["stock"]:
            raise ValidationError("err_not_enough_stock")
        unit_price = money(product["price"] if unit_price is None else unit_price)
        if unit_price < 0:
            raise ValidationError("err_amount_negative")
        total = money(unit_price * qty)
        on_date = today().isoformat()
        desc = "%s x%d" % (product["name"], qty)
        with self.conn:
            charge_id = None
            if member_id:
                charge_id = self.conn.execute(
                    "INSERT INTO charges(member_id, kind, description, amount, on_date) "
                    "VALUES (?, 'sale', ?, ?, ?)",
                    (member_id, desc, total, on_date),
                ).lastrowid
                paid = total if paid_now is None else money(paid_now)
                if paid < 0:
                    raise ValidationError("err_amount_negative")
                if paid > 0:
                    self._insert_payment(member_id, paid, on_date, desc)
            self.conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?", (qty, product_id)
            )
            return self.conn.execute(
                "INSERT INTO sales(product_id, product_name, member_id, qty, "
                "unit_price, total, on_date, charge_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (product_id, product["name"], member_id, qty, unit_price, total,
                 on_date, charge_id),
            ).lastrowid

    def delete_sale(self, sale_id):
        """Undo a sale: stock goes back, the member's charge is removed.
        Payments are kept; delete them separately if money was refunded."""
        sale = self.conn.execute(
            "SELECT * FROM sales WHERE id = ?", (sale_id,)
        ).fetchone()
        if sale is None:
            return
        with self.conn:
            self.conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (sale["qty"], sale["product_id"]),
            )
            self.conn.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            if sale["charge_id"]:
                self.conn.execute("DELETE FROM charges WHERE id = ?", (sale["charge_id"],))

    def list_sales(self, start=None, end=None, limit=500):
        sql = ("SELECT s.*, m.name AS member_name FROM sales s "
               "LEFT JOIN members m ON m.id = s.member_id WHERE 1 = 1")
        args = []
        if start:
            sql += " AND s.on_date >= ?"
            args.append(parse_date(start).isoformat())
        if end:
            sql += " AND s.on_date <= ?"
            args.append(parse_date(end).isoformat())
        sql += " ORDER BY s.on_date DESC, s.id DESC LIMIT ?"
        args.append(int(limit))
        return self.conn.execute(sql, args).fetchall()

    # ----------------------------------------------------------------- reports

    def income(self, start, end):
        """Cash actually received between two dates (inclusive)."""
        start = parse_date(start).isoformat()
        end = parse_date(end).isoformat()
        payments = self.conn.execute(
            "SELECT IFNULL(SUM(amount), 0) FROM payments WHERE on_date BETWEEN ? AND ?",
            (start, end),
        ).fetchone()[0]
        walk_in = self.conn.execute(
            "SELECT IFNULL(SUM(total), 0) FROM sales "
            "WHERE member_id IS NULL AND on_date BETWEEN ? AND ?",
            (start, end),
        ).fetchone()[0]
        return money(payments + walk_in)

    def summary(self):
        t = today()
        month_start = t.replace(day=1)
        active = self.conn.execute(
            """SELECT COUNT(*) FROM (
                 SELECT m.id FROM members m
                   JOIN subscriptions s ON s.member_id = m.id
                  WHERE m.archived = 0
                  GROUP BY m.id HAVING MAX(s.end_date) >= ?)""",
            (t.isoformat(),),
        ).fetchone()[0]
        members = self.conn.execute(
            "SELECT COUNT(*) FROM members WHERE archived = 0"
        ).fetchone()[0]
        return {
            "members": members,
            "active": active,
            "expired": members - active,
            "total_debt": self.total_debt(),
            "income_today": self.income(t, t),
            "income_month": self.income(month_start, t),
        }
