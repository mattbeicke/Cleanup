"""Combine local filesystem evidence into a conservative removal recommendation."""

from __future__ import annotations

from pathlib import Path

from .explainer import explain
from .models import ItemInfo
from .scanner import is_protected


# ---------------------------------------------------------------------------
# Strong signals
# ---------------------------------------------------------------------------

# These are directories/files that are normally generated and disposable.
GENERATED_DIRECTORY_NAMES = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".next",
    ".nuxt",
    ".turbo",
    ".parcel-cache",
    "coverage",
    "shadercache",
    "shader cache",
})

GENERATED_EXTENSIONS = frozenset({
    ".tmp",
    ".temp",
    ".log",
    ".dmp",
    ".mdmp",
    ".etl",
    ".wer",
})

CACHE_PATH_PARTS = frozenset({
    "cache",
    "caches",
    "cached",
    "temp",
    "tmp",
    "temporary",
    "prefetch",
    "shadercache",
})


# ---------------------------------------------------------------------------
# Things that should make us conservative
# ---------------------------------------------------------------------------

USER_DATA_DIRECTORIES = frozenset({
    "desktop",
    "documents",
    "downloads",
    "pictures",
    "videos",
    "music",
    "saved games",
})

IMPORTANT_EXTENSIONS = frozenset({
    # Documents/data
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".pdf",
    ".txt",
    ".csv",

    # Databases
    ".db",
    ".sqlite",
    ".sqlite3",
    ".mdb",
    ".accdb",

    # Projects/source
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".fs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".sql",
    ".sln",
    ".csproj",
    ".fsproj",
    ".vcxproj",

    # Configuration
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".config",
    ".env",
    ".xml",

    # Security
    ".key",
    ".pem",
    ".pfx",
    ".p12",

    # User media
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
    ".mp3",
    ".wav",
    ".flac",
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
})

INSTALLER_EXTENSIONS = frozenset({
    ".exe",
    ".msi",
    ".msix",
    ".appx",
})

ARCHIVE_EXTENSIONS = frozenset({
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".iso",
})

SYSTEM_NAMES = frozenset({
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "system32",
    "syswow64",
    "systemapps",
    "$recycle.bin",
    "system volume information",
})

