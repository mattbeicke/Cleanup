"""Local-only web interface for Cleanup Assistant."""

from __future__ import annotations

import os
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from send2trash import send2trash

from .ai import analyze_item
from .assessment import removal_assessment
from .explainer import human_size
from .scanner import inspect_path, is_hidden, is_non_viewable, is_protected

STATIC_DIR = Path(__file__).parent.parent / "ui"
DEFAULT_PORT = 8765
app = FastAPI(title="Cleanup Assistant", docs_url=None, redoc_url=None)
app.mount("/ui", StaticFiles(directory=STATIC_DIR), name="ui")
size_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="folder-size")
size_lock = Lock()


@dataclass(frozen=True)
class FolderSize:
    bytes: int
    files: int
    folders: int
    inaccessible: int


size_cache: dict[Path, FolderSize] = {}
size_jobs: set[Path] = set()


class RecycleRequest(BaseModel):
    path: str


class OpenRequest(BaseModel):
    """Describe a user-selected file to launch in VS Code."""

    path: str


def calculate_folder_size(folder: Path) -> FolderSize:
    """Calculate an exact reachable size without following links outside the folder."""
    total_bytes = files = folders = inaccessible = 0
    pending = [folder]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            folders += 1
                            pending.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total_bytes += entry.stat(follow_symlinks=False).st_size
                            files += 1
                    except OSError:
                        inaccessible += 1
        except OSError:
            inaccessible += 1
    return FolderSize(total_bytes, files, folders, inaccessible)


def _cache_folder_size(folder: Path) -> None:
    result = calculate_folder_size(folder)
    with size_lock:
        size_cache[folder] = result
        size_jobs.discard(folder)


def get_folder_size(folder: Path) -> FolderSize | None:
    """Return a cached size, scheduling an exact calculation when needed."""
    with size_lock:
        cached = size_cache.get(folder)
        if cached is not None:
            return cached
        if folder not in size_jobs:
            size_jobs.add(folder)
            size_executor.submit(_cache_folder_size, folder)
    return None


def immediate_contents(folder: Path) -> tuple[list[str], bool]:
    """Return a small unfiltered directory sample and whether it was readable.

    No hidden-item filtering is applied here: an empty successful result proves
    that the folder has no immediate contents of any visibility.
    """
    try:
        with os.scandir(folder) as entries:
            return [entry.name for _, entry in zip(range(5), entries)], True
    except OSError:
        return [], False


def find_vscode() -> str | None:
    """
    #Locate VS Code without relying on, or changing, file associations.
    command = shutil.which("code")
    if command:
        return command
    candidate_paths = [
        # Per-user installations include the Programs directory.
        Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Microsoft VS Code" / "Code.exe"
        if os.environ.get("LOCALAPPDATA")
        else None,
        # System-wide installations live directly under Program Files.
        Path(root) / "Microsoft VS Code" / "Code.exe"
        for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"))
        if root
    ]
    for candidate in filter(None, candidate_paths):
        if candidate.is_file():
            return str(candidate)"""
    return None


def resolve_accessible(path_text: str) -> Path:
    """Resolve a requested local path and reject inaccessible or invalid paths."""
    try:
        path = Path(path_text).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise HTTPException(status_code=400, detail="That path does not exist or cannot be accessed.") from None
    if is_non_viewable(path):
        raise HTTPException(status_code=403, detail="This system-critical path is not available in Cleanup Assistant.")
    return path


