# Changelog

All notable changes to AppDocStudio are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Productized v1:** AST-based parser core for Python (stdlib `ast`) and
  TypeScript/JavaScript (hand-written lexer + recursive-descent declaration
  parser) in `src/appdocstudio/`, replacing regex-grade detection for the
  CLI/MCP surfaces.
- **Role packs:** all six audience packs (users, developers, maintainers,
  regulators, admins, ops) structured on Diátaxis, rendered to CommonMark
  Markdown and WCAG-conscious HTML with schema.org JSON-LD; CycloneDX
  `sbom.cdx.json` component inventory on generate.
- **CLI** (`appdocstudio scan|generate|role-pack`) and **MCP server**
  (`appdocstudio-mcp`: `scan_project` / `generate_docs` / `role_pack`).
- **Tests:** parser, scanner, pack, HTML, CLI, and live MCP round-trip
  suites (zero-test state closed).
- `docs/STANDARDS.md` — the standards table the generated output is
  designed to meet (targets, not certifications).

### Fixed
- **Web tool was inert (escaped defect, pre-existing on `main`):** a
  missing closing parenthesis in a `match(...)` call in `index.html`
  made the entire inline script unparseable — the page rendered but no
  button worked. Fixed, and guarded by `tests/test_web_face.py`
  (script-parse check + role-button/tab presence) so the class cannot
  escape twice.

### Changed
- **Licence: MIT → Apache-2.0 + commercial** (Director's decision,
  2026-10-26), copyright holder 2351485 ALBERTA INC. Added `LICENSING.md`
  (licence map), `COMMERCIAL-LICENSE.md` (commercial services), and
  `NOTICE`. Copies obtained under MIT keep their MIT terms.
- **FUNDING.yml** completed to the house pattern: Buy Me a Coffee
  (`nrupalakolt`) + PayPal (`paypal.me/nrupalakolkar`); the GitHub Sponsors
  field was removed (not enrolled).
- **README** rewritten as the storefront: six audiences, the free web
  face, CLI/MCP quick start, standards summary, licence note.
- `TERMS.md` contact corrected to info@aimlds.org.


### Added
- **Portfolio certification rollout:** `CONTRIBUTING.md` (PR-flow discipline:
  draft PR → CI green → owner merges; no direct pushes to `main`;
  `CHANGELOG` entry under Unreleased per PR; merge commits reference PR
  numbers; releases tagged `vX.Y.Z`), `CHANGELOG.md`, and `ATTRIBUTION.md`.
- MIT license header comment on `index.html`.

### Notes
- This repo has no version file (version badges in `README.md` and the
  `meta` tag in `index.html` are informational only), so no semver bump was
  made in this PR.
- No deploy target found: CI only verifies repository files; there is no
  deploy script, workflow, or hosting config to delegate to the signed-deploy
  wrapper.
