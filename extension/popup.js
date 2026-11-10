"use strict";
// AppDocStudio extension popup: a remote control for the local studio API.
// It holds no project data; it asks the API on this machine to generate a
// pack and shows/downloads the result.
let lastContent = "";
let lastRole = "users";

async function generate() {
  const api = document.getElementById("api").value.replace(/\/$/, "");
  const path = document.getElementById("path").value.trim();
  const role = document.getElementById("role").value;
  const docFormat = document.getElementById("docformat").value;
  const out = document.getElementById("out");
  out.textContent = "Generating…";
  try {
    const res = await fetch(api + "/v1/role-pack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path, role: role, doc_format: docFormat })
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || ("HTTP " + res.status));
    lastContent = body.content;
    lastRole = role;
    out.textContent = body.content.slice(0, 4000);
    document.getElementById("save").disabled = false;
  } catch (err) {
    out.textContent = "Could not reach the AppDocStudio API (" + err.message +
      "). Is `appdocstudio serve` running on this machine?";
    document.getElementById("save").disabled = true;
  }
}

function save() {
  const blob = new Blob([lastContent], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = lastRole + ".md";
  a.click();
  URL.revokeObjectURL(url);
}

document.getElementById("go").addEventListener("click", generate);
document.getElementById("save").addEventListener("click", save);
