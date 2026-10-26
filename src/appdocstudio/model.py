"""Shared data model for AppDocStudio scan results.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Param:
    name: str
    type: Optional[str] = None
    default: Optional[str] = None
    optional: bool = False

    def signature(self) -> str:
        out = self.name
        if self.optional and self.default is None:
            out += "?"
        if self.type:
            out += f": {self.type}"
        if self.default is not None:
            out += f" = {self.default}"
        return out


@dataclass
class FunctionInfo:
    name: str
    params: list[Param] = field(default_factory=list)
    returns: Optional[str] = None
    doc: Optional[str] = None
    summary: Optional[str] = None
    kind: str = "function"  # function | method | arrow | constructor | getter | setter
    is_async: bool = False
    is_static: bool = False
    exported: bool = False
    line: int = 0
    decorators: list[str] = field(default_factory=list)

    def signature(self) -> str:
        prefix = ""
        if self.is_static:
            prefix += "static "
        if self.is_async:
            prefix += "async "
        params = ", ".join(p.signature() for p in self.params)
        out = f"{prefix}{self.name}({params})"
        if self.returns:
            out += f" -> {self.returns}"
        return out


@dataclass
class ClassInfo:
    name: str
    kind: str = "class"  # class | interface | enum | type
    bases: list[str] = field(default_factory=list)
    doc: Optional[str] = None
    summary: Optional[str] = None
    methods: list[FunctionInfo] = field(default_factory=list)
    properties: list[Param] = field(default_factory=list)
    exported: bool = False
    line: int = 0


@dataclass
class ModuleInfo:
    path: str  # project-relative path
    language: str  # python | typescript | javascript
    lines: int = 0
    doc: Optional[str] = None
    summary: Optional[str] = None
    imports: list[str] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    variables: list[Param] = field(default_factory=list)
    type_aliases: list[str] = field(default_factory=list)
    parse_error: Optional[str] = None
    sha256: Optional[str] = None


@dataclass
class LicenceInfo:
    spdx: str
    source: str  # where the identifier came from


@dataclass
class ProjectInfo:
    root: str
    name: str
    description: Optional[str] = None
    total_files: int = 0
    total_lines: int = 0
    file_types: dict[str, int] = field(default_factory=dict)
    modules: list[ModuleInfo] = field(default_factory=list)
    licences: list[LicenceInfo] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    scripts: dict[str, str] = field(default_factory=dict)
    config_files: list[str] = field(default_factory=list)
    ci_workflows: list[str] = field(default_factory=list)
    openapi: Optional[dict[str, Any]] = None  # {path, title, paths:[...]}
    has_readme: bool = False
    has_tests: bool = False

    def all_functions(self) -> list[tuple[ModuleInfo, FunctionInfo]]:
        out = []
        for m in self.modules:
            for f in m.functions:
                out.append((m, f))
            for c in m.classes:
                for f in c.methods:
                    out.append((m, f))
        return out

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def first_summary(doc: Optional[str]) -> Optional[str]:
    """First non-empty line of a docstring/comment, with JSDoc tags stripped."""
    if not doc:
        return None
    for line in doc.strip().splitlines():
        line = line.strip().lstrip("*").strip()
        if line and not line.startswith("@"):
            return line
    return None
