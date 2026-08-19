"""Safe filesystem discovery for cleanup reviews."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from .models import ItemInfo

PROTECTED_NAMES = frozenset({
    ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__", ".venv", "venv",
    "node_modules", "windows", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information",
})
NON_VIEWABLE_NAMES = frozenset({"pagefile.sys", "hiberfil.sys", "swapfile.sys", "memory.dmp"})


def is_hidden(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if os.name == "nt":
        try:
            return bool(path.stat().st_file_attributes & 2)  # FILE_ATTRIBUTE_HIDDEN
        except OSError:
            return False
    return False


def is_protected(path: Path) -> bool:
    return path.name.casefold() in PROTECTED_NAMES


def is_non_viewable(path: Path) -> bool:
    """Return whether a path is too critical to expose in the cleanup UI.

    These exclusions are stronger than normal protection: a user can opt into
    seeing protected application folders, but never Windows' own directory or
    paging/hibernation files that are required by the operating system.
    """
    if path.name.casefold() in NON_VIEWABLE_NAMES:
        return True
    system_root = Path(os.environ.get("SystemRoot", r"C:\\Windows"))
    try:
        candidate_text = str(path.resolve(strict=False)).casefold().rstrip("\\/")
        root_text = str(system_root.resolve(strict=False)).casefold().rstrip("\\/")
    except OSError:
        return False
    return candidate_text == root_text or candidate_text.startswith(f"{root_text}\\")


def _info(path: Path, root: Path) -> ItemInfo:
    try:
        stat = path.stat()
        size = stat.st_size if path.is_file() else 0
        sample = tuple(child.name for child in list(path.iterdir())[:5]) if path.is_dir() else ()
        return ItemInfo(path, path.relative_to(root), path.is_dir(), size, stat.st_mtime, sample)
    except OSError:
        return ItemInfo(path, path.relative_to(root), path.is_dir(), 0, 0, ())


def inspect_path(path: Path, root: Path) -> ItemInfo:
    """Return display information for one accessible path."""
    return _info(path, root)


def discover(
    root: Path,
    *,
    include_hidden: bool = False,
    include_protected: bool = False,
    excluded_paths: set[Path] | None = None,
) -> Iterator[ItemInfo]:
    """Yield reviewable entries, shallowest first, without following symlinks."""
    root = root.resolve()
    excluded = {path.resolve() for path in (excluded_paths or set())}
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(
            d for d in dirs
            if (include_hidden or not is_hidden(current_path / d))
            and (include_protected or not is_protected(current_path / d))
        )
        visible_files = sorted(
            f for f in files
            if (include_hidden or not is_hidden(current_path / f))
            and (include_protected or not is_protected(current_path / f))
            and (current_path / f).resolve() not in excluded
        )
        for name in dirs:
            yield _info(current_path / name, root)
        for name in visible_files:
            yield _info(current_path / name, root)
