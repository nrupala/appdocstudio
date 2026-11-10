"""v1.3.0 — API self-description + token auth; desktop preview.

Run: PYTHONPATH=src python3 -m unittest discover -s tests
"""

import json
import sys
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from appdocstudio import __version__, api, desktop_logic

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ApiSurfaceTests(unittest.TestCase):
    def test_index_and_health(self):
        status, body = api.handle_get("/")
        self.assertEqual(status, 200)
        self.assertEqual(body["version"], __version__)
        self.assertIn("POST /v1/generate", body["endpoints"])
        self.assertEqual(api.handle_get("/health")[1]["status"], "ok")

    def test_openapi_spec_is_live_shaped(self):
        status, spec = api.handle_get("/openapi.json")
        self.assertEqual(status, 200)
        self.assertTrue(spec["openapi"].startswith("3."))
        self.assertEqual(spec["info"]["version"], __version__)
        for path in ("/v1/scan", "/v1/role-pack", "/v1/generate",
                     "/v1/formats", "/v1/roles"):
            self.assertIn(path, spec["paths"])
        roles = (spec["paths"]["/v1/role-pack"]["post"]["requestBody"]
                 ["content"]["application/json"]["schema"]
                 ["properties"]["role"]["enum"])
        self.assertIn("regulators", roles)

    def test_token_gate(self):
        self.assertEqual(api.handle_get("/v1/roles", authorized=False)[0], 401)
        self.assertEqual(api.handle_get("/v1/formats", authorized=False)[0], 401)
        self.assertEqual(
            api.handle_post("/v1/scan", {"path": str(FIXTURES)},
                            authorized=False)[0], 401)
        # Liveness and the spec stay open; authorized calls work.
        self.assertEqual(api.handle_get("/health", authorized=False)[0], 200)
        self.assertEqual(api.handle_get("/openapi.json", authorized=False)[0], 200)
        status, body = api.handle_post("/v1/scan", {"path": str(FIXTURES)},
                                       authorized=True)
        self.assertEqual(status, 200)
        self.assertEqual(body["total_files"], 2)

    def test_unknown_and_queryless(self):
        self.assertEqual(api.handle_get("/nope")[0], 404)
        self.assertEqual(api.handle_post("/v1/nope", {})[0], 404)


class ApiSocketTests(unittest.TestCase):
    def test_live_server_with_token(self):
        server = api.make_server("127.0.0.1", 0, token="s3cret")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{port}"
            with urllib.request.urlopen(base + "/health", timeout=5) as resp:
                self.assertEqual(json.loads(resp.read())["status"], "ok")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(base + "/v1/roles", timeout=5)
            self.assertEqual(ctx.exception.code, 401)
            req = urllib.request.Request(
                base + "/v1/roles",
                headers={"Authorization": "Bearer s3cret"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertIn("regulators", json.loads(resp.read())["roles"])
            with urllib.request.urlopen(base + "/openapi.json", timeout=5) as resp:
                self.assertEqual(json.loads(resp.read())["info"]["version"],
                                 __version__)
        finally:
            server.shutdown()


class DesktopPreviewTests(unittest.TestCase):
    def test_preview_renders_one_pack(self):
        result = desktop_logic.preview(str(FIXTURES), role="ops",
                                       doc_format="iso")
        self.assertEqual(result["role"], "ops")
        self.assertIn("## Foreword", result["markdown"])

    def test_preview_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            desktop_logic.preview(str(FIXTURES), role="all")
        with self.assertRaises(ValueError):
            desktop_logic.preview(str(FIXTURES), role="nobody")
        with self.assertRaises(ValueError):
            desktop_logic.preview(str(FIXTURES), doc_format="klingon")


if __name__ == "__main__":
    unittest.main()
