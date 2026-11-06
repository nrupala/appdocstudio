# Test plan — appdocstudio

## Scope

AppDocStudio is a single-file static web app (`index.html`, vanilla JS, no build
step): it scans a project (File System Access API where available, otherwise its
built-in fixture project), extracts functions and variables, and generates
role-specific documentation (user, developer, maintainer, regulator, admin, ops)
with JSON/full/API exports. Out of scope: browsers' File System Access picker
itself and any hosting layer.

## Suites

| Suite | Covers | Run it | Runs in CI |
|---|---|---|---|
| Node built-in tests (`tests/appdocstudio.test.mjs`) | The inline app script parses and exposes the generator functions; `scanProject()` runs against the built-in fixture project and extracts its functions/variables; `genRole()` produces a distinct document for each of the six roles; `exportJSON()` emits valid JSON describing the scanned project; page shell declares its surfaces | `node --test tests/appdocstudio.test.mjs` | Yes — CI workflow (`.github/workflows/ci.yml`, test job) |

The suite runs the real app script in a VM with a minimal DOM stub — it executes
the shipped code, not a copy of it.

## CI gates

- Test job green on every push and pull request to `main` (alongside the
  existing file-verification job).
- CodeQL (javascript-typescript) runs on push, pull request, and weekly.

## Cadence

- Every pull request: CI (verify + test jobs) + CodeQL.
- Weekly: CodeQL scheduled run.
- Every release candidate: the release-readiness run (checker + evidence reads),
  per the house Release-Readiness Standard.

## Coverage bar

No numeric floor; new functionality lands with tests per CONTRIBUTING.
