const tree = document.querySelector("#tree");
const pathInput = document.querySelector("#path-input");
const treePath = document.querySelector("#tree-path");
const details = document.querySelector("#details");
const emptyState = document.querySelector("#empty-state");
const recycleButton = document.querySelector("#recycle-button");
const toast = document.querySelector("#toast");
let selectedPath = null;

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.style.background = isError ? "#5b2730" : "#243c2e";
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 3600);
}

async function request(url, options) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "The request failed.");
  return body;
}

function settings() {
  return `include_hidden=${document.querySelector("#hidden-toggle").checked}&include_protected=${document.querySelector("#protected-toggle").checked}`;
}

function renderEntries(entries) {
  tree.replaceChildren();
  if (!entries.length) { tree.textContent = "This folder has no visible, reviewable items."; return; }
  for (const entry of entries) {
    const button = document.createElement("button");
    button.className = "tree-row";
    button.dataset.path = entry.path;
    button.innerHTML = `<span class="icon">${entry.isDirectory ? "▸" : "•"}</span><span class="label"></span>${entry.protected ? '<span class="tag">protected</span>' : ""}`;
    button.querySelector(".label").textContent = entry.name;
    button.addEventListener("click", () => selectItem(entry.path, button));
    button.addEventListener("dblclick", () => { if (entry.isDirectory) browse(entry.path); });
    tree.append(button);
  }
}

async function browse(path) {
  try {
    const data = await request(`/api/list?path=${encodeURIComponent(path)}&${settings()}`);
    pathInput.value = data.path;
    treePath.textContent = data.path;
    renderEntries(data.entries);
    details.hidden = true;
    emptyState.hidden = false;
    selectedPath = null;
  } catch (error) { showToast(error.message, true); }
}

async function selectItem(path, button) {
  try {
    document.querySelectorAll(".tree-row.selected").forEach(row => row.classList.remove("selected"));
    button?.classList.add("selected");
    const item = await request(`/api/details?path=${encodeURIComponent(path)}`);
    selectedPath = item.path;
    details.hidden = false;
    emptyState.hidden = true;
    document.querySelector("#kind").textContent = item.kind.toUpperCase();
    document.querySelector("#name").textContent = item.name;
    document.querySelector("#selected-path").textContent = item.path;
    document.querySelector("#size").textContent = item.sizeDisplay;
    document.querySelector("#modified").textContent = new Date(item.modified).toLocaleString();
    document.querySelector("#contents").textContent = item.contents.length ? item.contents.join(", ") : "No immediate visible contents";
    document.querySelector("#source").textContent = item.assessment.source;
    document.querySelector("#recommendation").textContent = item.assessment.recommendation;
    document.querySelector("#summary").textContent = item.assessment.summary;
    document.querySelector("#reason").textContent = item.assessment.reason;
    document.querySelector("#protected-note").hidden = !item.protected;
    recycleButton.disabled = item.protected;
  } catch (error) { showToast(error.message, true); }
}

document.querySelector("#path-form").addEventListener("submit", event => { event.preventDefault(); browse(pathInput.value); });
document.querySelectorAll(".toggle input").forEach(control => control.addEventListener("change", () => browse(pathInput.value)));
recycleButton.addEventListener("click", async () => {
  if (!selectedPath) return;
  if (!confirm(`Move this item to the Recycle Bin?\n\n${selectedPath}\n\nIt will not be permanently deleted.`)) return;
  try {
    const result = await request("/api/recycle", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: selectedPath }) });
    showToast(result.message);
    browse(pathInput.value);
  } catch (error) { showToast(error.message, true); }
});

browse("~");
