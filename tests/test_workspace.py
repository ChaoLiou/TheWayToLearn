import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import pytest
from common import find_video_dir, video_dir


def test_video_dir_by_title_then_lookup_by_id(tmp_path):
    d = video_dir("abcdefghijk", tmp_path, title="My Video: Part 1")
    assert d.name == "My Video Part 1"
    (d / "meta.json").write_text(json.dumps({"video_id": "abcdefghijk"}))
    assert find_video_dir("abcdefghijk", tmp_path) == d
    assert video_dir("abcdefghijk", tmp_path) == d


def test_video_dir_unknown_without_title(tmp_path):
    with pytest.raises(FileNotFoundError):
        video_dir("zzzzzzzzzzz", tmp_path)


def test_workspace_and_override_resolution(tmp_path, monkeypatch):
    import importlib

    import common
    monkeypatch.setenv("LEARN_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setenv("LEARN_RULES", str(tmp_path / "ov"))
    importlib.reload(common)
    assert common.DEFAULT_WORKSPACE == (tmp_path / "ws").resolve()
    assert common.rule_file("narrative.md") == common.RULES / "narrative.md"
    (tmp_path / "ov").mkdir()
    (tmp_path / "ov" / "narrative.md").write_text("mine")
    assert common.rule_file("narrative.md") == (tmp_path / "ov" / "narrative.md").resolve()
    assert common.config_file("estimate.yaml") == common.CONFIG / "estimate.yaml"
    (tmp_path / "ov" / "templates").mkdir()
    assert len(common.template_dirs()) == 2
    monkeypatch.delenv("LEARN_WORKSPACE"); monkeypatch.delenv("LEARN_RULES")
    importlib.reload(common)
