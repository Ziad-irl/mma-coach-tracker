"""SQLite connection and schema.

Everything is kept in one file so the coach can back it up by copying it.
Only SQL supported by the SQLite bundled with Python 3.8 is used
(no RETURNING, no generated columns, no STRICT tables).
"""

import os
import sqlite3
import sys

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    phone      TEXT    NOT NULL DEFAULT '',
    notes      TEXT    NOT NULL DEFAULT '',
    created_on TEXT    NOT NULL,
    archived   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS plans (
    id       INTEGER PRIMARY KEY,
    name     TEXT    NOT NULL,
    days     INTEGER NOT NULL,
    price    REAL    NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0
);

-- Everything a member owes money for. Balance = charges - payments.
CREATE TABLE IF NOT EXISTS charges (
    id          INTEGER PRIMARY KEY,
    member_id   INTEGER NOT NULL REFERENCES members(id),
    kind        TEXT    NOT NULL,          -- 'sub', 'sale' or 'other'
    description TEXT    NOT NULL,
    amount      REAL    NOT NULL,
    on_date     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id        INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id),
    amount    REAL    NOT NULL,
    on_date   TEXT    NOT NULL,
    note      TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id         INTEGER PRIMARY KEY,
    member_id  INTEGER NOT NULL REFERENCES members(id),
    plan_id    INTEGER REFERENCES plans(id),
    plan_name  TEXT    NOT NULL,
    start_date TEXT    NOT NULL,
    end_date   TEXT    NOT NULL,
    price      REAL    NOT NULL,
    charge_id  INTEGER REFERENCES charges(id)
);

CREATE TABLE IF NOT EXISTS products (
    id       INTEGER PRIMARY KEY,
    name     TEXT    NOT NULL,
    price    REAL    NOT NULL,
    stock    INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0
);

-- member_id is NULL for walk-in cash sales.
CREATE TABLE IF NOT EXISTS sales (
    id           INTEGER PRIMARY KEY,
    product_id   INTEGER NOT NULL REFERENCES products(id),
    product_name TEXT    NOT NULL,
    member_id    INTEGER REFERENCES members(id),
    qty          INTEGER NOT NULL,
    unit_price   REAL    NOT NULL,
    total        REAL    NOT NULL,
    on_date      TEXT    NOT NULL,
    charge_id    INTEGER REFERENCES charges(id)
);

CREATE INDEX IF NOT EXISTS ix_charges_member  ON charges(member_id);
CREATE INDEX IF NOT EXISTS ix_payments_member ON payments(member_id);
CREATE INDEX IF NOT EXISTS ix_payments_date   ON payments(on_date);
CREATE INDEX IF NOT EXISTS ix_subs_member_end ON subscriptions(member_id, end_date);
CREATE INDEX IF NOT EXISTS ix_sales_date      ON sales(on_date);
"""

DEFAULT_SETTINGS = {
    "language": "en",
    "currency": "EGP",
}


def app_dir():
    """Folder the app runs from (works for both source and a PyInstaller exe)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_db_path():
    return os.path.join(app_dir(), "data", "tracker.db")


def connect(path):
    if path != ":memory:":
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Safer against power cuts than the default and still fast on old disks.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    _migrate(conn)
    return conn


def _migrate(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < 1:
        with conn:
            conn.executescript(SCHEMA)
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                    (key, value),
                )
            conn.execute(
                "INSERT INTO plans(name, days, price) VALUES (?, ?, ?)",
                ("Monthly", 30, 0),
            )
            conn.execute("PRAGMA user_version = %d" % SCHEMA_VERSION)
