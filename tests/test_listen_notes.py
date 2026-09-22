import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import listen
import notes
import publish
import validate

FX = Path(__file__).parent / "fixtures/ws"

LESSON = {
    "video_id": "zzzzzzzzzzz", "voice": "v", "rate": "+0%", "duration": 20.0, "file": "lesson.mp3",
    "created": "2026-01-02T00:00:00+00:00",
    "chapters": [{"seg_id": 1, "title": "一", "at": 0.0}, {"seg_id": 2, "title": "二", "at": 10.0}],
    "timeline": [
        {"i": 1, "at": 0.0, "dur": 10.0, "kind": "say", "seg_id": 1, "seg_title": "一", "text": "a b", "label": "",
         "lines": [{"at": 0.0, "dur": 5.0, "text": "a"}, {"at": 5.0, "dur": 5.0, "text": "b"}], "translation": ""},
        {"i": 2, "at": 10.0, "dur": 10.0, "kind": "clip", "seg_id": 2, "seg_title": "二", "text": "", "label": "原聲",
         "lines": [{"at": 10.0, "dur": 10.0, "text": "hello"}], "translation": "哈囉"},
    ],
    "dub": {"file": "lesson.dub.mp3", "voice": "d", "duration": 18.0,
            "chapters": [{"seg_id": 1, "title": "一", "at": 0.0}, {"seg_id": 2, "title": "二", "at": 10.0}],
            "timeline": [
                {"i": 1, "at": 0.0, "dur": 10.0, "kind": "say", "seg_id": 1, "seg_title": "一", "text": "a b", "label": "",
                 "lines": [{"at": 0.0, "dur": 5.0, "text": "a"}, {"at": 5.0, "dur": 5.0, "text": "b"}]},
                {"i": 2, "at": 10.0, "dur": 8.0, "kind": "dub", "seg_id": 2, "seg_title": "二", "text": "哈囉", "label": "原聲",
                 "lines": [{"at": 10.0, "dur": 8.0, "text": "哈囉"}], "orig_text": "hello"},
            ]},
}

NOTES = {"video_id": "zzzzzzzzzzz", "created": "2026-01-03T00:00:00+00:00", "notes": [
    {"id": 1, "seg_id": 1, "kind": "concept", "text": "第一條筆記內容", "terms": ["X"]},
    {"id": 2, "seg_id": 3, "kind": "skill", "text": "第二條筆記內容", "detail": "怎麼做"},
]}


def _ws(tmp_path, with_lesson=True, with_notes=True):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    d = ws / "測試影片 C"
    if with_lesson:
        (d / "lesson.json").write_text(json.dumps(LESSON, ensure_ascii=False))
        (d / "lesson.mp3").write_bytes(b"x")
        (d / "lesson.dub.mp3").write_bytes(b"x")
    if with_notes:
        (d / "notes.json").write_text(json.dumps(NOTES, ensure_ascii=False))
    return ws, d


# ---------- listen ----------

def test_captions_slim_keeps_blocks_and_labels():
    cap = listen.captions(LESSON)
    assert [ln["t"] for ln in cap["o"]] == ["a", "b", "hello"]
    assert [ln["k"] for ln in cap["o"]] == ["s", "s", "c"]
    assert cap["o"][2]["l"] == "原聲" and "l" not in cap["o"][0]
    assert cap["ob"] == [[0.0, 10.0], [10.0, 10.0]]
    assert cap["d"][2]["k"] == "d" and cap["db"][1] == [10.0, 8.0]
    assert cap["segs"] == {"1": "一", "2": "二"}
    assert cap["ch"][1] == [10.0, "二", 2]


def test_listen_lists_only_stations_with_audio_newest_first(tmp_path):
    ws, d = _ws(tmp_path)
    # 第二站：沒有 created，靠 mtime；設成更早
    a = ws / "測試影片 A: B"
    (a / "lesson.json").write_text(json.dumps(dict(LESSON, video_id="abcdefghijk", created=None, dub=None), ensure_ascii=False))
    (a / "lesson.mp3").write_bytes(b"x")
    import os
    os.utime(a / "lesson.mp3", (0, 0))
    eps = listen.load_episodes(ws)
    assert [e["id"] for e in eps] == ["zzzzzzzzzzz", "abcdefghijk"]
    assert eps[0]["dub"] and eps[0]["dub_duration"] == 18.0 and eps[1]["dub"] is None
    assert eps[0]["has_notes"] is True
    # captions.js 有寫出來，而且是可以直接 <script> 載的
    js = (d / "captions.js").read_text()
    assert js.startswith("window.__cap=window.__cap||{};window.__cap[\"zzzzzzzzzzz\"]=")


