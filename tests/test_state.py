from pathlib import Path

from cleanup_assistant.api.state import load, save


def test_decisions_round_trip(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    decisions = {"old.zip": "delete-proposed", "notes.txt": "keep"}

    save(state_path, decisions)

    assert load(state_path) == decisions
