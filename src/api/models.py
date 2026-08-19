"""Small, dependency-free data structures used by the application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ItemInfo:
    path: Path
    relative_path: Path
    is_dir: bool
    size_bytes: int
    modified_timestamp: float
    sample: tuple[str, ...] = ()

    @property
    def kind(self) -> str:
        return "folder" if self.is_dir else "file"
