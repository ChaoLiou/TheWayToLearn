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
    site, _ = publish.build(ws, dist)
    rels = {str(rel) for _, rel in site}
    assert rels == {"atlas.html", "index.html", "A vid/plan.html", "A vid/lesson.mp3", "A vid/frames/s01_1.jpg"}
    assert not (dist / "A vid" / "audio.mp3").exists()
    assert not (dist / "A vid" / "lesson_parts").exists()


# ---------- gc：回收中間檔 ----------

def _prune_ws(tmp_path, narrated=True):
    import json
    ws = tmp_path / "ws"
    d = ws / "A vid"
    (d / "frames").mkdir(parents=True)
    (d / "lesson_parts").mkdir()
    (d / "lesson_parts" / "001_say_x.mp3").write_text("part")
    (d / ".tmp-abc").mkdir()
    (d / ".tmp-abc" / "junk").write_text("junk")
    (d / "meta.json").write_text(json.dumps({"video_id": "aaaaaaaaaaa", "title": "A vid"}))
    for n in ("audio.mp3", "subs.en.json3", "transcript.json", "analysis.json",
              "segments.json", "digest.json", "narration.json", "plan.html"):
        (d / n).write_text("x")
    (d / "frames" / "s01_1.jpg").write_text("img")
    if narrated:
        (d / "lesson.mp3").write_text("mp3")
        (d / "lesson.json").write_text("{}")
    return ws, d


def test_prune_lists_only_regenerable_files(tmp_path):
    import prune
    _, d = _prune_ws(tmp_path)
    got = {p.name: kind for p, kind in prune.reclaimable(d)}
    assert got == {"audio.mp3": "refetch", "subs.en.json3": "refetch",
                   ".tmp-abc": "refetch", "lesson_parts": "cache"}
    # LLM 產出、成品、截圖一律不動
    for keep in ("analysis.json", "segments.json", "digest.json", "narration.json",
                 "transcript.json", "plan.html", "lesson.mp3", "lesson.json", "frames"):
        assert keep not in got


def test_prune_keeps_audio_and_cache_until_narrated(tmp_path):
    """還沒產出 lesson.mp3 的站 = narrate 可能正在跑，audio.mp3 與快取都不能碰。"""
    import prune
    _, d = _prune_ws(tmp_path, narrated=False)
    got = {p.name: kind for p, kind in prune.reclaimable(d)}
    assert "audio.mp3" not in got and "lesson_parts" not in got
    assert got == {"subs.en.json3": "refetch", ".tmp-abc": "refetch"}


def test_prune_keep_cache_and_actual_delete(tmp_path):
    import prune
    ws, d = _prune_ws(tmp_path)
    assert {p.name for p, _ in prune.reclaimable(d, keep_cache=True)} == {
        "audio.mp3", "subs.en.json3", ".tmp-abc"}
    prune.main(["--workspace", str(ws)])                 # 只列出，不刪
    assert (d / "audio.mp3").exists() and (d / "lesson_parts").exists()
    prune.main(["--workspace", str(ws), "--delete"])
    assert not (d / "audio.mp3").exists() and not (d / "lesson_parts").exists()
    assert not (d / ".tmp-abc").exists() and not (d / "subs.en.json3").exists()
    # 成品全部還在
    for keep in ("lesson.mp3", "plan.html", "analysis.json", "frames/s01_1.jpg"):
        assert (d / keep).exists()
    prune.main(["--workspace", str(ws), "--delete"])     # 再跑一次不會爆
