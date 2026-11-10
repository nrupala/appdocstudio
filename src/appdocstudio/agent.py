"""AppDocStudio agent surface — for orchestrators and LLM agents that do
not speak MCP.

Two parts:

- **Tool schema** (``appdocstudio agent-schema``): the studio's tools in
  the function-calling schema shape used by LLM agent frameworks. Single
  source of truth: derived from the same tool definitions the MCP server
  exposes, plus ``list_formats``.
- **Task protocol** (``appdocstudio agent``): one JSON task per run on
  stdin, one JSON result on stdout::

      {"task": "role_pack", "arguments": {"path": ".", "role": "developers",
                                          "doc_format": "iso"}}
      -> {"ok": true, "result": "<pack text>"}

Deterministic: the agent surface executes the studio's own tools; it does
not call a language model.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json

from .formats import FORMAT_IDS, FORMATS
from .mcp_server import TOOLS, call_tool

AGENT_TOOLS = [t["name"] for t in TOOLS] + ["list_formats"]


def tool_schemas() -> list[dict]:
    """Function-calling schemas for every agent-callable tool."""
    schemas = [{"name": t["name"], "description": t["description"],
                "parameters": t["inputSchema"]} for t in TOOLS]
    schemas.append({
        "name": "list_formats",
        "description": "List the standards-format profiles a pack can be rendered in "
                       "(Apache, Google, Microsoft, Apple, W3C, ISO, ANSI, EN, base).",
        "parameters": {"type": "object", "properties": {}},
    })
    return schemas


def list_formats() -> str:
    return json.dumps(
        [{"id": FORMATS[fid].id, "name": FORMATS[fid].name,
          "authority": FORMATS[fid].authority} for fid in FORMAT_IDS],
        indent=2)


def run_task(task: dict) -> dict:
    """Execute one agent task. Returns {"ok": bool, "result"|"error": ...}."""
    name = task.get("task", "")
    arguments = task.get("arguments") or {}
    try:
        if name == "list_formats":
            return {"ok": True, "result": list_formats()}
        result = call_tool(name, arguments)
        texts = [c.get("text", "") for c in result.get("content", [])]
        return {"ok": True, "result": "\n\n".join(texts)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_stream(lines) -> list[dict]:
    """Execute one task per non-empty input line; one result per line."""
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(run_task(json.loads(line)))
        except json.JSONDecodeError as exc:
            out.append({"ok": False, "error": f"Invalid JSON task: {exc}"})
    return out
