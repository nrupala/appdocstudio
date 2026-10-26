"""TypeScript/JavaScript parser — a real token-level parser, not regexes.

A hand-written lexer produces a token stream (identifiers, keywords,
strings, template literals, numbers, punctuation, and comments — JSDoc
blocks are preserved). A recursive-descent parser then walks the token
stream and builds a declaration AST for the constructs documentation is
generated from:

- ``import`` / ``export`` statements
- function declarations and arrow functions assigned to variables
- classes (methods, getters/setters, properties, static members)
- interfaces, type aliases, and enums (TypeScript)
- JSDoc/TSDoc comments attached to the declaration that follows them

Expression bodies are consumed with balanced-delimiter tracking over the
token stream, which is what makes this a parser: nesting, strings, and
comments can never produce phantom declarations the way line regexes do.
The grammar covered is the declaration grammar; arbitrary expression
statements between declarations are skipped token by token.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .model import ClassInfo, FunctionInfo, ModuleInfo, Param, first_summary


# --------------------------------------------------------------------------
# Lexer
# --------------------------------------------------------------------------

@dataclass
class Token:
    kind: str  # ident | string | number | punct | comment | doc
    value: str
    line: int
    doc: str | None = None  # cleaned JSDoc attached to a code token


_PUNCT3 = ("...", "===", "!==", "**=", "<<=", ">>=", ">>>", "&&=", "||=", "??=")
_PUNCT2 = ("=>", "==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=",
           "*=", "/=", "%=", "**", "<<", ">>", "?.", "??", "::")


def lex(source: str) -> list[Token]:
    tokens: list[Token] = []
    i, n, line = 0, len(source), 1
    while i < n:
        ch = source[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch in " \t\r":
            i += 1
            continue
        # comments
        if source.startswith("//", i):
            j = source.find("\n", i)
            j = n if j < 0 else j
            tokens.append(Token("comment", source[i:j], line))
            i = j
            continue
        if source.startswith("/*", i):
            j = source.find("*/", i + 2)
            j = n - 2 if j < 0 else j
            text = source[i:j + 2]
            kind = "doc" if text.startswith("/**") and not text.startswith("/***") else "comment"
            tokens.append(Token(kind, text, line))
            line += text.count("\n")
            i = j + 2
            continue
        # strings and template literals
        if ch in "\"'`":
            quote = ch
            j = i + 1
            while j < n:
                cj = source[j]
                if cj == "\\":
                    j += 2
                    continue
                if quote == "`" and source.startswith("${", j):
                    # consume the interpolation with brace balance
                    depth = 1
                    j += 2
                    while j < n and depth:
                        if source[j] == "{":
                            depth += 1
                        elif source[j] == "}":
                            depth -= 1
                        elif source[j] in "\"'`":
                            q2 = source[j]
                            j += 1
                            while j < n and source[j] != q2:
                                if source[j] == "\\":
                                    j += 1
                                j += 1
                        j += 1
                    continue
                if cj == quote:
                    j += 1
                    break
                if cj == "\n" and quote != "`":
                    break
                j += 1
            text = source[i:j]
            tokens.append(Token("string", text, line))
            line += text.count("\n")
            i = j
            continue
        # numbers
        if ch.isdigit():
            j = i
            while j < n and (source[j].isalnum() or source[j] in "._"):
                j += 1
            tokens.append(Token("number", source[i:j], line))
            i = j
            continue
        # identifiers / keywords
        if ch.isalpha() or ch in "_$":
            j = i
            while j < n and (source[j].isalnum() or source[j] in "_$"):
                j += 1
            tokens.append(Token("ident", source[i:j], line))
            i = j
            continue
        # punctuation (longest first)
        tri, two = source[i:i + 3], source[i:i + 2]
        if tri in _PUNCT3:
            tokens.append(Token("punct", tri, line))
            i += 3
        elif two in _PUNCT2:
            tokens.append(Token("punct", two, line))
            i += 2
        else:
            tokens.append(Token("punct", ch, line))
            i += 1
    return tokens


def _clean_doc(raw: str) -> str:
    """Strip the /** */ frame and leading asterisks from a JSDoc block."""
    body = raw[3:-2] if raw.startswith("/**") else raw[2:-2]
    lines = []
    for line in body.splitlines():
        lines.append(line.strip().lstrip("*").strip())
    return "\n".join(lines).strip()


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

_MODIFIERS = {"public", "private", "protected", "readonly", "static",
              "abstract", "declare", "override", "accessor"}
_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = set(_OPEN.values())


class Parser:
    def __init__(self, tokens: list[Token]):
        # Doc comments are attached to the code token that follows them,
        # so consuming a declaration never has to skip over comments.
        self.toks: list[Token] = []
        pending: str | None = None
        for tok in tokens:
            if tok.kind == "comment":
                continue
            if tok.kind == "doc":
                pending = _clean_doc(tok.value)
                continue
            self.toks.append(Token(tok.kind, tok.value, tok.line, pending))
            pending = None
        self.pos = 0

    # -- stream helpers ----------------------------------------------------
    def peek(self, off: int = 0) -> Token | None:
        idx = self.pos + off
        return self.toks[idx] if 0 <= idx < len(self.toks) else None

    def next(self) -> Token | None:
        tok = self.peek()
        if tok is not None:
            self.pos += 1
        return tok

    def at(self, value: str) -> bool:
        tok = self.peek()
        return tok is not None and tok.value == value

    def eat(self, value: str) -> bool:
        if self.at(value):
            self.next()
            return True
        return False

    def take_doc(self) -> str | None:
        tok = self.peek()
        if tok is not None and tok.doc:
            doc, tok.doc = tok.doc, None
            return doc
        return None

    def collect_until(self, *stops: str) -> list[Token]:
        """Collect tokens until a stop token at nesting depth 0."""
        out: list[Token] = []
        depth = 0
        while True:
            tok = self.peek()
            if tok is None:
                break
            if depth == 0 and tok.value in stops:
                break
            if tok.value in _OPEN:
                depth += 1
            elif tok.value in _CLOSE:
                if depth == 0:
                    break
                depth -= 1
            out.append(self.next())
        return out

    def skip_balanced(self) -> None:
        """Consume one balanced delimiter group starting at the cursor."""
        tok = self.peek()
        if tok is None or tok.value not in _OPEN:
            return
        depth = 0
        while True:
            t = self.next()
            if t is None:
                return
            if t.value in _OPEN:
                depth += 1
            elif t.value in _CLOSE:
                depth -= 1
                if depth == 0:
                    return

    def skip_statement(self) -> None:
        depth = 0
        while True:
            tok = self.peek()
            if tok is None:
                return
            if depth == 0 and tok.value == ";":
                self.next()
                return
            if depth == 0 and tok.value == "}":
                return
            if tok.value in _OPEN:
                depth += 1
            elif tok.value in _CLOSE:
                depth -= 1
            self.next()

    # -- fragments ---------------------------------------------------------
    def parse_params(self) -> list[Param]:
        """Cursor is at '('. Consume it and parse the parameter list."""
        inner: list[Token] = []
        depth = 0
        self.next()  # '('
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok.value == "(" or tok.value in _OPEN:
                depth += 1
            if tok.value == ")":
                if depth == 0:
                    self.next()
                    break
                depth -= 1
            inner.append(self.next())
        # split on top-level commas
        groups: list[list[Token]] = [[]]
        depth = 0
        for tok in inner:
            if tok.value in _OPEN:
                depth += 1
            elif tok.value in _CLOSE:
                depth -= 1
            if tok.value == "," and depth == 0:
                groups.append([])
            else:
                groups[-1].append(tok)
        params: list[Param] = []
        for group in groups:
            if not group:
                continue
            params.append(self._one_param(group))
        return params

    @staticmethod
    def _one_param(group: list[Token]) -> Param:
        vals = [t.value for t in group]
        # strip leading modifiers / rest
        rest = False
        while vals and vals[0] in _MODIFIERS | {"..."}:
            if vals[0] == "...":
                rest = True
            vals.pop(0)
        if not vals:
            return Param(name="_")
        # destructuring pattern
        if vals[0] in ("{", "["):
            name = "".join(vals)
            return Param(name=("..." if rest else "") + name)
        name = vals[0]
        if rest:
            name = "..." + name
        optional = False
        type_parts: list[str] = []
        default_parts: list[str] = []
        mode = None
        depth = 0
        for v in vals[1:]:
            if v in _OPEN:
                depth += 1
            elif v in _CLOSE:
                depth -= 1
            if depth == 0 and v == ":" and mode is None:
                mode = "type"
                continue
            if depth == 0 and v == "=" and mode != "default":
                mode = "default"
                continue
            if depth == 0 and v == "?" and mode is None:
                optional = True
                continue
            if mode == "type":
                type_parts.append(v)
            elif mode == "default":
                default_parts.append(v)
        join = lambda parts: " ".join(parts).replace(" ,", ",").replace("( ", "(").replace(" )", ")") or None
        return Param(name=name, type=join(type_parts), default=join(default_parts),
                     optional=optional or bool(default_parts))

    def parse_type_tail(self) -> str | None:
        """After a parameter list or name: optional ': Type' up to '{' ';' '=>'."""
        if not self.eat(":"):
            return None
        toks = self.collect_until("{", ";", "=>", "=")
        text = " ".join(t.value for t in toks).strip()
        return text or None

    # -- declarations ------------------------------------------------------
    def parse_module(self, mod: ModuleInfo) -> ModuleInfo:
        while True:
            tok = self.peek()
            if tok is None:
                break
            try:
                self.parse_top_level(mod)
            except Exception:
                # A construct outside the declaration grammar: skip one
                # token and keep going — never abort the whole module.
                self.next()
        return mod

    def parse_top_level(self, mod: ModuleInfo) -> None:
        tok = self.peek()
        if tok is None:
            return
        exported = False
        if tok.value == "import":
            self.next()
            stmt = self.collect_until(";")
            src = next((t.value for t in stmt if t.kind == "string"), None)
            if src:
                mod.imports.append(src.strip("\"'`"))
            self.eat(";")
            return
        if tok.value == "export":
            exported = True
            exp_tok = self.next()
            nxt = self.peek()
            if nxt is not None and exp_tok is not None and exp_tok.doc and not nxt.doc:
                nxt.doc = exp_tok.doc  # the doc comment belongs to the declaration
            if nxt is not None and nxt.value == "{":
                self.skip_balanced()
                self.skip_statement()
                return
            if nxt is not None and nxt.value == "default":
                self.next()
            tok = self.peek()
            if tok is None:
                return
        if tok.value == "declare":
            self.next()
            tok = self.peek()
            if tok is None:
                return
        if tok.value == "async" and self.peek(1) is not None and self.peek(1).value == "function":
            self.next()
            fn = self.parse_function(async_=True)
            if fn:
                fn.exported = exported
                mod.functions.append(fn)
            return
        if tok.value == "function":
            fn = self.parse_function()
            if fn:
                fn.exported = exported
                mod.functions.append(fn)
            return
        if tok.value == "class" or (tok.value == "abstract" and self.peek(1) is not None and self.peek(1).value == "class"):
            cls = self.parse_class()
            if cls:
                cls.exported = exported
                mod.classes.append(cls)
            return
        if tok.value == "interface":
            cls = self.parse_interface()
            if cls:
                cls.exported = exported
                mod.classes.append(cls)
            return
        if tok.value == "type":
            self.next()
            name_tok = self.next()
            if name_tok is not None:
                head = name_tok.value
                tail = self.collect_until(";")
                text = " ".join(t.value for t in tail).strip()
                if text.startswith("="):
                    text = text[1:].strip()
                mod.type_aliases.append(f"{head} = {text}".strip())
            self.eat(";")
            return
        if tok.value == "enum":
            cls = self.parse_enum()
            if cls:
                cls.exported = exported
                mod.classes.append(cls)
            return
        if tok.value in ("const", "let", "var"):
            self.parse_variable(mod, exported)
            return
        # anything else: skip the statement
        self.take_doc()
        self.skip_statement()

    def parse_function(self, async_: bool = False) -> FunctionInfo | None:
        doc = self.take_doc()
        line = self.peek().line if self.peek() else 0
        self.next()  # 'function'
        self.eat("*")
        name_tok = self.next()
        if name_tok is None or name_tok.kind != "ident":
            return None
        if self.at("<"):
            self.skip_balanced()  # type parameters
        params = self.parse_params() if self.at("(") else []
        returns = self.parse_type_tail()
        if self.at("{"):
            self.skip_balanced()
        self.eat(";")
        return FunctionInfo(name=name_tok.value, params=params, returns=returns,
                            doc=doc, summary=first_summary(doc), is_async=async_, line=line)

    def parse_class(self) -> ClassInfo | None:
        doc = self.take_doc()
        line = self.peek().line if self.peek() else 0
        self.eat("abstract")
        self.next()  # 'class'
        name_tok = self.next()
        if name_tok is None or name_tok.kind != "ident":
            return None
        cls = ClassInfo(name=name_tok.value, doc=doc, summary=first_summary(doc), line=line)
        # heritage: extends / implements up to '{'
        heritage = self.collect_until("{")
        vals = [t.value for t in heritage]
        if "extends" in vals:
            idx = vals.index("extends")
            if idx + 1 < len(vals):
                cls.bases.append(vals[idx + 1])
        if not self.at("{"):
            return cls
        self.next()  # '{'
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok.value == "}":
                self.next()
                break
            if tok.value == ";":
                self.next()
                continue
            self.parse_class_member(cls)
        return cls

    def parse_class_member(self, cls: ClassInfo) -> None:
        doc = self.take_doc()
        # decorators
        while self.at("@"):
            self.next()
            if self.peek() is not None:
                self.next()
            if self.at("("):
                self.skip_balanced()
        is_static = False
        is_async = False
        kind = "method"
        while True:
            tok = self.peek()
            if tok is None:
                return
            if tok.value == "static":
                is_static = True
                self.next()
            elif tok.value == "async":
                is_async = True
                self.next()
            elif tok.value in ("public", "private", "protected", "readonly",
                               "abstract", "override", "declare", "accessor"):
                self.next()
            elif tok.value == "get" and self.peek(1) is not None and self.peek(1).kind == "ident":
                kind = "getter"
                self.next()
                break
            elif tok.value == "set" and self.peek(1) is not None and self.peek(1).kind == "ident":
                kind = "setter"
                self.next()
                break
            else:
                break
        name_tok = self.peek()
        if name_tok is None:
            return
        if name_tok.value == "constructor":
            kind = "constructor"
        if name_tok.value == "#":
            self.next()
            name_tok = self.peek()
        if name_tok is None or name_tok.kind not in ("ident", "string"):
            self.skip_statement()
            return
        name = name_tok.value.strip("\"'")
        self.next()
        if self.at("<"):
            self.skip_balanced()
        if self.at("("):
            params = self.parse_params()
            returns = self.parse_type_tail()
            if self.at("{"):
                self.skip_balanced()
            self.eat(";")
            cls.methods.append(FunctionInfo(
                name=name, params=params, returns=returns, doc=doc,
                summary=first_summary(doc), kind=kind, is_async=is_async,
                is_static=is_static, line=name_tok.line))
            return
        # property: name ?: Type (= init)? ;
        optional = self.eat("?")
        self.eat("!")
        ptype = None
        if self.eat(":"):
            toks = self.collect_until("=", ";", "\n")
            ptype = " ".join(t.value for t in toks).strip() or None
        if self.at("="):
            self.next()
            self.collect_until(";")
        self.eat(";")
        cls.properties.append(Param(name=name, type=ptype, optional=optional))

    def parse_interface(self) -> ClassInfo | None:
        doc = self.take_doc()
        line = self.peek().line if self.peek() else 0
        self.next()  # 'interface'
        name_tok = self.next()
        if name_tok is None or name_tok.kind != "ident":
            return None
        cls = ClassInfo(name=name_tok.value, kind="interface", doc=doc,
                        summary=first_summary(doc), line=line)
        heritage = self.collect_until("{")
        vals = [t.value for t in heritage]
        if "extends" in vals:
            idx = vals.index("extends")
            cls.bases = [v for v in vals[idx + 1:] if v != ","]
        if not self.at("{"):
            return cls
        self.next()
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok.value == "}":
                self.next()
                break
            if tok.value in (";", ","):
                self.next()
                continue
            member_doc = self.take_doc()
            while self.peek() is not None and self.peek().value in ("readonly", "static"):
                self.next()
            name_tok = self.peek()
            if name_tok is None or name_tok.kind != "ident":
                self.skip_statement()
                continue
            name = name_tok.value
            self.next()
            optional = self.eat("?")
            if self.at("(") :
                params = self.parse_params()
                returns = self.parse_type_tail()
                self.eat(";")
                self.eat(",")
                cls.methods.append(FunctionInfo(name=name, params=params, returns=returns,
                                                doc=member_doc, summary=first_summary(member_doc),
                                                kind="method", line=name_tok.line))
            else:
                ptype = None
                if self.eat(":"):
                    toks = self.collect_until(";", ",")
                    ptype = " ".join(t.value for t in toks).strip() or None
                self.eat(";")
                self.eat(",")
                cls.properties.append(Param(name=name, type=ptype, optional=optional))
        return cls

    def parse_enum(self) -> ClassInfo | None:
        doc = self.take_doc()
        line = self.peek().line if self.peek() else 0
        self.next()  # 'enum'
        name_tok = self.next()
        if name_tok is None or name_tok.kind != "ident":
            return None
        cls = ClassInfo(name=name_tok.value, kind="enum", doc=doc,
                        summary=first_summary(doc), line=line)
        if self.at("{"):
            self.next()
            while True:
                tok = self.peek()
                if tok is None:
                    break
                if tok.value == "}":
                    self.next()
                    break
                if tok.kind == "ident":
                    cls.properties.append(Param(name=tok.value))
                self.next()
        return cls

    def parse_variable(self, mod: ModuleInfo, exported: bool) -> None:
        doc = self.take_doc()
        self.next()  # const/let/var
        while True:
            name_tok = self.peek()
            if name_tok is None:
                return
            if name_tok.kind != "ident":
                self.skip_statement()
                return
            name = name_tok.value
            self.next()
            if self.at(":"):
                self.next()
                self.collect_until("=")
            # initializer — is it a function?
            fn = None
            if self.at("="):
                self.next()
                is_async = self.eat("async")
                if self.at("function"):
                    fn = self.parse_function(async_=is_async)
                    if fn is not None:
                        fn.name = name
                elif self.at("("):
                    save = self.pos
                    params = self.parse_params()
                    if self.at(":"):
                        self.next()
                        self.collect_until("=>")
                    if self.at("=>"):
                        self.next()
                        returns = None
                        if self.at("{"):
                            self.skip_balanced()
                        else:
                            self.collect_until(";", ",")
                        fn = FunctionInfo(name=name, params=params, returns=returns,
                                          doc=doc, summary=first_summary(doc),
                                          kind="arrow", is_async=is_async,
                                          line=name_tok.line)
                    else:
                        self.pos = save
                elif (self.peek() is not None and self.peek().kind == "ident"
                      and self.peek(1) is not None and self.peek(1).value == "=>"):
                    param_tok = self.next()
                    self.next()  # =>
                    if self.at("{"):
                        self.skip_balanced()
                    else:
                        self.collect_until(";", ",")
                    fn = FunctionInfo(name=name, params=[Param(name=param_tok.value)],
                                      doc=doc, summary=first_summary(doc), kind="arrow",
                                      is_async=is_async, line=name_tok.line)
            if fn is not None:
                fn.exported = exported
                mod.functions.append(fn)
            else:
                mod.variables.append(Param(name=name))
            if self.at(","):
                self.next()
                continue
            self.eat(";")
            return


def parse_js(source: str, rel_path: str, language: str = "typescript") -> ModuleInfo:
    mod = ModuleInfo(path=rel_path, language=language, lines=source.count("\n") + 1)
    tokens = lex(source)
    # module doc: a leading doc comment before any code token
    for tok in tokens:
        if tok.kind == "doc":
            mod.doc = _clean_doc(tok.value)
            mod.summary = first_summary(mod.doc)
            break
        if tok.kind != "comment":
            break
    parser = Parser(tokens)
    parser.parse_module(mod)
    mod.imports = sorted(set(mod.imports))
    return mod


def parse_js_file(path: Path, root: Path) -> ModuleInfo:
    source = path.read_text(encoding="utf-8", errors="replace")
    language = "typescript" if path.suffix in (".ts", ".tsx", ".mts", ".cts") else "javascript"
    return parse_js(source, str(path.relative_to(root)), language)
