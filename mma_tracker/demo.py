# -*- coding: utf-8 -*-
"""Demo mode: a separate database filled with realistic sample data.

Start it with `python -m mma_tracker --demo` (or `<App>.exe --demo`). The
real data/tracker.db is never opened. Everything is generated relative to
today, so the demo always looks current. The same seed gives the same data.
"""

import datetime
import os
import random

from . import db

# Deletion order respects foreign keys (sales/subscriptions point at charges).
TABLES = ("attendance", "sales", "subscriptions", "payments", "charges",
          "products", "plans", "members")

PLANS = (("Monthly", 30, 600), ("3 Months", 90, 1600), ("Kids monthly", 30, 400))

PRODUCTS = (  # name, price, stock left after the sample sales
    ("Gloves 12oz", 850, 6), ("Gloves 16oz", 950, 3), ("Shin guards", 600, 4),
    ("Rash guard", 450, 9), ("Mouth guard", 120, 22), ("Hand wraps", 90, 2),
    ("MMA shorts", 400, 0),
)

NAMES = (
    u"Ahmed Hassan", u"Omar Khaled", u"Youssef Adel", u"Karim Nabil", u"Mostafa Samir",
    u"Hassan Ibrahim", u"Ziad Tarek", u"Mahmoud Fathy", u"Ali Mansour", u"Seif Ashraf",
    u"Amr Saeed", u"Tarek Hamdy", u"Islam Gamal", u"Mohamed Reda", u"Khaled Wael",
    u"Adham Sherif", u"Hamza Yasser", u"Nour Eldin", u"Belal Ayman", u"Marwan Essam",
    u"أحمد سمير", u"محمد علي", u"يوسف حسن", u"عمر طارق", u"مصطفى كمال",
    u"كريم عادل", u"زياد محمود", u"آدم شريف", u"حمزة وليد", u"سيف الدين",
    u"Malak Hany", u"Farida Osama",
)

# profile: (weight, how the subscription ends relative to today, visits per week)
PROFILES = (
    ("regular", 10, (8, 60), (3.0, 5.0)),     # running subscription, trains a lot
    ("casual", 6, (8, 60), (1.0, 2.5)),
    ("ending", 4, (0, 6), (2.0, 4.0)),        # renews this week
    ("expired", 4, (-20, -1), (1.5, 3.5)),    # just ran out
    ("quitter", 3, (10, 40), (2.0, 3.5)),     # paid but stopped coming
    ("lapsed", 3, (-150, -40), (1.0, 3.0)),   # left months ago
    ("new", 2, None, (0.0, 0.0)),             # never subscribed yet
)


def demo_db_path():
    return os.path.join(db.app_dir(), "data", "demo.db")


def is_empty(store):
    return store.conn.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 0


def reset(store, seed_value=7):
    """Wipe the demo database and fill it again."""
    with store.conn:
        for table in TABLES:
            store.conn.execute("DELETE FROM %s" % table)
    seed(store, seed_value)


def seed(store, seed_value=7):
    rng = random.Random(seed_value)
    today = datetime.date.today()
    now = datetime.datetime.now()
    conn = store.conn
    store.set_setting("currency", store.get_setting("currency") or "EGP")

    plans = [store.add_plan(name, days, price) for name, days, price in PLANS]
    with conn:
        conn.execute("DELETE FROM plans WHERE id NOT IN (%s)" % ",".join(map(str, plans)))

    weights = [p[1] for p in PROFILES]
    member_ids = []
    for index, name in enumerate(NAMES):
        # The first few members cover every profile; the rest are weighted.
        if index < len(PROFILES):
            profile = PROFILES[index]
        else:
            profile = rng.choices(PROFILES, weights)[0]
        member_ids.append(_seed_member(store, rng, today, now, name, profile, plans))

    _seed_sales(store, rng, today, member_ids)
    store.add_charge(member_ids[2], 200, u"Borrowed for transport", today - datetime.timedelta(days=9))
    store.add_charge(member_ids[11], 350, u"Old balance from last season",
                     today - datetime.timedelta(days=60))
    store.add_payment(member_ids[11], 150, today - datetime.timedelta(days=20), u"Part of old balance")


def _days(n):
    return datetime.timedelta(days=n)