def test_listen_render(tmp_path):
    ws, _ = _ws(tmp_path)
    out = listen.render(ws)
    html = out.read_text()
    assert 'id="ep-zzzzzzzzzzz"' in html and "captions.js" in html
    # 分類來自 atlas.json 的 region；搜尋列跟 atlas.html 同一份 macro
    eps = listen.load_episodes(ws)
    assert eps[0]["category"] == "A 與 B"
    assert 'data-category="A 與 B"' in html and 'id="sinput"' in html
    assert "cdn.jsdelivr" not in html            # 離線也要能開
    assert "notes.html#zzzzzzzzzzz" not in html   # notes.html 還沒產出就不連
    notes.render(ws)
    html = listen.render(ws).read_text()
    assert "notes.html#zzzzzzzzzzz" in html


def test_listen_empty_workspace(tmp_path):
    ws, _ = _ws(tmp_path, with_lesson=False)
    html = listen.render(ws).read_text()
    assert "learn-narrate" in html


# ---------- notes ----------

def test_notes_schema_and_seg_check(tmp_path):
    _, d = _ws(tmp_path)
    assert validate.validate("notes", d / "notes.json") == []
    bad = dict(NOTES, notes=[dict(NOTES["notes"][0], seg_id=99), dict(NOTES["notes"][0], text="x" * 81)])
    (d / "notes.json").write_text(json.dumps(bad, ensure_ascii=False))
    errs = validate.validate("notes", d / "notes.json")
    assert any("too long" in e for e in errs)
    bad = dict(NOTES, notes=[dict(NOTES["notes"][0], seg_id=99), dict(NOTES["notes"][0], id=1)])
    (d / "notes.json").write_text(json.dumps(bad, ensure_ascii=False))
    errs = validate.validate("notes", d / "notes.json")
    assert any("seg_id 99" in e for e in errs) and any("id 重複" in e for e in errs)


def test_notes_render_links_back_and_applies_keep(tmp_path):
    ws, _ = _ws(tmp_path)
    (ws / "notes.keep.json").write_text(json.dumps({"zzzzzzzzzzz:1": "keep", "zzzzzzzzzzz:2": "bogus"}))
    st = notes.load_stations(ws)
    assert [s["id"] for s in st] == ["zzzzzzzzzzz"]
    n = st[0]["notes"]
    assert n[0]["href"].endswith("/plan.html#zzzzzzzzzzz-s1") and n[0]["seg_title"]
    html = notes.render(ws).read_text()
    assert 'data-key="zzzzzzzzzzz:1" data-kind="concept" data-st="keep"' in html
    assert 'data-key="zzzzzzzzzzz:2" data-kind="skill" data-st=""' in html
    assert "cdn.jsdelivr" not in html


def test_notes_has_search_bar_with_category_and_note_text(tmp_path):
    ws, _ = _ws(tmp_path)
    st = notes.load_stations(ws)
    assert st[0]["category"] == listen.categories(ws).get("zzzzzzzzzzz", "")
    html = notes.render(ws).read_text()
    assert 'id="sinput"' in html and 'id="ui-data"' in html          # 跟 listen/atlas 同一份搜尋列
    assert 'data-title="測試影片 C"' in html and 'data-category="' in html
    assert "data-text=" in html and NOTES["notes"][0]["text"] in html.split("data-text=")[1].split(">")[0]
    assert 'class="cat" data-cat="' in html                          # 點分類 = 加一個篩選條件


# ---------- publish ----------

def test_publish_index_is_listen_and_keeps_captions(tmp_path):
    ws, d = _ws(tmp_path)
    listen.render(ws)
    notes.render(ws)
    (d / "plan.html").write_text("<html></html>")
    rels = {str(rel) for _, rel in publish.collect(ws)}
    assert {"index.html", "listen.html", "notes.html", "測試影片 C/captions.js", "測試影片 C/lesson.mp3"} <= rels
    src = {str(rel): src for src, rel in publish.collect(ws)}
    assert src["index.html"].name == "listen.html"


def test_publish_index_falls_back_to_atlas(tmp_path):
    ws, d = _ws(tmp_path, with_lesson=False, with_notes=False)
    (ws / "atlas.html").write_text("x")
    (d / "plan.html").write_text("x")
    src = {str(rel): src for src, rel in publish.collect(ws)}
    assert src["index.html"].name == "atlas.html"
