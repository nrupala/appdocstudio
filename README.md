# AppDocStudio — one scan, six audience-tailored documentation sets

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/License-Apache--2.0-green" alt="License: Apache-2.0">
  <img src="https://img.shields.io/badge/Dependencies-zero-yellow" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/Role%20Based%20Docs-6%20audiences-purple" alt="Six role packs">
</p>

Most documentation generators produce **one** developer reference. AppDocStudio
scans a codebase once and generates **six documentation sets, one per audience** —
because users, regulators, and on-call operators do not need the same document:

| Audience | What they get |
|---|---|
| 👤 **Users** | Getting-started tutorial, task how-tos, feature reference |
| 💻 **Developers** | API reference from real parsing, architecture, OpenAPI section |
| 🔧 **Maintainers** | Licence inventory (SPDX), module map, documentation-health report |
| 📋 **Regulators** | Compliance-evidence pack: SPDX inventory, CycloneDX component list, SHA-256 source inventory |
| ⚙️ **Admins** | Installation, configuration inventory, backup/restore |
| 🚀 **Ops** | Runbook: bring-up, incident response, CI/deployment workflows |

Every pack is structured on the **Diátaxis** framework (tutorial / how-to /
reference / explanation) and emitted as **CommonMark Markdown** and
**WCAG-conscious HTML** (semantic landmarks, skip link, checked contrast —
see [docs/STANDARDS.md](docs/STANDARDS.md) for the standards the output is
designed to meet).

## The free face — no install

Open [`index.html`](index.html) in a browser. It is a single-file, zero-dependency
web tool: pick a project folder, scan it, and read or export role-based docs,
2D/3D flow views, and a call graph. Nothing leaves your machine.

AppDocStudio is free. If it saves you time, the tip jar is in
[`.github/FUNDING.yml`](.github/FUNDING.yml) (Buy Me a Coffee / PayPal) —
tips are voluntary and buy nothing extra.

## The productized core — CLI and MCP server

Version 1.0 adds a real parser core (no more regex-grade detection):

- **Python** — parsed with the standard-library `ast` module: classes,
  methods, functions, signatures with types and defaults, docstrings.
- **TypeScript / JavaScript** — parsed by a hand-written lexer and
  recursive-descent parser that builds a declaration AST: functions,
  arrow functions, classes, interfaces, enums, type aliases, JSDoc/TSDoc
  comments. Strings and comments that merely *look* like code never leak
  into the output.

Zero dependencies — Python standard library only, Python ≥ 3.10.

Parser scope, honestly: the TS/JS parser covers the *declaration* grammar
(functions, classes, interfaces, enums, type aliases, imports/exports,
JSDoc/TSDoc). Constructs outside that grammar — for example conditional
or namespace re-export blocks — are skipped, never misreported; a file
that cannot be parsed at all is reported with its parse error, not
silently dropped.

### Quick start

```bash
pip install .            # or run without installing: PYTHONPATH=src python3 -m appdocstudio

appdocstudio scan ./your-project
appdocstudio generate ./your-project -o appdocs     # six packs (.md + .html) + sbom.cdx.json
appdocstudio role-pack ./your-project regulators    # one pack to stdout
```

### MCP server

AppDocStudio is also an MCP server (stdio), so an AI agent can document a
codebase as a tool call:

```json
{
  "mcpServers": {
    "appdocstudio": {
      "command": "appdocstudio-mcp"
    }
  }
}
```

Tools: `scan_project` · `generate_docs` · `role_pack`.

## Standards the output is designed to meet

These are **design targets the output is built to** — not certifications.
The full table, with what each one means for the generated documents, is in
[docs/STANDARDS.md](docs/STANDARDS.md): Diátaxis, CommonMark, OpenAPI 3.1,
TSDoc/JSDoc and Google-style docstrings, ISO/IEC/IEEE 26514 and 15289,
WCAG 2.2 AA, SPDX + CycloneDX, schema.org, and SOC 2 / ISO 27001
evidence-production support (the Regulator pack assembles audit-trail
documentation; it never claims to certify anything).

## Tests

```bash
python3 -m unittest discover -s tests
```

The suite covers both parsers, the scanner, all six packs, the HTML
renderer, the CLI end to end, and a live MCP stdio round-trip.

## Commercial

The code is Apache-2.0 and needs no commercial licence. 2351485 ALBERTA INC.
sells the doing around it — documentation engagements, custom role packs,
integration and CI doc-drift work — see
[COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md) and the licence map in
[LICENSING.md](LICENSING.md).

## Licence

Apache License, Version 2.0 — see [LICENSE](LICENSE).
Copyright 2026 2351485 ALBERTA INC.

> Note: copies of AppDocStudio obtained before 2026-10-26 were distributed
> under the MIT License and keep their MIT terms; the Apache-2.0 licence
> applies from the 2026-10-26 licence change onward.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md): draft PR → CI green → owner merges,
a CHANGELOG entry per PR, no direct pushes to `main`.

---

<p align="center">
  <strong>AppDocStudio</strong> — documentation for every role · by AIMLDS (2351485 ALBERTA INC.)
</p>
