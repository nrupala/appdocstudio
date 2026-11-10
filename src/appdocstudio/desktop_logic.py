"""Desktop-app logic — everything the GUI does except draw widgets.

Kept separate from desktop.py so the behaviour is unit-testable headless:
project generation (all packs or one role pack, any standards format),
and the recent-projects list persisted as JSON in the user's config
directory.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
from pathlib import Path

from .formats import FORMAT_IDS
from .html_render import pack_to_html
from .packs import ROLES, build_all_packs, build_pack, bom_json
from .scanner import scan_project

MAX_RECENTS = 8


def config_dir() -> Path:
    """Per-user config directory for the desktop app (created on demand)."""
    import os
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / "appdocstudio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_recents(store: Path | None = None) -> list[str]:
    store = store or (config_dir() / "recents.json")
    try:
        data = json.loads(store.read_text(encoding="utf-8"))
        return [p for p in data if isinstance(p, str)][:MAX_RECENTS]
    except (OSError, ValueError):
        return []


def remember_project(project_path: str, store: Path | None = None) -> list[str]:
    store = store or (config_dir() / "recents.json")
    recents = [project_path] + [p for p in load_recents(store) if p != project_path]
    recents = recents[:MAX_RECENTS]
    store.write_text(json.dumps(recents, indent=2), encoding="utf-8")
    return recents


def generate(project_path: str, outdir: str, role: str = "all",
             doc_format: str = "diataxis", medium: str = "both") -> list[str]:
    """Generate packs for a project directory. Returns written file paths.

    role="all" writes every role pack plus the CycloneDX inventory;
    otherwise writes just the named role pack.
    """
    if role != "all" and role not in ROLES:
        raise ValueError(f"Unknown role '{role}'. Valid roles: {', '.join(ROLES)} or 'all'")
    if doc_format not in FORMAT_IDS:
        raise ValueError(f"Unknown format '{doc_format}'. Valid formats: {', '.join(FORMAT_IDS)}")
    project = scan_project(project_path)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    packs = build_all_packs(project) if role == "all" else [build_pack(project, role)]
    written: list[str] = []
    for pack in packs:
        if medium in ("md", "both"):
            p = out / f"{pack.role}.md"
            p.write_text(pack.to_markdown(project, doc_format), encoding="utf-8")
            written.append(str(p))
        if medium in ("html", "both"):
            p = out / f"{pack.role}.html"
            p.write_text(pack_to_html(pack, project, doc_format), encoding="utf-8")
            written.append(str(p))
    if role == "all":
        bom = out / "sbom.cdx.json"
        bom.write_text(bom_json(project), encoding="utf-8")
        written.append(str(bom))
    remember_project(str(Path(project_path).resolve()))
    return written


def preview(project_path: str, role: str = "users",
            doc_format: str = "diataxis") -> dict:
    """Render one role pack in memory (nothing written to disk), for the
    desktop app's preview pane. Returns {role, doc_format, markdown}."""
    if role not in ROLES:
        raise ValueError(f"Unknown role '{role}'. Valid roles: {', '.join(ROLES)}")
    if doc_format not in FORMAT_IDS:
        raise ValueError(f"Unknown format '{doc_format}'. Valid formats: {', '.join(FORMAT_IDS)}")
    project = scan_project(project_path)
    pack = build_pack(project, role)
    return {"role": pack.role, "doc_format": doc_format,
            "markdown": pack.to_markdown(project, doc_format)}


def scan_summary(project_path: str) -> dict:
    project = scan_project(project_path)
    return {
        "name": project.name,
        "files": project.total_files,
        "lines": project.total_lines,
        "modules": len(project.modules),
        "licences": [lic.spdx for lic in project.licences],
    }
