"""Web-face tests — the single-file tool must stay alive.

Regression guard for the 2026-10-26 escaped defect: index.html shipped
with a missing closing parenthesis in a `match(...)` call, which made the
entire inline script unparseable and every button on the page inert —
while the HTML still rendered and looked fine. These tests exist so that
class can never escape twice.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

import re
import shutil
import subprocess
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


class WebFaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_all_six_role_buttons_exist(self):
        for role in ("user", "dev", "maint", "reg", "admin", "ops"):
            self.assertIn(f"genRole('{role}')", self.html)

    def test_ten_tabs_exist(self):
        for tab in ("scan", "files", "functions", "vars", "flow",
                    "apis", "roles", "version", "audit", "export"):
            self.assertIn(f"showTab('{tab}')", self.html)

    def test_inline_script_parses(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node not available — script parse check not run")
        start = self.html.index("<script>") + len("<script>")
        end = self.html.rindex("</script>")
        script = self.html[start:end]
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(script)
            tmp = fh.name
        proc = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
        Path(tmp).unlink(missing_ok=True)
        self.assertEqual(proc.returncode, 0,
                         f"inline script does not parse:\n{proc.stderr[:500]}")

    def test_licence_header_is_apache(self):
        self.assertIn("Apache License, Version 2.0", self.html[:600])
        self.assertIn("2351485 ALBERTA INC.", self.html[:600])


if __name__ == "__main__":
    unittest.main()
