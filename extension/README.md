# AppDocStudio browser extension

The extension cell of AppDocStudio: a small popup that acts as a remote
control for the studio's **local API** on the same machine.

## How it works

1. Start the API: `appdocstudio serve` (binds 127.0.0.1:8932).
2. Get the packaged extension from our own shelf: download
   `appdocstudio-extension-1.2.0.zip` from `extension/dist/` in this
   repository (at the v1.2.0 tag) — see `INSTALL.md` for the full steps.
   In short: unzip, open `chrome://extensions`, turn on Developer mode,
   Load unpacked, select the folder.
3. Open the popup, type the **local path** of a project folder, pick a
   role pack and a standards format, and generate. The pack renders in
   the popup and can be downloaded as Markdown.

## Honest limits

- The extension documents projects **on this machine**, through the
  local API — the browser cannot hand a web page's repository to the
  filesystem, and this extension does not pretend otherwise.
- Host permission is loopback-only (`http://127.0.0.1/*`). No data
  leaves the machine; the extension has no analytics and no remote
  endpoints.
- Distribution is **self-hosted by design** (owner's ruling,
  2026-11-09): the extension is installed from our own repository /
  release shelf, not from the Chrome Web Store or any other store.
  Self-hosted extensions do not auto-update; a new release zip is
  published with each version.
