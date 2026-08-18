from pathlib import Path

from cleanup_assistant.scanner import discover


def test_discover_excludes_protected_and_hidden_folders(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("x")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")
    (tmp_path / "visible").mkdir()
    (tmp_path / "visible" / "file.txt").write_text("x")

    paths = {item.relative_path.as_posix() for item in discover(tmp_path)}

    assert paths == {"keep.txt", "visible", "visible/file.txt"}
