from pathlib import Path

from api.scanner import discover, is_non_viewable


def test_discover_excludes_protected_and_hidden_folders(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("x")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")
    (tmp_path / "visible").mkdir()
    (tmp_path / "visible" / "file.txt").write_text("x")

    paths = {item.relative_path.as_posix() for item in discover(tmp_path)}

    assert paths == {"keep.txt", "visible", "visible/file.txt"}


def test_non_viewable_system_files_are_always_identified() -> None:
    """Paging and hibernation files must stay out of the review experience."""
    assert is_non_viewable(Path("pagefile.sys"))
    assert is_non_viewable(Path("hiberfil.sys"))
