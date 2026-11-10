"""Python parser — real AST parsing via the standard-library ``ast`` module.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import ast
from pathlib import Path

from .model import ClassInfo, FunctionInfo, ModuleInfo, Param, first_summary


def _unparse(node) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _params(args: ast.arguments) -> list[Param]:
    out: list[Param] = []
    positional = list(args.posonlyargs) + list(args.args)
    defaults: list = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    for arg, default in zip(positional, defaults):
        out.append(Param(
            name=arg.arg,
            type=_unparse(arg.annotation),
            default=_unparse(default),
            optional=default is not None,
        ))
    if args.vararg:
        out.append(Param(name="*" + args.vararg.arg, type=_unparse(args.vararg.annotation)))
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        out.append(Param(
            name=arg.arg,
            type=_unparse(arg.annotation),
            default=_unparse(default),
            optional=True,
        ))
    if args.kwarg:
        out.append(Param(name="**" + args.kwarg.arg, type=_unparse(args.kwarg.annotation)))
    return out


def _function(node, kind: str = "function") -> FunctionInfo:
    doc = ast.get_docstring(node)
    return FunctionInfo(
        name=node.name,
        params=_params(node.args),
        returns=_unparse(node.returns),
        doc=doc,
        summary=first_summary(doc),
        kind=kind,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        line=getattr(node, "lineno", 0),
        decorators=[_unparse(d) for d in node.decorator_list if _unparse(d)],
    )


def _class(node: ast.ClassDef) -> ClassInfo:
    doc = ast.get_docstring(node)
    cls = ClassInfo(
        name=node.name,
        bases=[_unparse(b) for b in node.bases if _unparse(b)],
        doc=doc,
        summary=first_summary(doc),
        line=getattr(node, "lineno", 0),
    )
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cls.methods.append(_function(item, kind="method"))
        elif isinstance(item, ast.ClassDef):
            nested = _class(item)
            nested.name = f"{node.name}.{item.name}"
            cls.methods.extend(nested.methods)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            cls.properties.append(Param(name=item.target.id, type=_unparse(item.annotation)))
        elif isinstance(item, ast.Assign):
            for t in item.targets:
                if isinstance(t, ast.Name):
                    cls.properties.append(Param(name=t.id))
    return cls


def _imports(tree: ast.Module) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.append(node.module)
    return sorted(set(out))


def parse_python(source: str, rel_path: str) -> ModuleInfo:
    mod = ModuleInfo(path=rel_path, language="python", lines=source.count("\n") + 1)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        mod.parse_error = f"{exc.__class__.__name__}: {exc.msg} (line {exc.lineno})"
        return mod
    mod.doc = ast.get_docstring(tree)
    mod.summary = first_summary(mod.doc)
    mod.imports = _imports(tree)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = _function(node)
            fn.exported = not fn.name.startswith("_")
            mod.functions.append(fn)
        elif isinstance(node, ast.ClassDef):
            cls = _class(node)
            cls.exported = not cls.name.startswith("_")
            mod.classes.append(cls)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    mod.variables.append(Param(name=t.id, default=_unparse(node.value)))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            mod.variables.append(Param(name=node.target.id, type=_unparse(node.annotation)))
    return mod


def parse_python_file(path: Path, root: Path) -> ModuleInfo:
    source = path.read_text(encoding="utf-8", errors="replace")
    return parse_python(source, str(path.relative_to(root)))
