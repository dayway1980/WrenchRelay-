"""Static contract tests for English/Spanish native Android resources.

Does not claim an on-device or authenticated web-app localization test.
"""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app" / "src" / "main"

def strings_for(locale):
    file = APP / "res" / locale / "strings.xml"
    root = ET.parse(file).getroot()
    if root.tag != "resources":
        raise AssertionError(f"Unexpected resource root in {file}")
    values = {}
    for node in root.findall("string"):
        key = node.attrib["name"]
        if key in values:
            raise AssertionError(f"Duplicate {key} in {file}")
        values[key] = "".join(node.itertext()).strip()
    return values

class BilingualResourcesTest(unittest.TestCase):
    def test_both_locales_have_identical_nonempty_keys(self):
        en, es = strings_for("values"), strings_for("values-es")
        self.assertEqual(set(en), set(es))
        self.assertGreaterEqual(len(en), 9)
        for locale, values in (("English", en), ("Spanish", es)):
            for key, text in values.items():
                with self.subTest(locale=locale, key=key):
                    self.assertTrue(text, f"Missing {locale} text for {key}")

    def test_native_account_controls_are_translated(self):
        en, es = strings_for("values"), strings_for("values-es")
        for key in ("account_settings", "account_dialog_title", "privacy_action",
                    "deletion_action", "cancel", "microphone_fallback",
                    "file_picker_unavailable"):
            with self.subTest(key=key):
                self.assertIn(key, es)
                self.assertNotEqual(en[key], es[key])

    def test_manifest_uses_localized_app_label(self):
        ns = {"android": "http://schemas.android.com/apk/res/android"}
        root = ET.parse(APP / "AndroidManifest.xml").getroot()
        app = root.find("application")
        self.assertIsNotNone(app)
        self.assertEqual(app.attrib.get("{" + ns["android"] + "}label"), "@string/app_name")

    def test_activity_uses_native_resources_and_does_not_force_web_locale(self):
        source = (APP / "java" / "com" / "wrenchrelay" / "industrial"
                  / "MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("R.string.account_settings", source)
        self.assertIn("R.string.privacy_action", source)
        self.assertIn("R.string.deletion_action", source)
        self.assertNotIn("setDefaultLocale", source)
        self.assertNotIn('"?lang=es"', source)

if __name__ == "__main__":
    unittest.main()
