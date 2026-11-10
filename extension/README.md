# AppDocStudio browser extension

The extension cell of AppDocStudio: a small popup that acts as a remote
control for the studio's **local API** on the same machine.

## How it works

1. Start the API: `appdocstudio serve` (binds 127.0.0.1:8932).
2. Load this folder as an unpacked extension
   (Chrome/Edge: `chrome://extensions` → Developer mode → Load unpacked;
   the manifest is Manifest V3).
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
- Store distribution (Chrome Web Store / Edge Add-ons) is a separate,
  owner-gated step; this cell ships as a load-unpacked extension in the
  repository.
