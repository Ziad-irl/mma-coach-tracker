# -*- coding: utf-8 -*-
import datetime
import os
import shutil
import tempfile
import unittest
import zipfile
from unittest import mock
from xml.etree import ElementTree

from mma_tracker import export, i18n, store as store_mod
from mma_tracker.store import Store
from mma_tracker.xlsx import column_letter, write_xlsx

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_sheet(path, number):
    """Return the sheet as a list of rows of cell text."""
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("xl/worksheets/sheet%d.xml" % number))
    rows = []
    for row in root.iter("{%s}row" % NS["m"]):
        cells = []
        for c in row.findall("m:c", NS):
            v = c.find("m:v", NS)
            cells.append(v.text if v is not None else "".join(c.itertext()))
        rows.append(cells)
    return rows


class XlsxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_column_letters(self):
        self.assertEqual([column_letter(i) for i in (0, 25, 26, 701, 702)],
                         ["A", "Z", "AA", "ZZ", "AAA"])

    def test_writes_valid_workbook(self):
        path = os.path.join(self.tmp, "out.xlsx")
        write_xlsx(path, [
            ("A/B:C", [("Name", "text", 20), ("Owes", "money", 10)],
             [(u"عمر <&>", 150.5), ("Ali", None)]),
            ("a/b:c", [("x", "int", 5)], [(3,)]),
        ], rtl=True)
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():  # every part must be well-formed XML
                ElementTree.fromstring(z.read(name))
            workbook = z.read("xl/workbook.xml").decode("utf-8")
            sheet1 = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn('name="A B C"', workbook)
        self.assertIn('name="a b c (2)"', workbook)  # names are made unique
        self.assertIn('rightToLeft="1"', sheet1)
        self.assertEqual(read_sheet(path, 1),
                         [["Name", "Owes"], [u"عمر <&>", "150.5"], ["Ali"]])


class ExportTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(store_mod, "today",
                                    return_value=datetime.date(2026, 3, 10))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.s = Store(":memory:")
        self.addCleanup(self.s.close)
        plan = self.s.list_plans()[0]["id"]
        self.s.update_plan(plan, "Monthly", 30, 500)
        ali = self.s.add_member("Ali", "0100")
        self.s.subscribe(ali, plan, paid_now=200)
        gloves = self.s.add_product("Gloves", 800, 3)
        self.s.sell(gloves, 1)

    def tearDown(self):
        i18n.set_language("en")

    def test_export_all_sheets(self):
        path = export.export_all(self.s, os.path.join(self.tmp, "all.xlsx"))
        members = read_sheet(path, 1)
        self.assertEqual(members[0][0], "Name")
        self.assertEqual(members[1][:2], ["Ali", "0100"])
        self.assertIn("Active - 29 days left", members[1])
        self.assertEqual(read_sheet(path, 2)[1], ["Ali", "0100", "300.0"])
        self.assertEqual(read_sheet(path, 6)[1][-1], "(Walk-in customer, cash)")

    def test_arabic_headers(self):
        i18n.set_language("ar")
        path = export.export_all(self.s, os.path.join(self.tmp, "ar.xlsx"))
        self.assertEqual(read_sheet(path, 1)[0][0], u"الاسم")


if __name__ == "__main__":
    unittest.main()