def entry_payload(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        is_dir = path.is_dir()
        return {
            "path": str(path),
            "name": path.name or str(path),
            "isDirectory": is_dir,
            "size": stat.st_size if not is_dir else None,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "protected": is_protected(path),
            "hidden": is_hidden(path),
        }
    except OSError:
        raise HTTPException(status_code=403, detail="This item cannot be read.") from None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/list")
def list_directory(path: str, include_hidden: bool = False, include_protected: bool = False) -> dict[str, Any]:
    directory = resolve_accessible(path)
    if not directory.is_dir():
        raise HTTPException(status_code=400, detail="Choose a folder to browse.")
    entries: list[dict[str, Any]] = []
    try:
        children = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
        for child in children:
            # Never expose critical Windows files, even when protected items are enabled.
            if is_non_viewable(child):
                continue
            if not include_hidden and is_hidden(child):
                continue
            if not include_protected and is_protected(child):
                continue
            entries.append(entry_payload(child))
    except OSError:
        raise HTTPException(status_code=403, detail="This folder cannot be read.") from None
    return {"path": str(directory), "entries": entries}


@app.get("/api/details")
def details(path: str) -> dict[str, Any]:
    item_path = resolve_accessible(path)
    root = item_path.parent if item_path.parent != item_path else item_path
    item = inspect_path(item_path, root)
    contents, contents_known = immediate_contents(item_path) if item.is_dir else ([], True)
    payload = entry_payload(item_path)
    cached_size = get_folder_size(item_path) if item.is_dir else None
    size_display = human_size(item.size_bytes)
    if item.is_dir:
        size_display = human_size(cached_size.bytes) if cached_size else "Calculating full folder size…"
    payload.update(
        {
            "kind": item.kind,
            "sizeDisplay": size_display,
            "contents": contents,
            "contentsKnown": contents_known,
            "assessment": removal_assessment(item),
        }
    )
    return payload


@app.get("/api/ai-analyze")
def ai_analyze(path: str) -> dict[str, Any]:
    """Analyze the selected filesystem item with the local Ollama model."""
    item_path = resolve_accessible(path)

    root = item_path.parent if item_path.parent != item_path else item_path
    item = inspect_path(item_path, root)

    try:
        return analyze_item(item)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.get("/api/folder-size")
def folder_size(path: str) -> dict[str, Any]:
    """Return a cached exact folder size or signal that calculation is underway."""
    folder = resolve_accessible(path)
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail="Folder size is only available for folders.")
    result = get_folder_size(folder)
    if result is None:
        return {"status": "calculating"}
    return {
        "status": "ready",
        "bytes": result.bytes,
        "display": human_size(result.bytes),
        "files": result.files,
        "folders": result.folders,
        "inaccessible": result.inaccessible,
    }


@app.post("/api/recycle")
def recycle(request: RecycleRequest) -> dict[str, str]:
    """Send one existing item to the OS Recycle Bin. Permanent removal is unsupported."""
    item = resolve_accessible(request.path)
    if item.parent == item:
        raise HTTPException(status_code=400, detail="A filesystem root cannot be recycled.")
    if is_protected(item):
        raise HTTPException(status_code=403,
                            detail="Protected technical and system folders cannot be recycled in this app.")
    try:
        send2trash(str(item))
    except OSError:
        raise HTTPException(status_code=500, detail="Windows could not move this item to the Recycle Bin.") from None
    return {"message": f"Moved {item.name} to the Recycle Bin."}


@app.post("/api/open-vscode")
def open_in_vscode(request: OpenRequest) -> dict[str, str]:
    """Launch a selected file in VS Code without modifying Windows defaults."""
    item = resolve_accessible(request.path)
    if item.is_dir():
        raise HTTPException(status_code=400, detail="Only files can be opened with VS Code.")
    vscode = find_vscode()
    if not vscode:
        raise HTTPException(status_code=404,
                            detail="VS Code was not found. Install it or add the 'code' command to PATH.")
    try:
        # Invoke Code directly rather than Windows' shell so associations remain untouched.
        subprocess.Popen([vscode, str(item)], close_fds=True)
    except OSError:
        raise HTTPException(status_code=500, detail="VS Code could not be started.") from None
    return {"message": f"Opened {item.name} in VS Code."}


def find_open_port(start_port: int = DEFAULT_PORT) -> int:
    """Return the first available loopback port at or above ``start_port``."""
    for port in range(start_port, 65536):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
        return port
    raise RuntimeError("No local TCP ports are available.")


def main() -> None:
    """Start the local web app without accepting command-line arguments."""
    port = DEFAULT_PORT
    while True:
        port = find_open_port(port)
        url = f"http://127.0.0.1:{port}"
        print(f"Cleanup Assistant is running at {url}")
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        try:
            server.run()
        except KeyboardInterrupt:
            print("\nCleanup Assistant stopped.")
            return
        if server.started:
            print("Cleanup Assistant stopped.")
            return
        print(f"Port {port} became unavailable; trying another local port.")
        port += 1
