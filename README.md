# Cleanup Assistant

Cleanup Assistant is a local web app for reviewing files and folders. It opens a browser-based file explorer: select an item on the left to see its stats, contents, plain-English explanation, and removal assessment on the right.

It is deliberately conservative:

- It ignores protected metadata and system-style directories by default (`.git`, virtual environments, `node_modules`, Windows system folders, and more).
- It is only served on your computer (`127.0.0.1`) and chooses a free local port automatically.
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

The app opens your browser and starts at your home folder. Enter or paste a different folder into **Start folder** to browse it; double-click a folder in the explorer to open it. Toggle hidden or protected technical items only when you specifically need to inspect them.

To remove an item, select it and choose **Move to Recycle Bin**. The app asks for confirmation and does not offer permanent deletion.

The assessment is currently an offline, rule-based explanation. Its source is shown in the interface so it never claims to have checked an AI service or the internet when it has not. This is deliberately ready for a future optional AI/internet provider.

## Development

```powershell
pip install -e .[dev]
python -m pytest
```

The code lives in `src/cleanup_assistant`; the web server is `web.py`, UI files are in `static`, and tests live in `tests`.
