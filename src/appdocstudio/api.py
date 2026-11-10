"""AppDocStudio REST API — the API surface (third endpoint, with CLI + MCP).

Standard-library HTTP server. Local-first by design: it binds to
127.0.0.1 unless told otherwise, and it only reads project directories on
the machine it runs on — the same trust model as the CLI. It is a local
developer API, not a hosted multi-tenant service.

Endpoints:
    GET  /               -> index: version + endpoint list
    GET  /health         -> {"status": "ok", "version": ...}
    GET  /openapi.json   -> the OpenAPI 3.1 description of this API
    GET  /v1/formats     -> the standards-format profiles
    GET  /v1/roles       -> the six role packs
    POST /v1/scan        {path} -> structured scan (JSON)
    POST /v1/role-pack   {path, role, format?, doc_format?} -> one pack
    POST /v1/generate    {path, format?, doc_format?} -> all packs + SBOM

Here ``format`` is the output medium ("md" | "html") and ``doc_format``
is the standards-format profile (see formats.py).

Access control: by default (loopback, no token) the API is open, like
the CLI. Start it with a token — ``appdocstudio serve --token …`` or
the APPDOCSTUDIO_API_TOKEN environment variable — and every /v1/*
request must carry ``Authorization: Bearer <token>``. /health and
/openapi.json stay open (liveness + documentation). Set a token before
binding the server to anything beyond loopback.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from . import __version__
from .formats import FORMAT_IDS, FORMATS
from .html_render import pack_to_html
from .packs import ROLES, build_all_packs, build_pack, cyclonedx_bom
from .scanner import scan_project

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8932
TOKEN_ENV = "APPDOCSTUDIO_API_TOKEN"

ENDPOINTS = [
    "GET /", "GET /health", "GET /openapi.json", "GET /v1/formats",
    "GET /v1/roles", "POST /v1/scan", "POST /v1/role-pack",
    "POST /v1/generate",
]


def _formats_payload() -> list[dict]:
    return [{"id": p.id, "name": p.name, "authority": p.authority,
             "numbered": p.numbered, "heading_case": p.heading_case}
            for p in (FORMATS[fid] for fid in FORMAT_IDS)]


def openapi_spec() -> dict:
    """The OpenAPI 3.1 description of this API, built from the live
    version and route table so it cannot drift from the server."""
    def op(summary, body_schema=None):
        operation = {"summary": summary,
                     "responses": {"200": {"description": "OK"}}}
        if body_schema is not None:
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": body_schema}}}
        return operation

    path_schema = {"type": "object", "required": ["path"],
                   "properties": {"path": {"type": "string"}}}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "AppDocStudio API",
            "version": __version__,
            "description": ("Local-first documentation studio API. "
                            "/v1/* endpoints require a bearer token when "
                            "the server is started with one."),
            "license": {"name": "Apache-2.0"},
        },
        "servers": [{"url": f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"}],
        "components": {"securitySchemes": {"bearerAuth": {
            "type": "http", "scheme": "bearer"}}},
        "paths": {
            "/": {"get": op("Index: version and endpoint list")},
            "/health": {"get": op("Liveness")},
            "/openapi.json": {"get": op("This OpenAPI description")},
            "/v1/formats": {"get": op("Standards-format profiles")},
            "/v1/roles": {"get": op("The six role packs")},
            "/v1/scan": {"post": op("Structured scan of a project directory",
                                    path_schema)},
            "/v1/role-pack": {"post": op("One role pack for a project", {
                "type": "object", "required": ["path", "role"],
                "properties": {
                    "path": {"type": "string"},
                    "role": {"type": "string", "enum": list(ROLES)},
                    "format": {"type": "string", "enum": ["md", "html"]},
                    "doc_format": {"type": "string",
                                   "enum": list(FORMAT_IDS)},
                }})},
            "/v1/generate": {"post": op("All role packs + CycloneDX SBOM", {
                "type": "object", "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "format": {"type": "string", "enum": ["md", "html"]},
                    "doc_format": {"type": "string",
                                   "enum": list(FORMAT_IDS)},
                }})},
        },
    }


def _render(pack, project, medium: str, doc_format: str) -> str:
    return (pack.to_markdown(project, doc_format) if medium == "md"
            else pack_to_html(pack, project, doc_format))


def handle_get(path: str, authorized: bool = True):
    """Pure GET logic (unit-testable without a socket). Returns
    (status, body_dict)."""
    if path == "/":
        return 200, {"name": "AppDocStudio API", "version": __version__,
                     "endpoints": ENDPOINTS, "openapi": "/openapi.json"}
    if path == "/health":
        return 200, {"status": "ok", "version": __version__}
    if path == "/openapi.json":
        return 200, openapi_spec()
    if path.startswith("/v1/") and not authorized:
        return 401, {"error": "Unauthorized: this server requires a bearer token"}
    if path == "/v1/formats":
        return 200, {"formats": _formats_payload()}
    if path == "/v1/roles":
        return 200, {"roles": list(ROLES)}
    return 404, {"error": f"Unknown endpoint: GET {path}"}


def handle_post(path: str, payload: dict, authorized: bool = True):
    """Pure POST logic (unit-testable without a socket). Returns
    (status, body_dict)."""
    if path.startswith("/v1/") and not authorized:
        return 401, {"error": "Unauthorized: this server requires a bearer token"}
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

    def _authorized(self) -> bool:
        token = getattr(self.server, "api_token", None)
        if not token:
            return True
        header = self.headers.get("Authorization") or ""
        return hmac.compare_digest(header, f"Bearer {token}")

    def _json(self, status: int, body) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        status, body = handle_get(urlsplit(self.path).path, self._authorized())
        self._json(status, body)

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
        status, body = handle_post(urlsplit(self.path).path, payload,
                                   self._authorized())
        self._json(status, body)


def make_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                token: str | None = None) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), _Handler)
    server.api_token = token if token is not None else os.environ.get(TOKEN_ENV)
    return server


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
          token: str | None = None) -> int:
    server = make_server(host, port, token)
    auth = "bearer-token auth ON" if server.api_token else "no token (loopback trust)"
    print(f"AppDocStudio API listening on http://{host}:{server.server_address[1]} "
          f"({auth}; Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
