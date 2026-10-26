"""AppDocStudio REST API — the API surface (third endpoint, with CLI + MCP).

Standard-library HTTP server. Local-first by design: it binds to
127.0.0.1 unless told otherwise, and it only reads project directories on
the machine it runs on — the same trust model as the CLI. It is a local
developer API, not a hosted multi-tenant service.

Endpoints:
    GET  /health           -> {"status": "ok", "version": ...}
    GET  /v1/formats       -> the standards-format profiles
    GET  /v1/roles         -> the six role packs
    POST /v1/scan          {path} -> structured scan (JSON)
    POST /v1/role-pack     {path, role, format?, doc_format?} -> one pack
    POST /v1/generate      {path, format?, doc_format?} -> all packs + SBOM

Here ``format`` is the output medium ("md" | "html") and ``doc_format``
is the standards-format profile (see formats.py).

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from .formats import FORMAT_IDS, FORMATS
from .html_render import pack_to_html
from .packs import ROLES, build_all_packs, build_pack, cyclonedx_bom
from .scanner import scan_project

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8932


def _formats_payload() -> list[dict]:
    return [{"id": p.id, "name": p.name, "authority": p.authority,
             "numbered": p.numbered, "heading_case": p.heading_case}
            for p in (FORMATS[fid] for fid in FORMAT_IDS)]


def _render(pack, project, medium: str, doc_format: str) -> str:
    return (pack.to_markdown(project, doc_format) if medium == "md"
            else pack_to_html(pack, project, doc_format))


def handle_post(path: str, payload: dict):
    """Pure request logic (unit-testable without a socket). Returns
    (status, body_dict)."""
    try:
        if path == "/v1/scan":
            project = scan_project(payload["path"])
            return 200, project.to_dict()
        if path == "/v1/role-pack":
            project = scan_project(payload["path"])
            pack = build_pack(project, payload["role"])
            return 200, {
                "role": pack.role,
                "doc_format": payload.get("doc_format", "diataxis"),
                "content": _render(pack, project, payload.get("format", "md"),
                                   payload.get("doc_format", "diataxis")),
            }
        if path == "/v1/generate":
            project = scan_project(payload["path"])
            medium = payload.get("format", "md")
            doc_format = payload.get("doc_format", "diataxis")
            packs = {pack.role: _render(pack, project, medium, doc_format)
                     for pack in build_all_packs(project)}
            return 200, {"doc_format": doc_format, "packs": packs,
                         "sbom": cyclonedx_bom(project)}
        return 404, {"error": f"Unknown endpoint: POST {path}"}
    except KeyError as exc:
        return 400, {"error": f"Missing required field: {exc.args[0]}"}
    except (ValueError, NotADirectoryError, FileNotFoundError) as exc:
        return 400, {"error": str(exc)}


class _Handler(BaseHTTPRequestHandler):
    server_version = f"AppDocStudio/{__version__}"

    def log_message(self, *args):  # keep stdout clean
        pass

    def _json(self, status: int, body) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "ok", "version": __version__})
        elif self.path == "/v1/formats":
            self._json(200, {"formats": _formats_payload()})
        elif self.path == "/v1/roles":
            self._json(200, {"roles": list(ROLES)})
        else:
            self._json(404, {"error": f"Unknown endpoint: GET {self.path}"})

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "Request body must be a JSON object"})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": "Request body must be a JSON object"})
            return
        status, body = handle_post(self.path, payload)
        self._json(status, body)


def make_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _Handler)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> int:
    server = make_server(host, port)
    print(f"AppDocStudio API listening on http://{host}:{server.server_address[1]} "
          f"(Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
