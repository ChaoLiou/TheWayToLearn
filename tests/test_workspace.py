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


def test_publish_collects_only_shippable_files(tmp_path):
    import publish
    ws = tmp_path / "ws"
    (ws / "A vid" / "frames").mkdir(parents=True)
    (ws / "atlas.html").write_text("atlas")
    for name in ("plan.html", "lesson.mp3", "audio.mp3", "analysis.json"):
        (ws / "A vid" / name).write_text("x")
    (ws / "A vid" / "lesson_parts").mkdir()
    (ws / "A vid" / "lesson_parts" / "001.mp3").write_text("x")
    (ws / "A vid" / "frames" / "s01_1.jpg").write_text("x")
    (ws / "_overview.json").write_text("{}")
    dist = tmp_path / "dist"
    rels = {str(rel) for _, rel in publish.build(ws, dist)}
    assert rels == {"atlas.html", "index.html", "A vid/plan.html", "A vid/lesson.mp3", "A vid/frames/s01_1.jpg"}
    assert not (dist / "A vid" / "audio.mp3").exists()
    assert not (dist / "A vid" / "lesson_parts").exists()
