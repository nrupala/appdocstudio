"""AppDocStudio MCP server — scan_project / generate_docs / role_pack / list_formats.

A stdio MCP server using only the Python standard library. Speaks
newline-delimited JSON-RPC 2.0 as per the Model Context Protocol.

Tools:
- scan_project  {path}                       -> structured scan summary (JSON text)
- generate_docs {path, format?}              -> all six role packs (Markdown/HTML text)
- role_pack     {path, role, format?}        -> one role pack

Local-first: tools only read the local filesystem path they are given.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import sys

from . import __version__
from .formats import FORMAT_IDS
from .html_render import pack_to_html
from .packs import ROLES, build_all_packs, build_pack, bom_json
from .scanner import scan_project

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "scan_project",
        "description": "Scan a local project directory (Python + TypeScript/JavaScript AST parsing) "
                       "and return the structured inventory: modules, functions, classes, licences (SPDX), "
                       "dependencies, and configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Local directory to scan"}},
            "required": ["path"],
        },
    },
    {
        "name": "generate_docs",
        "description": "Generate all six role packs (users, developers, maintainers, regulators, admins, ops) "
                       "for a local project, each structured on the Diátaxis framework, plus a CycloneDX "
                       "component inventory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "format": {"type": "string", "enum": ["md", "html"], "default": "md"},
                "doc_format": {"type": "string", "enum": list(FORMAT_IDS), "default": "diataxis",
                               "description": "Standards-format profile (Apache/Google/Microsoft/Apple/W3C/ISO/ANSI/EN/base)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "role_pack",
        "description": "Generate one role pack for a local project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "role": {"type": "string", "enum": list(ROLES)},
                "format": {"type": "string", "enum": ["md", "html"], "default": "md"},
                "doc_format": {"type": "string", "enum": list(FORMAT_IDS), "default": "diataxis",
                               "description": "Standards-format profile (Apache/Google/Microsoft/Apple/W3C/ISO/ANSI/EN/base)"},
            },
            "required": ["path", "role"],
        },
    },
    {
        "name": "list_formats",
        "description": "List the standards-format profiles a pack can be rendered in.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _text(payload: str) -> dict:
    return {"content": [{"type": "text", "text": payload}]}


def call_tool(name: str, arguments: dict) -> dict:
    if name not in {t["name"] for t in TOOLS}:
        raise ValueError(f"Unknown tool: {name}")
    if name == "list_formats":
        from .agent import list_formats
        return _text(list_formats())
    path = arguments.get("path")
    if not path:
        raise ValueError("Argument 'path' is required")
    project = scan_project(path)
    fmt = arguments.get("format", "md")
    doc_format = arguments.get("doc_format", "diataxis")
    if name == "scan_project":
        summary = {
            "name": project.name,
            "description": project.description,
            "total_files": project.total_files,
            "total_lines": project.total_lines,
            "modules": [
                {"path": m.path, "language": m.language, "lines": m.lines,
                 "functions": [f.signature() for f in m.functions],
                 "classes": [c.name for c in m.classes],
                 "parse_error": m.parse_error}
                for m in project.modules
            ],
            "licences": [{"spdx": lic.spdx, "source": lic.source} for lic in project.licences],
            "dependencies": project.dependencies,
        }
        return _text(json.dumps(summary, indent=2))
    if name == "generate_docs":
        parts = []
        for pack in build_all_packs(project):
            parts.append(pack.to_markdown(project, doc_format) if fmt == "md"
                         else pack_to_html(pack, project, doc_format))
        parts.append(bom_json(project) if fmt == "md" else "")
        return _text("\n\n---\n\n".join(part for part in parts if part))
    # role_pack
    pack = build_pack(project, arguments["role"])
    return _text(pack.to_markdown(project, doc_format) if fmt == "md"
                 else pack_to_html(pack, project, doc_format))


def handle(request: dict) -> dict | None:
    method = request.get("method")
    req_id = request.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "appdocstudio", "version": __version__},
        }}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params") or {}
        try:
            result = call_tool(params.get("name", ""), params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as exc:  # surfaced as a tool error, never a crash
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": f"error: {exc}"}], "isError": True}}
    if req_id is None:
        return None  # notification
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
