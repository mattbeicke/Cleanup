"""Interactive command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from send2trash import send2trash

from .explainer import explain, human_size
from .models import ItemInfo
from .scanner import discover
from .state import load, save


def display(item: ItemInfo) -> None:
    print(f"\n{'Folder' if item.is_dir else 'File'}: {item.relative_path}")
    print("Size: not calculated for folders (keeps large scans responsive)." if item.is_dir else f"Size: {human_size(item.size_bytes)}")
    if item.sample:
        print(f"Contains: {', '.join(item.sample)}")
    print(f"What it looks like: {explain(item)}")


def apply_proposals(root: Path, decisions: dict[str, str]) -> int:
    """Recycle decisions made during a previous preview run."""
    proposed = [key for key, value in decisions.items() if value == "delete-proposed"]
    # Recycle parent folders before descendants, which prevents duplicate attempts.
    proposed.sort(key=lambda key: (len(Path(key).parts), key))
    recycled = 0
    recycled_parents: list[Path] = []
    for key in proposed:
        candidate = (root / key).resolve()
        if root not in candidate.parents or not candidate.exists():
            continue
        if any(parent in candidate.parents for parent in recycled_parents):
            decisions[key] = "recycled-with-parent"
            continue
        try:
            send2trash(str(candidate))
            decisions[key] = "recycled"
            recycled_parents.append(candidate)
            recycled += 1
            print(f"Moved previously selected item to the Recycle Bin: {key}")
        except OSError as error:
            print(f"Could not move '{key}' to the Recycle Bin: {error}")
    return recycled


def review(root: Path, state_path: Path, *, apply: bool, include_hidden: bool, include_protected: bool) -> int:
    decisions = load(state_path)
    removed = apply_proposals(root, decisions) if apply else 0
    save(state_path, decisions)
    reviewed = 0
    for item in discover(
        root,
        include_hidden=include_hidden,
        include_protected=include_protected,
        excluded_paths={state_path},
    ):
        key = item.relative_path.as_posix()
        if key in decisions:
            continue
        reviewed += 1
        while True:
            display(item)
            choice = input("[k]eep, [d]elete, [s]kip, [i]nfo, [q]uit: ").strip().lower()
            if choice in {"k", "keep"}:
                decisions[key] = "keep"
                save(state_path, decisions)
                break
            if choice in {"s", "skip"}:
                print("Skipped without recording a decision; it will be shown again next time.")
                break
            if choice in {"i", "info"}:
                continue
            if choice in {"q", "quit"}:
                save(state_path, decisions)
                print(f"Saved {reviewed} decisions to {state_path}.")
                return 0
            if choice in {"d", "delete"}:
                if apply:
                    try:
                        send2trash(str(item.path))
                        decisions[key] = "recycled"
                        removed += 1
                        print("Moved to the Recycle Bin.")
                    except OSError as error:
                        print(f"Could not move item to the Recycle Bin: {error}")
                        continue
                else:
                    decisions[key] = "delete-proposed"
                    print("Proposed for removal. Run again with --apply to move selected items to the Recycle Bin.")
                save(state_path, decisions)
                break
            print("Choose k, d, s, i, or q.")
    print(f"Review complete: {reviewed} new item(s) reviewed; {removed} item(s) recycled.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely review files and folders one at a time.")
    parser.add_argument("target", type=Path, help="Folder to review")
    parser.add_argument("--state", type=Path, help="Decision file (default: cleanup-decisions.json beside target)")
    parser.add_argument("--apply", action="store_true", help="Move chosen items to the Recycle Bin instead of only recording a proposal")
    parser.add_argument("--include-hidden", action="store_true", help="Review hidden items")
    parser.add_argument("--include-protected", action="store_true", help="Review technical/system-like directories normally excluded")
    parser.add_argument("--reset", action="store_true", help="Discard stored decisions and start a new review")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.target.expanduser()
    if not root.is_dir():
        print(f"Error: '{root}' is not an accessible folder.")
        return 2
    root = root.resolve()
    state_path = args.state or root / "cleanup-decisions.json"
    if args.reset and state_path.exists():
        state_path.unlink()
    print(f"Reviewing: {root}")
    print("Protected technical and system folders are excluded by default. No files are removed unless --apply is used.")
    return review(root, state_path, apply=args.apply, include_hidden=args.include_hidden, include_protected=args.include_protected)
