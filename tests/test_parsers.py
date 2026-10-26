"""Parser tests — Python AST parser and TypeScript/JavaScript parser.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from appdocstudio.parser_python import parse_python  # noqa: E402
from appdocstudio.parser_js import parse_js  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class PythonParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = parse_python((FIXTURES / "sample.py").read_text(), "sample.py")

    def test_module_docstring(self):
        self.assertIn("Greeter service", self.mod.summary or "")

    def test_class_and_methods(self):
        classes = {c.name: c for c in self.mod.classes}
        self.assertIn("Greeter", classes)
        methods = {m.name: m for m in classes["Greeter"].methods}
        self.assertEqual(set(methods), {"__init__", "greet", "greet_many"})
        self.assertTrue(methods["greet_many"].is_async)

    def test_params_types_and_defaults(self):
        greet = next(m for c in self.mod.classes for m in c.methods if m.name == "greet")
        names = [p.name for p in greet.params]
        self.assertEqual(names, ["self", "name", "punctuate"])
        self.assertEqual(greet.params[1].type, "str")
        self.assertEqual(greet.params[2].default, "True")
        self.assertEqual(greet.returns, "str")

    def test_top_level_function_and_variable(self):
        self.assertIn("make_greeter", {f.name for f in self.mod.functions})
        self.assertIn("DEFAULT_LOCALE", {v.name for v in self.mod.variables})

    def test_syntax_error_is_reported_not_raised(self):
        bad = parse_python("def broken(:\n", "bad.py")
        self.assertIsNotNone(bad.parse_error)


class JsParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = parse_js((FIXTURES / "sample.ts").read_text(), "sample.ts")

    def test_functions(self):
        fns = {f.name: f for f in self.mod.functions}
        self.assertIn("formatMoney", fns)
        self.assertIn("summarize", fns)  # arrow function assigned to const
        self.assertEqual(fns["formatMoney"].returns, "string")
        self.assertTrue(fns["formatMoney"].exported)
        param_names = [p.name for p in fns["formatMoney"].params]
        self.assertEqual(param_names, ["money", "locale"])
        self.assertEqual(fns["formatMoney"].params[1].default, '"en-CA"')

    def test_jsdoc_attached(self):
        fn = next(f for f in self.mod.functions if f.name == "formatMoney")
        self.assertIn("Format a money amount", fn.summary or "")

    def test_class_members(self):
        cls = next(c for c in self.mod.classes if c.name == "InvoiceService")
        methods = {m.name: m for m in cls.methods}
        self.assertIn("createInvoice", methods)
        self.assertIn("describe", methods)
        self.assertIn("size", methods)
        self.assertTrue(methods["createInvoice"].is_async)
        self.assertTrue(methods["describe"].is_static)
        self.assertEqual(methods["size"].kind, "getter")
        props = {p.name for p in cls.properties}
        self.assertIn("counter", props)
        self.assertIn("name", props)

    def test_interface_enum_type(self):
        kinds = {(c.name, c.kind) for c in self.mod.classes}
        self.assertIn(("Invoice", "interface"), kinds)
        self.assertIn(("InvoiceStatus", "enum"), kinds)
        invoice = next(c for c in self.mod.classes if c.name == "Invoice")
        props = {p.name: p for p in invoice.properties}
        self.assertIn("total", props)
        self.assertTrue(props["paid"].optional)
        self.assertTrue(any("Money" in a for a in self.mod.type_aliases))

    def test_regex_trap_constructs_do_not_leak(self):
        # Strings and comments that merely look like declarations must
        # not produce phantom functions (the regex-grade failure mode).
        source = 'const s = "function fake() {}";\n// function alsoFake() {}\n' \
                 'export function real(x: number): number { return x; }\n'
        mod = parse_js(source, "trap.ts")
        names = {f.name for f in mod.functions}
        self.assertEqual(names, {"real"})


if __name__ == "__main__":
    unittest.main()
