# Cleanup Assistant

Cleanup Assistant is a local, interactive command-line app that walks through a folder and asks whether each non-essential file or folder should be kept, skipped, or removed. For every item it gives a plain-English explanation based on its name, location, size, age, and a small content listing.

It is deliberately conservative:

- It ignores protected metadata and system-style directories by default (`.git`, virtual environments, `node_modules`, Windows system folders, and more).
- It does **not** delete anything by default. Decisions are recorded in a JSON file so a review can be resumed.
- With `--apply`, removals go to the Recycle Bin via `Send2Trash`, not permanent deletion.

## Install

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Use

Preview a directory (nothing is removed):

```powershell
cleanup-assistant "C:\Users\you\Downloads"
```

Apply removals by sending them to the Recycle Bin:

```powershell
cleanup-assistant "C:\Users\you\Downloads" --apply
```

Useful options:

```text
--state PATH        Where to save review decisions (default: cleanup-decisions.json beside the target)
--include-hidden    Include hidden files and directories in the review
--include-protected Include normally protected technical folders (use with care)
--reset             Forget previous decisions for this target and start over
```

During review: `k` keeps an item, `d` marks it for removal, `s` leaves it undecided (so it will appear again next time), `i` repeats detailed information, and `q` exits safely. In preview mode, `d` records a proposed removal; the next run with `--apply` moves all previously proposed items to the Recycle Bin.

## Development

```powershell
pip install -e .[dev]
python -m pytest
```

The code lives in `src/cleanup_assistant`; tests live in `tests`.
