"""AppDocStudio Desktop — a small native window over the studio core.

The desktop cell of the studio: pick a project folder, pick a role pack
(or all six) and a standards format, generate, and open the output
folder. All behaviour lives in desktop_logic.py (unit-tested); this file
is the thin tkinter shell. tkinter is part of the Python standard
library, so the zero-dependency rule holds.

Launch:  appdocstudio desktop     (or: python -m appdocstudio.desktop)
Packaged binaries are built by .github/workflows/desktop.yml.

Copyright 2026 2351485 ALBERTA INC. — SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from .formats import FORMAT_IDS
from .packs import ROLES


def _open_folder(path: str) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606 - opening the user's own output folder
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def main() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    from . import desktop_logic as logic

    root = tk.Tk()
    root.title(f"AppDocStudio {__version__} — Documentation Studio")
    root.geometry("680x500")

    project_var = tk.StringVar()
    out_var = tk.StringVar(value=str(Path.cwd() / "appdocs"))
    role_var = tk.StringVar(value="all")
    format_var = tk.StringVar(value="diataxis")
    medium_var = tk.StringVar(value="both")
    recent_var = tk.StringVar()
    status_var = tk.StringVar(value="Pick a project folder to begin.")

    def show_summary(path: str) -> None:
        try:
            s = logic.scan_summary(path)
            status_var.set(f"{s['name']}: {s['files']} files, {s['lines']} lines, "
                           f"{s['modules']} modules parsed.")
        except Exception as exc:
            status_var.set(f"Scan failed: {exc}")

    def browse_project() -> None:
        chosen = filedialog.askdirectory(title="Project folder")
        if chosen:
            project_var.set(chosen)
            show_summary(chosen)

    def pick_recent(_event=None) -> None:
        chosen = recent_var.get()
        if chosen:
            project_var.set(chosen)
            show_summary(chosen)

    def browse_out() -> None:
        chosen = filedialog.askdirectory(title="Output folder")
        if chosen:
            out_var.set(chosen)

    def run_generate() -> None:
        try:
            written = logic.generate(project_var.get(), out_var.get(),
                                     role=role_var.get(), doc_format=format_var.get(),
                                     medium=medium_var.get())
            status_var.set(f"Wrote {len(written)} files to {out_var.get()}")
        except Exception as exc:
            messagebox.showerror("AppDocStudio", str(exc))
            status_var.set(f"Failed: {exc}")

    def run_preview() -> None:
        role = role_var.get()
        role = "users" if role == "all" else role
        try:
            result = logic.preview(project_var.get(), role=role,
                                   doc_format=format_var.get())
        except Exception as exc:
            messagebox.showerror("AppDocStudio", str(exc))
            status_var.set(f"Preview failed: {exc}")
            return
        window = tk.Toplevel(root)
        window.title(f"Preview — {result['role']} ({result['doc_format']})")
        window.geometry("720x560")
        text = tk.Text(window, wrap="word")
        text.insert("1.0", result["markdown"])
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)

    pad = {"padx": 10, "pady": 6}
    ttk.Label(root, text="Project folder").grid(row=0, column=0, sticky="w", **pad)
    ttk.Entry(root, textvariable=project_var, width=52).grid(row=0, column=1, **pad)
    ttk.Button(root, text="Browse…", command=browse_project).grid(row=0, column=2, **pad)

    ttk.Label(root, text="Output folder").grid(row=1, column=0, sticky="w", **pad)
    ttk.Entry(root, textvariable=out_var, width=52).grid(row=1, column=1, **pad)
    ttk.Button(root, text="Browse…", command=browse_out).grid(row=1, column=2, **pad)

    ttk.Label(root, text="Role pack").grid(row=2, column=0, sticky="w", **pad)
    ttk.Combobox(root, textvariable=role_var, values=("all",) + ROLES,
                 state="readonly").grid(row=2, column=1, sticky="w", **pad)
    ttk.Label(root, text="Standards format").grid(row=3, column=0, sticky="w", **pad)
    ttk.Combobox(root, textvariable=format_var, values=FORMAT_IDS,
                 state="readonly").grid(row=3, column=1, sticky="w", **pad)
    ttk.Label(root, text="Output").grid(row=4, column=0, sticky="w", **pad)
    ttk.Combobox(root, textvariable=medium_var, values=("both", "md", "html"),
                 state="readonly").grid(row=4, column=1, sticky="w", **pad)

    ttk.Button(root, text="Generate documentation", command=run_generate).grid(
        row=5, column=1, sticky="w", **pad)
    ttk.Button(root, text="Preview pack", command=run_preview).grid(
        row=5, column=0, sticky="w", **pad)
    ttk.Button(root, text="Open output folder",
               command=lambda: _open_folder(out_var.get())).grid(row=5, column=2, **pad)

    recents = logic.load_recents()
    if recents:
        ttk.Label(root, text="Recent projects").grid(row=6, column=0, sticky="w", **pad)
        box = ttk.Combobox(root, textvariable=recent_var, values=recents,
                           state="readonly", width=52)
        box.grid(row=6, column=1, **pad)
        box.bind("<<ComboboxSelected>>", pick_recent)
    ttk.Label(root, textvariable=status_var, wraplength=600).grid(
        row=7, column=0, columnspan=3, sticky="w", **pad)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
