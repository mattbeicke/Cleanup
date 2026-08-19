from pathlib import Path

from cleanup_assistant.api.assessment import removal_assessment
from cleanup_assistant.api.models import ItemInfo


def test_temporary_file_is_likely_removable() -> None:
    item = ItemInfo(Path("work.tmp"), Path("work.tmp"), False, 1, 0)

    assert removal_assessment(item)["recommendation"] == "Likely removable"


def test_source_control_folder_is_not_removable() -> None:
    item = ItemInfo(Path(".git"), Path(".git"), True, 0, 0)

    assert removal_assessment(item)["recommendation"] == "Do not remove"
