"""Standards-format packs + API + agent surfaces (owner extension, 2026-10-26).

Run: PYTHONPATH=src python3 -m unittest discover -s tests
"""

import json
import sys
import threading
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from appdocstudio.agent import run_task, tool_schemas
from appdocstudio.api import handle_post, make_server
from appdocstudio.formats import FORMAT_IDS, get_format, sentence_case, title_case
from appdocstudio.packs import build_pack
from appdocstudio.scanner import scan_project

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class FormatProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = scan_project(FIXTURES)

    def render(self, role, fmt):
        return build_pack(self.project, role).to_markdown(self.project, fmt)

    def test_all_profiles_render(self):
        for fid in FORMAT_IDS:
            text = self.render("developers", fid)
            self.assertIn("API reference", text, fid)

    def test_base_output_unchanged(self):
        text = self.render("users", "diataxis")
        self.assertIn("## Tutorial", text)
        self.assertNotIn("Foreword", text)

    def test_iso_numbered_clauses_and_foreword(self):
        text = self.render("users", "iso")
        self.assertIn("## Foreword", text)
        self.assertIn("## 1 Introduction", text)  # Tutorial quadrant, clause 1
        self.assertIn("### 1.1 Getting started", text)
        self.assertIn("shall", text)  # conventions note

    def test_w3c_front_matter_and_keywords(self):
        text = self.render("users", "w3c")
        self.assertIn("## Abstract", text)
        self.assertIn("## Status of This Document", text)
        self.assertIn("RFC 2119", text)
        self.assertIn("not a W3C publication", text)

    def test_en_european_foreword(self):
        text = self.render("users", "en")
        self.assertIn("## European foreword", text)
        self.assertIn("## 1 Introduction", text)

    def test_heading_cases(self):
        self.assertEqual(sentence_case("Cut a Release and Ship It"), "Cut a release and ship it")
        self.assertEqual(title_case("cut a release and ship it"), "Cut a Release and Ship It")
        google = self.render("maintainers", "google")
        self.assertIn("## How-to guide", google)
        apple = self.render("maintainers", "apple")
        self.assertIn("## How-To", apple)

    def test_unknown_format_rejected(self):
        with self.assertRaises(ValueError):
            get_format("klingon")


class ApiTests(unittest.TestCase):
    def test_handle_post_role_pack_iso(self):
        status, body = handle_post("/v1/role-pack",
                                   {"path": str(FIXTURES), "role": "users",
                                    "doc_format": "iso"})
        self.assertEqual(status, 200)
        self.assertIn("## Foreword", body["content"])

    def test_handle_post_errors(self):
        status, _ = handle_post("/v1/scan", {})
        self.assertEqual(status, 400)
        status, _ = handle_post("/v1/nope", {"path": str(FIXTURES)})
        self.assertEqual(status, 404)

    def test_http_round_trip(self):
        server = make_server("127.0.0.1", 0)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
                self.assertEqual(json.loads(r.read())["status"], "ok")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/formats", timeout=5) as r:
                formats = json.loads(r.read())["formats"]
            self.assertEqual(len(formats), len(FORMAT_IDS))
        finally:
            server.shutdown()


class AgentTests(unittest.TestCase):
    def test_schemas_cover_all_tools(self):
        names = {s["name"] for s in tool_schemas()}
        self.assertEqual(names, {"scan_project", "generate_docs", "role_pack", "list_formats"})

    def test_run_task_list_formats(self):
        result = run_task({"task": "list_formats", "arguments": {}})
        self.assertTrue(result["ok"])
        self.assertIn("ISO format", result["result"])

    def test_run_task_role_pack_w3c(self):
        result = run_task({"task": "role_pack",
                           "arguments": {"path": str(FIXTURES), "role": "ops",
                                         "doc_format": "w3c"}})
        self.assertTrue(result["ok"])
        self.assertIn("Status of This Document", result["result"])

    def test_run_task_unknown(self):
        result = run_task({"task": "explode", "arguments": {}})
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