BACKUP_WORDS = frozenset({
    "backup",
    "backups",
    "bak",
    "old",
    "archive",
    "archives",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _path_parts(path: Path) -> set[str]:
    """Return case-insensitive path components."""
    return {part.casefold() for part in path.parts}


def _has_cache_path(path: Path) -> bool:
    """Check whether the item lives in an obviously cache/temp location."""
    parts = _path_parts(path)

    if parts & CACHE_PATH_PARTS:
        return True

    text = str(path).casefold().replace("/", "\\")

    return (
        "\\cache\\" in text
        or "\\caches\\" in text
        or "\\temp\\" in text
        or "\\tmp\\" in text
        or "\\prefetch\\" in text
    )


def _is_user_data_location(path: Path) -> bool:
    """Determine whether the item is underneath an obvious user-data folder."""
    parts = _path_parts(path)
    return bool(parts & USER_DATA_DIRECTORIES)


def _has_backup_name(path: Path) -> bool:
    """Detect filenames suggesting backups or older copies."""
    name = path.name.casefold()

    if name in BACKUP_WORDS:
        return True

    stem = path.stem.casefold()

    return any(
        stem.endswith(f"_{word}")
        or stem.endswith(f"-{word}")
        or stem.endswith(f" {word}")
        or stem.startswith(f"{word}_")
        or stem.startswith(f"{word}-")
        for word in BACKUP_WORDS
    )


def _is_project_directory(item: ItemInfo) -> bool:
    """Detect directories that appear to be development projects."""
    if not item.is_dir:
        return False

    names = {entry.casefold() for entry in item.sample}

    project_markers = {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
        "cargo.toml",
        "pom.xml",
        "build.gradle",
        "settings.gradle",
        "dockerfile",
    }

    if names & project_markers:
        return True

    return any(
        name.endswith((".sln", ".csproj", ".fsproj", ".vcxproj"))
        for name in names
    )


# ---------------------------------------------------------------------------
# Main assessment
# ---------------------------------------------------------------------------

def removal_assessment(item: ItemInfo) -> dict[str, str]:
    """
    Produce a conservative local recommendation.

    The local rules deliberately favor false negatives over false positives:
    if the program cannot establish that something is disposable, it asks the
    user to review it rather than recommending deletion.
    """

    explanation = explain(item)
    name = item.path.name.casefold()
    suffix = item.path.suffix.casefold()
    parts = _path_parts(item.path)

    # -----------------------------------------------------------------------
    # Absolute "do not remove" cases
    # -----------------------------------------------------------------------

    if is_protected(item.path):
        return {
            "summary": explanation,
            "recommendation": "Do not remove",
            "reason": (
                "This item is in a protected system, source-control, IDE, "
                "development, or environment directory."
            ),
            "source": "Local rules (offline)",
        }

    if name in SYSTEM_NAMES or parts & SYSTEM_NAMES:
        return {
            "summary": explanation,
            "recommendation": "Do not remove",
            "reason": (
                "This item is associated with a Windows/system location. "
                "The local rules will not recommend deleting system data."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Strong generated/cache/temp signals
    # -----------------------------------------------------------------------

    if name in GENERATED_DIRECTORY_NAMES:
        return {
            "summary": explanation,
            "recommendation": "Likely removable",
            "reason": (
                "This directory is normally generated automatically by an "
                "application or development tool and can generally be "
                "recreated. Close the associated application first."
            ),
            "source": "Local rules (offline)",
        }

    if _has_cache_path(item.path):
        # Don't blindly recommend things inside a cache-looking path if they
        # are clearly user data or important configuration.
        if suffix in IMPORTANT_EXTENSIONS and not item.is_dir:
            return {
                "summary": explanation,
                "recommendation": "Review before removing",
                "reason": (
                    "The location resembles a cache or temporary directory, "
                    "but the file type may contain configuration or user data. "
                    "The AI analyzer can inspect this item further."
                ),
                "source": "Local rules (offline)",
            }

        return {
            "summary": explanation,
            "recommendation": "Likely removable",
            "reason": (
                "The item is located in a cache or temporary-data location. "
                "Such data is commonly regenerated. Close the associated "
                "application before removing it."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Logs and diagnostic files
    # -----------------------------------------------------------------------

    if suffix in {".log", ".etl", ".wer"}:
        return {
            "summary": explanation,
            "recommendation": "Likely removable",
            "reason": (
                "This is diagnostic/logging data rather than a normal user "
                "document. It can usually be removed once it is no longer "
                "needed for troubleshooting."
            ),
            "source": "Local rules (offline)",
        }

    if suffix in {".dmp", ".mdmp"}:
        return {
            "summary": explanation,
            "recommendation": "Likely removable",
            "reason": (
                "This appears to be a crash dump. It is useful for debugging "
                "but is not normally required for everyday operation."
            ),
            "source": "Local rules (offline)",
        }

    if suffix in {".tmp", ".temp"}:
        return {
            "summary": explanation,
            "recommendation": "Likely removable",
            "reason": (
                "Temporary files are normally generated for short-term use. "
                "The associated application should be closed before removal."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Special Windows-generated files
    # -----------------------------------------------------------------------

    if name in {"desktop.ini", "thumbs.db", "ehthumbs.db", ".ds_store"}:
        return {
            "summary": explanation,
            "recommendation": "Likely removable",
            "reason": (
                "This is metadata/cache generated by an operating system or "
                "file browser and can normally be regenerated."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Development projects
    # -----------------------------------------------------------------------

    if _is_project_directory(item):
        return {
            "summary": explanation,
            "recommendation": "Do not remove",
            "reason": (
                "This appears to be an active development project. The "
                "directory may contain source code, project configuration, "
                "or other files that cannot safely be regenerated."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # User data
    # -----------------------------------------------------------------------

    if _is_user_data_location(item.path):
        if _has_backup_name(item.path):
            return {
                "summary": explanation,
                "recommendation": "Review before removing",
                "reason": (
                    "This item appears to be in a user-data location and its "
                    "name suggests it may be a backup or older copy. It could "
                    "contain the only remaining copy of important data."
                ),
                "source": "Local rules (offline)",
            }

        return {
            "summary": explanation,
            "recommendation": "Review before removing",
            "reason": (
                "This item is located in a directory commonly used for "
                "user-created or downloaded data. The local rules will not "
                "assume that it is disposable."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Databases
    # -----------------------------------------------------------------------

    if suffix in {".db", ".sqlite", ".sqlite3", ".mdb", ".accdb"}:
        return {
            "summary": explanation,
            "recommendation": "Review before removing",
            "reason": (
                "Database files can contain application state or irreplaceable "
                "user data. The database owner should be identified before "
                "removal."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Backups
    # -----------------------------------------------------------------------

    if _has_backup_name(item.path) or suffix == ".bak":
        return {
            "summary": explanation,
            "recommendation": "Review before removing",
            "reason": (
                "This appears to be a backup, archive, or older copy. It may "
                "be safe to remove if another copy exists, but the local rules "
                "cannot establish that."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Installers and archives
    # -----------------------------------------------------------------------

    if suffix in INSTALLER_EXTENSIONS:
        return {
            "summary": explanation,
            "recommendation": "Review before removing",
            "reason": (
                "This appears to be an installer. It is usually safe to remove "
                "after the software is installed if you do not need the "
                "installer again, but it may still be useful for reinstalling."
            ),
            "source": "Local rules (offline)",
        }

    if suffix in ARCHIVE_EXTENSIONS:
        return {
            "summary": explanation,
            "recommendation": "Review before removing",
            "reason": (
                "Archives may contain backups, installers, software, or "
                "personal files. The extension alone is not enough to safely "
                "recommend deletion."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Executables / libraries / scripts
    # -----------------------------------------------------------------------

    if suffix in {".dll", ".sys"}:
        return {
            "summary": explanation,
            "recommendation": "Do not remove",
            "reason": (
                "This is a system/library component. Removing it individually "
                "could break the application or Windows component that uses it."
            ),
            "source": "Local rules (offline)",
        }

    if suffix in {".exe", ".bat", ".cmd", ".ps1", ".com"}:
        return {
            "summary": explanation,
            "recommendation": "Review before removing",
            "reason": (
                "This file can be executed by Windows. It may be an installed "
                "program, updater, installer, or user-created script, so its "
                "purpose should be established first."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Configuration / security files
    # -----------------------------------------------------------------------

    if suffix in {
        ".json",
        ".jsonc",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".config",
        ".env",
        ".xml",
        ".key",
        ".pem",
        ".pfx",
        ".p12",
    }:
        return {
            "summary": explanation,
            "recommendation": "Review before removing",
            "reason": (
                "This appears to be configuration, environment, or security "
                "data. It may be required by an application or project."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Source code
    # -----------------------------------------------------------------------

    if suffix in {
        ".py",
        ".pyw",
        ".pyi",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".java",
        ".kt",
        ".kts",
        ".c",
        ".h",
        ".cpp",
        ".cc",
        ".cxx",
        ".hpp",
        ".cs",
        ".csx",
        ".fs",
        ".fsx",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".lua",
        ".sh",
        ".sql",
    }:
        return {
            "summary": explanation,
            "recommendation": "Do not remove",
            "reason": (
                "This appears to be source code. Source files are normally "
                "not disposable generated data."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Media and documents
    # -----------------------------------------------------------------------

    if suffix in {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".svg",
        ".tif",
        ".tiff",
        ".mp3",
        ".wav",
        ".flac",
        ".ogg",
        ".m4a",
        ".aac",
        ".opus",
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".webm",
        ".m4v",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".pdf",
        ".txt",
        ".csv",
        ".md",
        ".rtf",
        ".epub",
    }:
        return {
            "summary": explanation,
            "recommendation": "Review before removing",
            "reason": (
                "This appears to be user-readable content or media. The "
                "extension does not provide enough evidence that it is "
                "disposable."
            ),
            "source": "Local rules (offline)",
        }

    # -----------------------------------------------------------------------
    # Final fallback
    # -----------------------------------------------------------------------

    return {
        "summary": explanation,
        "recommendation": "Review before removing",
        "reason": (
            "The local rules could not establish that this item is disposable. "
            "Use the AI analysis for a more detailed identification."
        ),
        "source": "Local rules (offline)",
    }