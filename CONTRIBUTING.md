# Contributing to AppDocStudio

Thank you for your interest in contributing to AppDocStudio!

## PR-flow discipline (required)

- **Draft PRs only.** Every change ships as a draft pull request against
  `main`; direct pushes to `main` are retired. CI must be green before review,
  and the owner merges when ready.
- **No direct pushes to `main`.** All changes land through a PR.
- **CHANGELOG entry.** Every PR adds an entry under `## [Unreleased]` in
  `CHANGELOG.md` describing the change. (This repo has no version file, so no
  semver bump is made — if versioned artifacts are added later, use
  patch=fix, minor=feature.)
- **Merge commits reference the PR number.** Releases are tagged `vX.Y.Z`
  after merge.

## How to contribute

1. Fork the repository and create a feature branch
   (`git checkout -b feature/amazing-feature`).
2. Make your changes — AppDocStudio is a single static `index.html`
   (100% vanilla JS, no build step). Open it in a browser to test.
3. Verify the file still loads and the scan flow works
   (open `index.html`, click through the roles tabs).
4. Add your `CHANGELOG.md` entry under `## [Unreleased]`.
5. Commit with conventional commits (`feat:`, `fix:`, `docs:`, `chore:`).
6. Push to your fork and open a **draft** PR.

## Code of conduct

- Be respectful and inclusive.
- Provide constructive feedback.
- Keep diffs minimal and focused.

## License

By contributing, you agree that your contributions are licensed under the
MIT License (see `LICENSE`).
