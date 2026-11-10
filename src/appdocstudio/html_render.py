"""HTML rendering for role packs — WCAG-conscious by construction.

Design decisions aimed at WCAG 2.2 AA (a design target, verified by the
checks that can be automated — contrast ratios computed from the palette
below, semantic structure, focus visibility — not a certification):

- one <h1>, headings in order, landmark elements (header/main/footer),
  a skip link as the first focusable element;
- body text #1a1a1a on #ffffff (contrast ≈ 17:1), links #0b5394 on
  #ffffff (contrast ≈ 7.0:1) and underlined;
- visible focus outline; tables use <th scope="col">;
- schema.org TechArticle JSON-LD embedded for discoverability.

The Markdown converter covers exactly the subset AppDocStudio packs
emit: headings, paragraphs, ordered/unordered lists, tables, fenced code,
inline code, bold, and italics.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import html
import json
import re

from .model import ProjectInfo
from .packs import Pack

_CSS = """
:root { color-scheme: light; }
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: #1a1a1a;
       background: #ffffff; line-height: 1.6; margin: 0; }
main { max-width: 52rem; margin: 0 auto; padding: 1rem 1.25rem 3rem; }
a { color: #0b5394; text-decoration: underline; }
a:focus-visible { outline: 3px solid #0b5394; outline-offset: 2px; }
.skip-link { position: absolute; left: -9999px; top: 0; background: #1a1a1a; color: #ffffff;
             padding: 0.5rem 1rem; }
.skip-link:focus { left: 0; }
code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.92em;
       background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px; }
pre { background: #f0f0f0; padding: 1rem; overflow-x: auto; border-radius: 4px; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid #767676; padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
nav.quadrants { border: 1px solid #767676; padding: 0.75rem 1rem; margin: 1rem 0; }
footer { max-width: 52rem; margin: 0 auto; padding: 1rem 1.25rem 2rem; color: #444444;
         border-top: 1px solid #767676; font-size: 0.9rem; }
"""


def _inline(text: str) -> str:
    out = html.escape(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", out)
    out = re.sub(r"_([^_\n]+)_", r"<em>\1</em>", out)
    return out


def markdown_to_html(md: str) -> str:
    """Convert the pack Markdown subset to HTML (heading levels preserved)."""
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    list_tag: str | None = None

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            close_list()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and \
                re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            close_list()
            headers = [c.strip() for c in line.strip().strip("|").split("|")]
            out.append("<table>")
            out.append("<thead><tr>" + "".join(
                f'<th scope="col">{_inline(h)}</th>' for h in headers) + "</tr></thead>")
            out.append("<tbody>")
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
                i += 1
            out.append("</tbody></table>")
            continue
        item = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if item:
            tag = "ol" if item.group(2)[0].isdigit() else "ul"
            if list_tag != tag:
                close_list()
                list_tag = tag
                out.append(f"<{tag}>")
            out.append(f"<li>{_inline(item.group(3))}</li>")
            i += 1
            continue
        if not line.strip():
            close_list()
            i += 1
            continue
        close_list()
        out.append(f"<p>{_inline(line.strip())}</p>")
        i += 1
    close_list()
    return "\n".join(out)


def pack_to_html(pack: Pack, project: ProjectInfo, doc_format: str = "diataxis") -> str:
    md = pack.to_markdown(project, doc_format)
    body = markdown_to_html(md)
    json_ld = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": f"{project.name} — {pack.title}",
        "about": {"@type": "SoftwareSourceCode", "name": project.name},
        "author": {"@type": "Organization", "name": "AIMLDS (2351485 ALBERTA INC.)"},
        "license": "https://www.apache.org/licenses/LICENSE-2.0",
    }
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(project.name)} — {html.escape(pack.title)}</title>
<style>{_CSS}</style>
<script type="application/ld+json">{json.dumps(json_ld, indent=2)}</script>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<main id="main">
{body}
</main>
<footer>
<p>Generated by AppDocStudio — free and open source under Apache-2.0.
If it saved you time, tips are welcome via the project's funding page.</p>
</footer>
</body>
</html>
"""
