"""End-to-end tests — scanner, packs, HTML, CLI, and MCP server.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from appdocstudio.cli import main as cli_main  # noqa: E402
from appdocstudio.html_render import pack_to_html  # noqa: E402
from appdocstudio.packs import QUADRANTS, ROLES, build_all_packs, build_pack, bom_json  # noqa: E402
from appdocstudio.scanner import scan_project  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def make_project(tmp: str) -> Path:
    proj = Path(tmp) / "demo"
    proj.mkdir()
    (proj / "billing.ts").write_text((FIXTURES / "sample.ts").read_text())
    (proj / "greeter.py").write_text((FIXTURES / "sample.py").read_text())
    (proj / "LICENSE").write_text("MIT License\n\nCopyright (c) 2026 Example\n")
    (proj / "package.json").write_text(json.dumps({
        "name": "demo", "description": "Demo project", "license": "MIT",
        "dependencies": {"left-pad": "1.0.0"},
        "scripts": {"test": "node --test"},
    }))
    (proj / "openapi.json").write_text(json.dumps({
        "openapi": "3.1.0", "info": {"title": "Demo API", "version": "1.0"},
        "paths": {"/invoices": {}, "/health": {}},
    }))
    return proj


class ScanAndPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = make_project(self.tmp.name)
        self.project = scan_project(self.proj)

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_counts_and_licences(self):
        self.assertEqual(self.project.name, "demo")
        self.assertEqual(len(self.project.modules), 2)
        spdx = {lic.spdx for lic in self.project.licences}
        self.assertIn("MIT", spdx)
        self.assertTrue(all(m.sha256 for m in self.project.modules))
        self.assertEqual(self.project.openapi["title"], "Demo API")

    def test_all_six_packs_have_diataxis_quadrants(self):
        packs = build_all_packs(self.project)
        self.assertEqual([p.role for p in packs], list(ROLES))
        for pack in packs:
            md = pack.to_markdown(self.project)
            for quadrant in QUADRANTS:
                self.assertIn(f"## {quadrant}", md, f"{pack.role} missing {quadrant}")

    def test_developer_pack_has_api_reference(self):
        md = build_pack(self.project, "developers").to_markdown(self.project)
        self.assertIn("formatMoney", md)
        self.assertIn("greet", md)
        self.assertIn("/invoices", md)

    def test_regulator_pack_is_honest_and_has_hashes(self):
        md = build_pack(self.project, "regulators").to_markdown(self.project)
        self.assertIn("does **not** certify", md)
        self.assertIn("SHA-256", md)
        self.assertIn("MIT", md)

    def test_bom_is_cyclonedx(self):
        bom = json.loads(bom_json(self.project))
        self.assertEqual(bom["bomFormat"], "CycloneDX")
        self.assertEqual(bom["metadata"]["component"]["name"], "demo")

    def test_html_is_wcag_conscious_and_has_jsonld(self):
        pack = build_pack(self.project, "users")
        doc = pack_to_html(pack, self.project)
        self.assertIn('lang="en"', doc)
        self.assertIn("skip-link", doc)
        self.assertIn('<main id="main">', doc)
        self.assertIn("application/ld+json", doc)
        self.assertIn("TechArticle", doc)
        self.assertIn('scope="col"', doc)


class CliTests(unittest.TestCase):
    def test_cli_generate_and_role_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = make_project(tmp)
            out = Path(tmp) / "out"
            self.assertEqual(cli_main(["generate", str(proj), "-o", str(out)]), 0)
            for role in ROLES:
                self.assertTrue((out / f"{role}.md").exists(), role)
                self.assertTrue((out / f"{role}.html").exists(), role)
            self.assertTrue((out / "sbom.cdx.json").exists())
            self.assertEqual(cli_main(["scan", str(proj)]), 0)
            self.assertEqual(cli_main(["role-pack", str(proj), "ops",
                                       "-o", str(Path(tmp) / "ops.md")]), 0)

    def test_cli_missing_dir_errors_cleanly(self):
        self.assertEqual(cli_main(["scan", "/nonexistent/path/xyz"]), 2)


class McpTests(unittest.TestCase):
    def test_mcp_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = make_project(tmp)
            proc = subprocess.Popen(
                [sys.executable, "-m", "appdocstudio.mcp_server"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
            )
            assert proc.stdin and proc.stdout

            def call(payload: dict) -> dict:
                proc.stdin.write(json.dumps(payload) + "\n")
                proc.stdin.flush()
                return json.loads(proc.stdout.readline())

            init = call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            self.assertEqual(init["result"]["serverInfo"]["name"], "appdocstudio")
            tools = call({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            names = {t["name"] for t in tools["result"]["tools"]}
            self.assertEqual(names, {"scan_project", "generate_docs", "role_pack", "list_formats"})
            scan = call({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                         "params": {"name": "scan_project", "arguments": {"path": str(proj)}}})
            summary = json.loads(scan["result"]["content"][0]["text"])
            self.assertEqual(summary["name"], "demo")
            self.assertEqual(len(summary["modules"]), 2)
            pack = call({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                         "params": {"name": "role_pack",
                                    "arguments": {"path": str(proj), "role": "regulators"}}})
            self.assertIn("does **not** certify", pack["result"]["content"][0]["text"])
            bad = call({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                        "params": {"name": "scan_project", "arguments": {"path": "/nope/xyz"}}})
            self.assertTrue(bad["result"]["isError"])
            proc.stdin.close()
            proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()


class SpdxProseTrapTests(unittest.TestCase):
    def test_prose_licence_mention_is_not_a_licence(self):
        # Regression (independent tester, 2026-10-26): a module whose
        # docstring merely discusses "the MIT License" in prose must not
        # mint a licence entry for the project.
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "essay"
            proj.mkdir()
            (proj / "essay.py").write_text(
                '"""On the history of the MIT License and other licences."""\n\n'
                "def discuss() -> None:\n    pass\n")
            project = scan_project(proj)
            self.assertEqual(project.licences, [])
