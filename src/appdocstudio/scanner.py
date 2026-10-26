"""Project scanner — walks a codebase and builds a ProjectInfo.

Local-first by construction: the scan reads files on the machine it runs
on and makes no network calls.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .model import LicenceInfo, ProjectInfo
from .parser_python import parse_python_file
from .parser_js import parse_js_file

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
              "build", "out", "coverage", ".next", ".release-gate", "test-output"}
_PY_EXTS = {".py"}
_JS_EXTS = {".ts", ".tsx", ".mts", ".cts"}
_JS_PLAIN_EXTS = {".js", ".jsx", ".mjs", ".cjs"}
_SOURCE_EXTS = _PY_EXTS | _JS_EXTS | _JS_PLAIN_EXTS
_CONFIG_NAMES = {"package.json", "pyproject.toml", "tsconfig.json", "Dockerfile",
                 "docker-compose.yml", "docker-compose.yaml", ".env.example",
                 "Makefile", "wrangler.toml", "vercel.json", "netlify.toml"}

_LICENCE_MARKERS = [
    ("Apache License", "Apache-2.0"),
    ("MIT License", "MIT"),
    ("GNU AFFERO GENERAL PUBLIC LICENSE", "AGPL-3.0"),
    ("GNU GENERAL PUBLIC LICENSE", "GPL-3.0"),
    ("BSD 3-Clause", "BSD-3-Clause"),
    ("BSD 2-Clause", "BSD-2-Clause"),
    ("Mozilla Public License", "MPL-2.0"),
    ("ISC License", "ISC"),
]


def detect_spdx(text: str) -> str | None:
    head = text[:4000]
    m = re.search(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)", head)
    if m:
        return m.group(1)
    for marker, spdx in _LICENCE_MARKERS:
        if marker.lower() in head.lower():
            return spdx
    return None


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def scan_project(root: str | Path) -> ProjectInfo:
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")
    project = ProjectInfo(root=str(root), name=root.name)
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if any(part in _SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            files.append(path)
    project.total_files = len(files)

    for path in files:
        rel = str(path.relative_to(root))
        ext = path.suffix.lower()
        project.file_types[ext or "(none)"] = project.file_types.get(ext or "(none)", 0) + 1
        if path.name in _CONFIG_NAMES:
            project.config_files.append(rel)
        if rel.startswith(".github/workflows/"):
            project.ci_workflows.append(rel)
        if path.name.lower() == "readme.md":
            project.has_readme = True
        if "test" in path.name.lower() or "test" in path.parts:
            if ext in _SOURCE_EXTS:
                project.has_tests = True
        if ext in _SOURCE_EXTS:
            try:
                data = path.read_bytes()
                project.total_lines += data.count(b"\n") + 1
                sha = hashlib.sha256(data).hexdigest()
            except OSError:
                continue
            if ext in _PY_EXTS:
                module = parse_python_file(path, root)
            else:
                module = parse_js_file(path, root)
            module.sha256 = sha
            project.modules.append(module)

    # package metadata
    pkg = root / "package.json"
    if pkg.is_file():
        data = _read_json(pkg) or {}
        if data.get("name"):
            project.name = str(data["name"])
        if data.get("description"):
            project.description = str(data["description"])
        if data.get("license"):
            project.licences.append(LicenceInfo(spdx=str(data["license"]), source="package.json"))
        deps = list((data.get("dependencies") or {}).keys()) + \
            list((data.get("devDependencies") or {}).keys())
        project.dependencies.extend(sorted(set(deps)))
        project.scripts.update({str(k): str(v) for k, v in (data.get("scripts") or {}).items()})
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.M)
        if m and (root / "package.json").exists() is False:
            project.name = m.group(1)
        m = re.search(r'^\s*description\s*=\s*"([^"]+)"', text, re.M)
        if m and not project.description:
            project.description = m.group(1)
        m = re.search(r'^\s*license\s*=\s*\{?\s*text\s*=\s*"([^"]+)"', text, re.M)
        if m:
            project.licences.append(LicenceInfo(spdx=m.group(1), source="pyproject.toml"))
        deps_section = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.S)
        if deps_section:
            for dep in re.findall(r'"([^"]+)"', deps_section.group(1)):
                project.dependencies.append(re.split(r"[<>=!~;\[]", dep)[0].strip())
            project.dependencies = sorted(set(project.dependencies))

    # licence files
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md"):
        lic_path = root / name
        if lic_path.is_file():
            spdx = detect_spdx(lic_path.read_text(encoding="utf-8", errors="replace"))
            if spdx:
                project.licences.append(LicenceInfo(spdx=spdx, source=name))
            break
    # SPDX in source headers — only explicit SPDX-License-Identifier tags
    # count here. Prose mentions of a licence inside a docstring or comment
    # (e.g. documenting "the MIT License" in an essay module) must not mint
    # a licence entry; the earlier marker-based pass did exactly that.
    seen_spdx = {lic.spdx for lic in project.licences}
    for module in project.modules[:200]:
        try:
            head = (root / module.path).read_text(encoding="utf-8", errors="replace")[:600]
        except OSError:
            continue
        tag = re.search(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)", head)
        if tag and tag.group(1) not in seen_spdx:
            spdx = tag.group(1)
            project.licences.append(LicenceInfo(spdx=spdx, source=f"SPDX tag in {module.path}"))
            seen_spdx.add(spdx)

    # OpenAPI description
    for candidate in ("openapi.json", "openapi.yaml", "openapi.yml",
                      "docs/openapi.json", "api/openapi.json"):
        oa_path = root / candidate
        if oa_path.is_file():
            info: dict = {"path": candidate}
            if candidate.endswith(".json"):
                data = _read_json(oa_path) or {}
                info["title"] = (data.get("info") or {}).get("title")
                info["version"] = (data.get("info") or {}).get("version")
                info["paths"] = sorted((data.get("paths") or {}).keys())
            project.openapi = info
            break
    return project
