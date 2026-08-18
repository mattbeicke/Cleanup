"""Local-only web interface for Cleanup Assistant."""

from __future__ import annotations

import socket
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from send2trash import send2trash

from .assessment import removal_assessment
from .explainer import human_size
from .scanner import inspect_path, is_hidden, is_protected

STATIC_DIR = Path(__file__).parent / "static"
app = FastAPI(title="Cleanup Assistant", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RecycleRequest(BaseModel):
    path: str


def resolve_accessible(path_text: str) -> Path:
    """Resolve a requested local path and reject inaccessible or invalid paths."""
    try:
        path = Path(path_text).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise HTTPException(status_code=400, detail="That path does not exist or cannot be accessed.") from None
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
    payload = entry_payload(item_path)
    payload.update(
        {
            "kind": item.kind,
            "sizeDisplay": "Folder size is not calculated during browsing." if item.is_dir else human_size(item.size_bytes),
            "contents": list(item.sample),
            "assessment": removal_assessment(item),
        }
    )
    return payload


@app.post("/api/recycle")
def recycle(request: RecycleRequest) -> dict[str, str]:
    """Send one existing item to the OS Recycle Bin. Permanent removal is unsupported."""
    item = resolve_accessible(request.path)
    if item.parent == item:
        raise HTTPException(status_code=400, detail="A filesystem root cannot be recycled.")
    if is_protected(item):
        raise HTTPException(status_code=403, detail="Protected technical and system folders cannot be recycled in this app.")
    try:
        send2trash(str(item))
    except OSError:
        raise HTTPException(status_code=500, detail="Windows could not move this item to the Recycle Bin.") from None
    return {"message": f"Moved {item.name} to the Recycle Bin."}


def find_open_port() -> int:
    """Ask the OS for an available loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def main() -> None:
    """Start the local web app without accepting command-line arguments."""
    while True:
        port = find_open_port()
        url = f"http://127.0.0.1:{port}"
        print(f"Cleanup Assistant is running at {url}")
        webbrowser.open(url)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        server.run()
        if server.started:
            return
        print(f"Port {port} became unavailable; trying another local port.")
