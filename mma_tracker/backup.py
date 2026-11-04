"""Database backups. Uses SQLite's online backup API, so it is safe to run
while the app has the database open."""

import datetime
import os
import sqlite3


def backup_to(store, dest_path):
    dest = sqlite3.connect(dest_path)
    try:
        store.conn.backup(dest)
    finally:
        dest.close()
    return dest_path


def backups_dir(store):
    return os.path.join(os.path.dirname(os.path.abspath(store.path)), "backups")


def daily_backup(store, keep=30):
    """Make at most one backup per day and keep the newest `keep` files."""
    if store.path == ":memory:":
        return None
    folder = backups_dir(store)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    name = "tracker-%s.db" % datetime.date.today().strftime("%Y%m%d")
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        backup_to(store, path)
    old = sorted(f for f in os.listdir(folder)
                 if f.startswith("tracker-") and f.endswith(".db"))
    for f in old[:-keep]:
        try:
            os.remove(os.path.join(folder, f))
        except OSError:
            pass
    return path
