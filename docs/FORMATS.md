# Standards-format profiles

AppDocStudio's spine is Diátaxis structure over an ISO/IEC/IEEE 26514 &
15289-conformant content model. A **format profile** renders that spine
in the structure and style of a documentation standard or house style.
Profiles change what is mechanically checkable in the output: front
matter, section naming, heading case, clause numbering, and the
conventions and disclaimer blocks. They are **design targets** — a pack
in the ISO profile follows the ISO drafting structure; it is not an ISO
standard and claims no certification.

Select a profile anywhere a pack is generated:

```bash
appdocstudio generate ./project --doc-format iso
appdocstudio role-pack ./project regulators --doc-format w3c
appdocstudio formats            # list all profiles
```

Over MCP and the API the same choice is the `doc_format` argument.

| Profile | Follows | What changes |
|---|---|---|
| `diataxis` | Diátaxis framework; ISO/IEC/IEEE 26514 & 15289 content model | The base rendering; no house style applied |
| `apache` | Apache Software Foundation project documentation conventions | "About this document" front matter; ASF attribution/trademark footer |
| `google` | Google developer documentation style guide | Sentence-case headings; Diátaxis quadrants renamed (Concepts, How-to guide); style conventions note |
| `microsoft` | Microsoft Writing Style Guide; Microsoft Learn conventions | Sentence-case headings; "In this article" front matter; Quickstart/Concepts naming |
| `apple` | Apple Style Guide | Title-case headings; Getting Started/Overview naming; plain-language conventions note |
| `w3c` | W3C specification conventions | Abstract + "Status of This Document" front matter; RFC 2119 conformance-keywords note; explicit not-a-W3C-publication footer |
| `iso` | ISO/IEC Directives, Part 2 | Foreword + Introduction; numbered clauses (1, 1.1, …); shall/should/may verbal-forms note; not-an-ISO-publication footer |
| `ansi` | ANSI Essential Requirements; ANS drafting practice | Foreword; numbered clauses; shall/should/may note; not-an-ANS footer |
| `en` | CEN/CENELEC Internal Regulations, Part 3 | European foreword + Introduction; numbered clauses; verbal-forms note; not-an-EN footer |

## What a profile does not do

- It does not restyle the *content extracted from the code* — doc comments
  are reproduced as written; a profile shapes the document around them.
- It does not convert a generated pack into a publication of ASF, Google,
  Microsoft, Apple, W3C, ISO, ANSI, or CEN/CENELEC; standards-body
  profiles carry an explicit footer saying so.
- It does not certify conformance with the standard it follows. If a
  deliverable needs certified conformance, that is an engagement, not a
  rendering option — see COMMERCIAL-LICENSE.md.