def _seed_member(store, rng, today, now, name, profile, plans):
    kind, _weight, end_range, rate_range = profile
    phone = "01%d%08d" % (rng.choice((0, 1, 2, 5)), rng.randint(0, 99999999))
    notes = rng.choice(("", "", "", "Heavyweight", "Kids class", "Competes next month",
                        "Knee injury - go easy", "Brazilian jiu-jitsu blue belt"))
    member_id = store.add_member(name, phone, notes)
    joined = today - _days(rng.randint(30, 330))
    with store.conn:
        store.conn.execute("UPDATE members SET created_on = ? WHERE id = ?",
                           (joined.isoformat(), member_id))
    if end_range is None:
        return member_id

    # Build the subscription chain backwards from its final end date.
    plan_id = rng.choice(plans[:2]) if "Kids" not in notes else plans[2]
    plan = store.get_plan(plan_id)
    # Cap it so the latest subscription has already started.
    final_end = today + _days(min(rng.randint(*end_range), plan["days"] - 1))
    chain = []
    end = final_end
    while True:
        start = end - _days(plan["days"] - 1)
        if start < joined and chain:
            break
        chain.append(start)
        end = start - _days(1 + (rng.random() < 0.25) * rng.randint(3, 15))  # some gaps
        if len(chain) > 12:
            break
    owes_on_last = rng.random() < 0.3
    for i, start in enumerate(reversed(chain)):
        sub_id = store.subscribe(member_id, plan_id, start_date=start, paid_now=0)
        last = i == len(chain) - 1
        paid = plan["price"]
        if last and owes_on_last:
            paid = rng.choice((0, plan["price"] // 2, plan["price"] - 100))
        sub = store.conn.execute("SELECT charge_id FROM subscriptions WHERE id = ?",
                                 (sub_id,)).fetchone()
        with store.conn:
            store.conn.execute("UPDATE charges SET on_date = ? WHERE id = ?",
                               (min(start, today).isoformat(), sub["charge_id"]))
        if paid > 0:
            store.add_payment(member_id, paid, min(start, today), plan["name"])

    # Attendance: from the first subscription to when they stopped coming.
    first_day = max(min(chain), today - _days(150))
    if kind == "quitter":
        last_day = today - _days(rng.randint(16, 30))
    elif kind in ("expired", "lapsed"):
        last_day = min(today, final_end + _days(rng.randint(0, 3)))
    else:
        last_day = today
    per_week = rng.uniform(*rate_range)
    rows = []
    day = first_day
    while day <= last_day:
        chance = per_week / 6.0
        if day.weekday() == 4:  # Friday: gym mostly closed
            chance *= 0.15
        if rng.random() < chance:
            if day == today:
                if now.hour < 8 or rng.random() < 0.6:
                    day += _days(1)
                    continue
                minute = rng.randint(7 * 60, now.hour * 60 + now.minute)
            else:
                minute = rng.randint(16 * 60, 22 * 60)
            rows.append((member_id, day.isoformat(), "%02d:%02d" % divmod(minute, 60)))
        day += _days(1)
    with store.conn:
        store.conn.executemany(
            "INSERT OR IGNORE INTO attendance(member_id, on_date, checked_at) VALUES (?, ?, ?)",
            rows)
    return member_id


def _seed_sales(store, rng, today, member_ids):
    products = []
    for name, price, _left in PRODUCTS:
        products.append(store.add_product(name, price, 100))
    for _ in range(28):
        product_id = rng.choice(products)
        price = store.get_product(product_id)["price"]
        member_id = rng.choice(member_ids) if rng.random() < 0.6 else None
        qty = 1 if rng.random() < 0.8 else 2
        paid = None
        if member_id and rng.random() < 0.3:
            paid = rng.choice((0, price * qty // 2))
        sale_id = store.sell(product_id, qty, member_id=member_id, paid_now=paid)
        when = (today - _days(rng.randint(0, 120))).isoformat()
        sale = store.conn.execute("SELECT charge_id FROM sales WHERE id = ?",
                                  (sale_id,)).fetchone()
        with store.conn:
            store.conn.execute("UPDATE sales SET on_date = ? WHERE id = ?", (when, sale_id))
            if sale["charge_id"]:
                store.conn.execute("UPDATE charges SET on_date = ? WHERE id = ?",
                                   (when, sale["charge_id"]))
                if paid != 0:  # move the payment made at the till to the sale date
                    store.conn.execute(
                        "UPDATE payments SET on_date = ? WHERE id = "
                        "(SELECT MAX(id) FROM payments WHERE member_id = ?)",
                        (when, member_id))
    for (name, price, left), product_id in zip(PRODUCTS, products):
        store.update_product(product_id, name, price, left)
