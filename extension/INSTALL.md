# Install the AppDocStudio extension (self-hosted)

This extension is distributed from our own shelf — the project's GitHub
release — not from the Chrome Web Store.

## Chrome / Edge / Brave (desktop)

1. Download `appdocstudio-extension-1.2.0.zip` from the project's
   GitHub release (v1.2.0) and unzip it.
2. Open `chrome://extensions` (Edge: `edge://extensions`).
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked** and select the unzipped folder.
5. Start the local API on the same machine: `appdocstudio serve`.
6. Click the AppDocStudio toolbar icon, type a local project path,
   pick a role pack and a standards format, and generate.

## Notes

- The extension only talks to the AppDocStudio API on your own machine
  (loopback). It sends nothing anywhere else.
- Self-hosted extensions do not auto-update from a store. To update,
  download the newer release zip and reload the extension.
- Firefox: the manifest is MV3; use `about:debugging` →
  "This Firefox" → "Load Temporary Add-on" for a session install.
