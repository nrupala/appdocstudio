# Standards AppDocStudio's generated documentation is designed to meet

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0

**Claim discipline.** Every row below is a *design target*: the generated
output is built to satisfy it, and the test suite checks the parts that can
be checked mechanically (structure, contrast values, identifier formats).
Nothing here is a certification, and AppDocStudio never claims one — for
its own output or for yours.

| Layer | Standard / framework | What it means for the generated output |
|---|---|---|
| Doc architecture | **Diátaxis** (tutorials / how-to / reference / explanation) | Every role pack is structured in the four Diátaxis quadrants |
| Markdown output | **CommonMark** spec | Generated `.md` renders identically across CommonMark renderers |
| API reference | **OpenAPI 3.1** | If the project carries an OpenAPI description, the Developer pack documents it (title, version, endpoint inventory) |
| Source comments | **TSDoc / JSDoc** (TS/JS), **Google-style docstrings** (Python) | The parsers read the comment standards developers already write, and attach them to the declarations they document |
| Doc quality (frame) | **ISO/IEC/IEEE 26514** (user documentation design & development) and **ISO/IEC/IEEE 15289** (software documentation content) | The packs are designed against the recognized international standards for software user documentation |
| Accessibility | **WCAG 2.2 AA** | Generated HTML uses semantic landmarks, ordered headings, a skip link, visible focus, `scope="col"` table headers, and a palette whose contrast ratios meet AA (≈17:1 body text, ≈7:1 links) |
| Licence inventory | **SPDX** identifiers + **CycloneDX 1.5** SBOM | Maintainer and Regulator packs carry the SPDX licence table; generation also emits `sbom.cdx.json` |
| Discoverability | **schema.org** (`TechArticle` / `SoftwareSourceCode`) JSON-LD | Generated HTML sites carry the entity markup search engines read |
| Compliance support | **SOC 2 / ISO/IEC 27001** evidence expectations | The Regulator pack is *evidence-production support*: it assembles audit-trail documentation (licence inventory + SHA-256 source inventory). It never claims to certify |
| The product itself | House **Gate 17** release discipline | AppDocStudio's own releases pass the release gate before they are called live; the verdict is recorded in the release notes |
