from pathlib import Path

from cleanup_assistant.explainer import explain, human_size
from cleanup_assistant.models import ItemInfo


def test_cache_folder_explanation_is_actionable() -> None:
    item = ItemInfo(Path("cache"), Path("cache"), True, 0, 0, ())
    assert "cached" in explain(item).lower()


def test_size_formatting() -> None:
    assert human_size(1536) == "1.5 KB"


def test_folder_markers_identify_python_project() -> None:
    item = ItemInfo(Path("project"), Path("project"), True, 0, 0, ("pyproject.toml", "src"))
    assert "python project" in explain(item).lower()
