# Cleanup Assistant

Cleanup Assistant is a local web app for reviewing files and folders. It opens a browser-based file explorer: select an item on the left to see its stats, contents, plain-English explanation, and removal assessment on the right.

It is deliberately conservative:

- It ignores protected metadata and system-style directories by default (`.git`, virtual environments, `node_modules`, Windows system folders, and more).
- It is only served on your computer (`127.0.0.1`) at port `8765`, then tries the next port only if that one is occupied.
- Every removal goes through Windows' Recycle Bin via `Send2Trash`. The app contains no permanent-delete action.

## Install

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Use

```powershell
cleanup-assistant
```

The app prints its local URL and starts at your home folder when you open it in a browser. Enter or paste a different folder into **Current folder** to browse it; double-click a folder in the explorer to open it. Hidden items are shown by default; toggle protected technical items only when you specifically need to inspect them.

To remove an item, select it and choose **Move to Recycle Bin**. The app asks for confirmation and does not offer permanent deletion.

The assessment is currently an offline, rule-based explanation. Its source is shown in the interface so it never claims to have checked an AI service or the internet when it has not. This is deliberately ready for a future optional AI/internet provider.

Folder sizes are calculated exactly in the background and cached for the current session. This keeps browsing responsive; unlike disk-indexing tools such as WizTree, the app does not parse the Windows NTFS index, so the first calculation for a very large folder can take time.

## Development

```powershell
pip install -e .[dev]
python -m pytest
```

The code lives in `src/cleanup_assistant`; the web server is `web.py`, UI files are in `static`, and tests live in `tests`.
