import os
import shutil
import sqlite3
import tempfile
import unittest

from mma_tracker import backup
from mma_tracker.store import Store


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.s = Store(os.path.join(self.tmp, "tracker.db"))
        self.addCleanup(self.s.close)
        self.s.add_member("Ali")

    def test_daily_backup_copies_data_and_prunes(self):
        folder = backup.backups_dir(self.s)
        os.makedirs(folder)
        for i in range(3):
            open(os.path.join(folder, "tracker-2000010%d.db" % i), "w").close()
        path = backup.daily_backup(self.s, keep=2)
        conn = sqlite3.connect(path)
        self.assertEqual(conn.execute("SELECT name FROM members").fetchone()[0], "Ali")
        conn.close()
        self.assertEqual(len(os.listdir(folder)), 2)
        self.assertIn(os.path.basename(path), os.listdir(folder))


if __name__ == "__main__":
    unittest.main()
