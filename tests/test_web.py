from pathlib import Path

from api.web import (
    DEFAULT_PORT,
    OpenRequest,
    RecycleRequest,
    calculate_folder_size,
    find_open_port,
    open_in_vscode,
    recycle,
)


def test_recycle_uses_send2trash_only(tmp_path: Path, monkeypatch) -> None:
    """Recycling must delegate solely to Send2Trash."""
    item = tmp_path / "remove-me.txt"
    item.write_text("temporary")
    recycled: list[str] = []
    monkeypatch.setattr("cleanup_assistant.web.send2trash", recycled.append)

    result = recycle(RecycleRequest(path=str(item)))

    assert recycled == [str(item.resolve())]
    assert "Recycle Bin" in result["message"]


def test_find_open_port_uses_requested_starting_port() -> None:
    """The predictable default port is preferred when it is free."""
    assert find_open_port(DEFAULT_PORT) >= DEFAULT_PORT


def test_calculate_folder_size_counts_nested_files(tmp_path: Path) -> None:
    """Folder-size scans include every readable nested regular file."""
    (tmp_path / "small.txt").write_bytes(b"abc")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "large.txt").write_bytes(b"12345")

    size = calculate_folder_size(tmp_path)

    assert size.bytes == 8
    assert size.files == 2
    assert size.folders == 1


def test_open_in_vscode_starts_code_without_shell_association(tmp_path: Path, monkeypatch) -> None:
    """Opening a file invokes VS Code directly rather than changing file defaults."""
    item = tmp_path / "readme.txt"
    item.write_text("notes")
    launched: list[list[str]] = []
    monkeypatch.setattr("cleanup_assistant.web.find_vscode", lambda: "C:/VSCode/Code.exe")
    monkeypatch.setattr("cleanup_assistant.web.subprocess.Popen", lambda command, **_: launched.append(command))

    result = open_in_vscode(OpenRequest(path=str(item)))

    assert launched == [["C:/VSCode/Code.exe", str(item.resolve())]]
    assert result["message"] == "Opened readme.txt in VS Code."
