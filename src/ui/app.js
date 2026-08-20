const tree = document.querySelector("#tree");
const pathInput = document.querySelector("#path-input");
const treePath = document.querySelector("#tree-path");
const details = document.querySelector("#details");
const emptyState = document.querySelector("#empty-state");
const openButton = document.querySelector("#open-button");
const aiButton = document.querySelector("#ai-button");
const recycleButton = document.querySelector("#recycle-button");
const toast = document.querySelector("#toast");
let selectedPath = null;
let selectionVersion = 0;

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

function formatModified(timestamp) {
    const date = new Date(timestamp);
    return `${date.toLocaleDateString()} at ${date.toLocaleTimeString()}`;
}

function renderEntries(entries) {
    tree.replaceChildren();
    if (!entries.length) {
        tree.textContent = "This folder has no visible, reviewable items.";
        return;
    }
    for (const entry of entries) {
        const button = document.createElement("button");
        button.className = "tree-row";
        button.dataset.path = entry.path;
        button.innerHTML = `<span class="icon">${entry.isDirectory ? "▸" : "•"}</span><span class="label"></span>${entry.protected ? '<span class="tag">protected</span>' : ""}`;
        button.querySelector(".label").textContent = entry.name;
        button.addEventListener("click", () => selectItem(entry.path, button));
        button.addEventListener("dblclick", () => {
            if (entry.isDirectory) browse(entry.path);
        });
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
        selectionVersion += 1;
        selectItem(data.path);
    } catch (error) {
        showToast(error.message, true);
    }
}

async function selectItem(path, button) {
    try {
        document.querySelectorAll(".tree-row.selected").forEach(row => row.classList.remove("selected"));
        button?.classList.add("selected");
        const item = await request(`/api/details?path=${encodeURIComponent(path)}`);
        selectedPath = item.path;
        const selectedVersion = ++selectionVersion;
        details.hidden = false;
        emptyState.hidden = true;
        document.querySelector("#kind").textContent = item.kind.toUpperCase();
        document.querySelector("#name").textContent = item.name;
        document.querySelector("#selected-path").textContent = item.path;
        document.querySelector("#size").textContent = item.sizeDisplay;
        document.querySelector("#modified").textContent = formatModified(item.modified);
        document.querySelector("#contents").textContent = item.contents.length
            ? item.contents.join(", ")
            : item.contentsKnown
                ? "No immediate contents, including hidden items"
                : "Immediate contents could not be read";
        document.querySelector("#source").textContent = item.assessment.source;
        document.querySelector("#recommendation").textContent = item.assessment.recommendation;
        document.querySelector("#summary").textContent = item.assessment.summary;
        document.querySelector("#reason").textContent = item.assessment.reason;
        document.querySelector("#protected-note").hidden = !item.protected;
        recycleButton.disabled = item.protected;
        openButton.hidden = item.isDirectory;
        aiButton.disabled = false;
        aiButton.textContent = "Analyze with AI";

        document.querySelector("#ai-result").hidden = true;

        if (item.isDirectory) refreshFolderSize(item.path, selectedVersion);
    } catch (error) {
        showToast(error.message, true);
    }
}

async function refreshFolderSize(path, selectedVersion) {
    try {
        const data = await request(`/api/folder-size?path=${encodeURIComponent(path)}`);
        if (selectedVersion !== selectionVersion) return;
        if (data.status === "calculating") {
            setTimeout(() => refreshFolderSize(path, selectedVersion), 350);
            return;
        }
        const skipped = data.inaccessible ? `; ${data.inaccessible} inaccessible item(s)` : "";
        document.querySelector("#size").textContent = `${data.display} (${data.files} files, ${data.folders} folders${skipped})`;
    } catch (error) {
        if (selectedVersion === selectionVersion) document.querySelector("#size").textContent = "Folder size unavailable";
    }
}

document.querySelector("#path-form").addEventListener("submit", event => {
    event.preventDefault();
    browse(pathInput.value);
});
document.querySelectorAll(".toggle input").forEach(control => control.addEventListener("change", () => browse(pathInput.value)));
document.querySelector("#up-button").addEventListener("click", () => {
    const current = pathInput.value;
    const separator = current.includes("\\") ? "\\" : "/";
    const trimmed = current.endsWith(separator) ? current.slice(0, -1) : current;
    const parent = trimmed.lastIndexOf(separator);
    if (parent > 0) browse(trimmed.slice(0, parent + 1));
});
aiButton.addEventListener("click", async () => {
    if (!selectedPath) return;

    console.log("here");
    const pathAtStart = selectedPath;

    aiButton.disabled = true;
    aiButton.textContent = "Analyzing…";

    try {
        const result = await request(
            `/api/ai-analyze?path=${encodeURIComponent(pathAtStart)}`
        );

        // The user may have selected something else while the AI was thinking.
        if (selectedPath !== pathAtStart) return;

        document.querySelector("#ai-result").hidden = false;
        document.querySelector("#ai-classification").textContent =
            result.classification;

        document.querySelector("#ai-risk").textContent =
            result.risk;

        document.querySelector("#ai-confidence").textContent =
            `${Math.round(result.confidence * 100)}%`;

        document.querySelector("#ai-recreated").textContent =
            result.recreated ? "Yes" : "No";

        document.querySelector("#ai-reason").textContent =
            result.reason;

        document.querySelector("#source").textContent =
            result.source;

        document.querySelector("#recommendation").textContent =
            result.recommendation;

        document.querySelector("#summary").textContent =
            result.summary;

        showToast("AI analysis complete.");
    } catch (error) {
        if (selectedPath === pathAtStart) {
            showToast(error.message, true);
        }
    } finally {
        if (selectedPath === pathAtStart) {
            aiButton.disabled = false;
            aiButton.textContent = "Analyze with AI";
        }
    }
});
openButton.addEventListener("click", async () => {
    if (!selectedPath) return;
    try {
        const result = await request("/api/open-vscode", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({path: selectedPath})
        });
        showToast(result.message);
    } catch (error) {
        showToast(error.message, true);
    }
});
recycleButton.addEventListener("click", async () => {
    if (!selectedPath) return;
    if (!confirm(`Move this item to the Recycle Bin?\n\n${selectedPath}\n\nIt will not be permanently deleted.`)) return;
    try {
        const result = await request("/api/recycle", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({path: selectedPath})
        });
        showToast(result.message);
        browse(pathInput.value);
    } catch (error) {
        showToast(error.message, true);
    }
});

browse("~");
