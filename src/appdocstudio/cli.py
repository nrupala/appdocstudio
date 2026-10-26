"""AppDocStudio CLI — scan a project, generate documentation packs.

Usage:
    appdocstudio scan <project> [--json]
    appdocstudio generate <project> [-o OUTDIR] [--format md|html|both] [--doc-format PROFILE]
    appdocstudio role-pack <project> <role> [--format md|html] [--doc-format PROFILE]
    appdocstudio formats | serve [--port N] | agent-schema | agent

Local-first: no network calls are made, ever.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .formats import FORMAT_IDS, FORMATS
from .html_render import pack_to_html
from .packs import ROLES, build_all_packs, build_pack, bom_json
from .scanner import scan_project


def _write_packs(project, packs, outdir: Path, fmt: str,
                 doc_format: str = "diataxis") -> list[str]:
    outdir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for pack in packs:
        if fmt in ("md", "both"):
            path = outdir / f"{pack.role}.md"
            path.write_text(pack.to_markdown(project, doc_format), encoding="utf-8")
            written.append(str(path))
        if fmt in ("html", "both"):
            path = outdir / f"{pack.role}.html"
            path.write_text(pack_to_html(pack, project, doc_format), encoding="utf-8")
            written.append(str(path))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="appdocstudio",
                                     description="Generate role-based documentation from a codebase scan.")
    parser.add_argument("--version", action="version", version=f"AppDocStudio {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Scan a project and report what was found")
    p_scan.add_argument("project")
    p_scan.add_argument("--json", action="store_true", help="Emit the full scan as JSON")

    p_gen = sub.add_parser("generate", help="Generate all six role packs plus a CycloneDX inventory")
    p_gen.add_argument("project")
    p_gen.add_argument("-o", "--out", default="appdocs", help="Output directory (default: appdocs)")
    p_gen.add_argument("--format", choices=("md", "html", "both"), default="both")
    p_gen.add_argument("--doc-format", choices=FORMAT_IDS, default="diataxis",
                       help="Standards-format profile (default: diataxis)")

    p_role = sub.add_parser("role-pack", help="Generate one role pack to stdout or a file")
    p_role.add_argument("project")
    p_role.add_argument("role", choices=ROLES)
    p_role.add_argument("--format", choices=("md", "html"), default="md")
    p_role.add_argument("--doc-format", choices=FORMAT_IDS, default="diataxis",
                        help="Standards-format profile (default: diataxis)")
    p_role.add_argument("-o", "--out", help="Write to this file instead of stdout")

    sub.add_parser("formats", help="List the standards-format profiles")

    p_serve = sub.add_parser("serve", help="Run the REST API server (local-first, 127.0.0.1)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8932)

    sub.add_parser("agent-schema", help="Print the agent tool schemas (function-calling shape)")

    sub.add_parser("agent", help="Agent task protocol: one JSON task per line on stdin, "
                                 "one JSON result per line on stdout")

    args = parser.parse_args(argv)

    if args.command == "formats":
        for fid in FORMAT_IDS:
            prof = FORMATS[fid]
            print(f"{prof.id:10} {prof.name} — {prof.authority}")
        return 0

    if args.command == "serve":
        from .api import serve
        return serve(args.host, args.port)

    if args.command == "agent-schema":
        from .agent import tool_schemas
        print(json.dumps(tool_schemas(), indent=2))
        return 0

    if args.command == "agent":
        from .agent import run_stream
        for result in run_stream(sys.stdin):
            print(json.dumps(result))
        return 0

    try:
        project = scan_project(args.project)
    except (NotADirectoryError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "scan":
        if args.json:
            print(json.dumps(project.to_dict(), indent=2))
        else:
            print(f"Project: {project.name}")
            if project.description:
                print(f"Description: {project.description}")
            print(f"Files: {project.total_files}  Source lines: {project.total_lines}  "
                  f"Modules parsed: {len(project.modules)}")
            print(f"Functions/methods: {len(project.all_functions())}  "
                  f"Classes/interfaces: {sum(len(m.classes) for m in project.modules)}")
            for lic in project.licences:
                print(f"Licence: {lic.spdx} ({lic.source})")
            errors = [m for m in project.modules if m.parse_error]
            for m in errors:
                print(f"Parse error in {m.path}: {m.parse_error}")
        return 0

    if args.command == "generate":
        packs = build_all_packs(project)
        written = _write_packs(project, packs, Path(args.out), args.format, args.doc_format)
        bom_path = Path(args.out) / "sbom.cdx.json"
        bom_path.write_text(bom_json(project), encoding="utf-8")
        written.append(str(bom_path))
        for path in written:
            print(f"wrote {path}")
        return 0

    if args.command == "role-pack":
        pack = build_pack(project, args.role)
        text = (pack.to_markdown(project, args.doc_format) if args.format == "md"
                else pack_to_html(pack, project, args.doc_format))
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(text, end="")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
