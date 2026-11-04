import unittest

from mma_tracker import i18n


class I18nTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_every_language_has_every_key(self):
        en = set(i18n.STRINGS["en"])
        for code, strings in i18n.STRINGS.items():
            self.assertEqual(set(strings), en, "missing/extra keys in %s" % code)

    def test_switch_and_fallback(self):
        i18n.set_language("ar")
        self.assertTrue(i18n.is_rtl())
        self.assertEqual(i18n.t("no_such_key"), "no_such_key")
        i18n.set_language("xx")
        self.assertEqual(i18n.language(), "en")


if __name__ == "__main__":
    unittest.main()
