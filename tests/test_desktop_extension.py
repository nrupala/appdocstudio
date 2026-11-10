"""Desktop logic + extension statics (endpoint cells, v1.2.0).

Run: PYTHONPATH=src python3 -m unittest discover -s tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from appdocstudio import desktop_logic

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]


class DesktopLogicTests(unittest.TestCase):
    def test_generate_all_and_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = desktop_logic.generate(str(FIXTURES), tmp, role="all",
                                             doc_format="iso")
            names = {Path(p).name for p in written}
            self.assertIn("sbom.cdx.json", names)
            self.assertIn("developers.md", names)
            text = Path(tmp, "users.md").read_text(encoding="utf-8")
            self.assertIn("## Foreword", text)
            one = desktop_logic.generate(str(FIXTURES), tmp, role="ops")
            self.assertEqual([Path(p).name for p in one],
                             ["ops.md", "ops.html"])

    def test_recents_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "recents.json"
            desktop_logic.remember_project("/a/b", store)
            desktop_logic.remember_project("/c/d", store)
            desktop_logic.remember_project("/a/b", store)
            self.assertEqual(desktop_logic.load_recents(store), ["/a/b", "/c/d"])

    def test_scan_summary(self):
        s = desktop_logic.scan_summary(str(FIXTURES))
        self.assertEqual(s["files"], 2)
        self.assertGreaterEqual(s["modules"], 2)

    def test_bad_role_and_format_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                desktop_logic.generate(str(FIXTURES), tmp, role="nobody")
            with self.assertRaises(ValueError):
                desktop_logic.generate(str(FIXTURES), tmp, doc_format="klingon")


class ExtensionStaticTests(unittest.TestCase):
    def test_manifest_valid_and_loopback_only(self):
        manifest = json.loads((ROOT / "extension" / "manifest.json").read_text())
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest["host_permissions"], ["http://127.0.0.1/*"])
        popup = manifest["action"]["default_popup"]
        self.assertTrue((ROOT / "extension" / popup).exists())

    def test_popup_assets_exist_and_no_remote_endpoints(self):
        js = (ROOT / "extension" / "popup.js").read_text()
        self.assertIn("/v1/role-pack", js)
        for token in ("https://", "googleapis", "analytics"):
            self.assertNotIn(token, js)


if __name__ == "__main__":
    unittest.main()
