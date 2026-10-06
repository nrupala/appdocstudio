# Changelog

All notable changes to AppDocStudio are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
