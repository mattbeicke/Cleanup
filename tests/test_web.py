from pathlib import Path

from cleanup_assistant.web import RecycleRequest, recycle


def test_recycle_uses_send2trash_only(tmp_path: Path, monkeypatch) -> None:
    item = tmp_path / "remove-me.txt"
    item.write_text("temporary")
    recycled: list[str] = []
    monkeypatch.setattr("cleanup_assistant.web.send2trash", recycled.append)

    result = recycle(RecycleRequest(path=str(item)))

    assert recycled == [str(item.resolve())]
    assert "Recycle Bin" in result["message"]
