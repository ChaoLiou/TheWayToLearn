import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from urllib.parse import quote

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
    # 有 notes.json 就連過去：那頁遲早會產出（/learn-notes 寫完 json 就會跑 notes.py）。
    # 判準是「資料在不在」而不是「html 這一刻產了沒」，否則先產的頁會永久少一個頁籤。
    assert "notes.html#zzzzzzzzzzz" in html
    notes.render(ws)
    assert "notes.html#zzzzzzzzzzz" in listen.render(ws).read_text()


def test_topnav_does_not_depend_on_render_order(tmp_path):
    """四頁互相連結：先產的那頁也要看得到還沒產出的兄弟頁（依資料判斷，不依 html）。"""
    import common
    ws, d = _ws(tmp_path)
    (d / "digest.json").write_text(json.dumps(
        {"video_id": "zzzzzzzzzzz", "items": []}, ensure_ascii=False), encoding="utf-8")
    sib = common.sibling_pages(ws)
    assert sib == {"has_listen": True, "has_notes": True, "has_digest": True, "has_atlas": True,
                   "home_page": "atlas.html"}
    # listen 先產（此時四個 html 都還不存在）→ topnav 仍然四個都在
    html = listen.render(ws).read_text()
    for href in ("notes.html", "digest.html", "atlas.html"):
        assert f'href="{href}"' in html
    # 完全沒有資料的 workspace 就不要亂連
    bare = tmp_path / "bare"
    (bare / "X vid").mkdir(parents=True)
    (bare / "X vid" / "meta.json").write_text('{"video_id":"x"}')
    assert common.sibling_pages(bare) == {
        "has_listen": False, "has_notes": False, "has_digest": False, "has_atlas": False,
        "home_page": "atlas.html"}


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


def test_publish_media_base_splits_mp3_out(tmp_path):
    """混合式：mp3 進 dist-media/，HTML 留在 dist/ 且路徑改寫成絕對網址。"""
    ws, d = _ws(tmp_path)
    listen.render(ws)
    (d / "frames").mkdir(exist_ok=True)
    (d / "frames" / "s01_30.jpg").write_text("img", encoding="utf-8")
    (d / "plan.html").write_text(
        '<audio src="lesson.mp3"><img src="frames/s01_30.jpg">'
        '<span>依據: 截圖 frames/s01_30.jpg 的資料表</span>'
        '<img src="https://i.ytimg.com/vi/x/hq.jpg"><script>{"href": "lesson.dub.mp3"}</script>',
        encoding="utf-8")
    dist, media = tmp_path / "dist", tmp_path / "dist-media"
    base = "https://media.example.com/learn"
    _, mp3s = publish.build(ws, dist, media, base)
    # mp3 不在 dist/ 裡，而在 dist-media/
    assert not list(dist.rglob("*.mp3"))
    assert {rel.name for _, rel in mp3s} == {"lesson.mp3", "lesson.dub.mp3", "s01_30.jpg"}
    assert (media / d.name / "lesson.mp3").exists()
    # plan.html 的裸檔名要補回站名
    plan = (dist / d.name / "plan.html").read_text(encoding="utf-8")
    assert f'src="{base}/{quote(d.name)}/lesson.mp3"' in plan
    assert f'"href": "{base}/{quote(d.name)}/lesson.dub.mp3"' in plan
    # 截圖一起搬走，但外部縮圖與散文裡提到的檔名不動
    assert f'<img src="{base}/{quote(d.name)}/frames/s01_30.jpg">' in plan
    assert '<img src="https://i.ytimg.com/vi/x/hq.jpg">' in plan
    assert "依據: 截圖 frames/s01_30.jpg 的資料表" in plan
    assert not list(dist.rglob("*.jpg")) and (media / d.name / "frames" / "s01_30.jpg").exists()
    # listen.html 本來就帶站名前綴，不能變成兩層
    lis = (dist / "listen.html").read_text(encoding="utf-8")
    assert f"{base}/{quote(d.name)}/lesson.mp3" in lis and f"{base}/{base}" not in lis
    # 沒有 --media-base 就跟以前一樣，全部留在 dist/
    _, mp3s2 = publish.build(ws, dist)
    assert mp3s2 == [] and (dist / d.name / "lesson.mp3").exists()


def test_publish_r2_worker_serves_media_prefix(tmp_path):
    """--r2-binding 產出 dist/_worker.js：媒體前綴讀 R2，其餘丟回靜態檔，且處理 Range。"""
    ws, d = _ws(tmp_path)
    (d / "plan.html").write_text('<audio src="lesson.mp3">', encoding="utf-8")
    dist = tmp_path / "dist"
    publish.build(ws, dist, tmp_path / "m", "/media")
    publish.write_worker(dist, "/media", "MEDIA")
    js = (dist / "_worker.js").read_text(encoding="utf-8")
    assert 'const PREFIX = "/media/"' in js          # 前綴自動補斜線
    assert "env.MEDIA.get(key" in js
    assert "env.ASSETS.fetch(request)" in js         # 非媒體路徑回靜態檔
    assert "content-range" in js and "accept-ranges" in js and "status: 206" in js
    assert 'audio/mpeg' in js                        # content-type 補救（iOS 會挑）
    # 站內路徑的 base：HTML 變成 root-relative，plan.html 在子目錄也指得到
    assert 'src="/media/' in (dist / d.name / "plan.html").read_text(encoding="utf-8")


def test_publish_r2_binding_rejects_absolute_base(tmp_path):
    """絕對網址 = R2 自己接了自訂網域，不需要 worker；混用會產出指不到的前綴。"""
    import pytest
    ws, d = _ws(tmp_path)
    (d / "plan.html").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="站內路徑"):
        publish.main(["--workspace", str(ws), "--out", str(tmp_path / "dist"),
                      "--media-base", "https://x.example.com", "--r2-binding", "MEDIA"])


def test_publish_media_rewrite_only_touches_quoted_paths():
    r = publish.rewrite_media
    assert r('<audio src="lesson.mp3">', "https://m.x", "站 A")[0] == '<audio src="https://m.x/%E7%AB%99%20A/lesson.mp3">'
    assert r('"mp3":"a%20b/lesson.dub.mp3"', "https://m.x", None)[0] == '"mp3":"https://m.x/a%20b/lesson.dub.mp3"'
    assert r("語音解析檔名是 lesson.mp3 喔", "https://m.x", "S")[1] == 0   # 沒有引號夾住 = 不是路徑
    assert r('src="frames/a.jpg"', "https://m.x", "S")[0] == 'src="https://m.x/S/frames/a.jpg"'
    assert r('src="https://i.ytimg.com/vi/x/hq.jpg"', "https://m.x", "S")[1] == 0   # 外部網址不動


def test_publish_index_falls_back_to_atlas(tmp_path):
    ws, d = _ws(tmp_path, with_lesson=False, with_notes=False)
    (ws / "atlas.html").write_text("x")
    (d / "plan.html").write_text("x")
    src = {str(rel): src for src, rel in publish.collect(ws)}
    assert src["index.html"].name == "atlas.html"


def test_publish_media_key_collapses_dot_runs(tmp_path):
    """Cloudflare 管理 API 把路徑裡的 `..` 當目錄穿越擋掉，所以媒體 key 的連續點要收斂成一個。
    URL 與 dist-media/ 的路徑必須一起收斂，不然對不上。"""
    assert publish.safe_key("You Think.. Here's Why/lesson.mp3") == "You Think. Here's Why/lesson.mp3"
    assert publish.safe_key("a...b/x.mp3") == "a.b/x.mp3"
    assert publish.safe_key("lesson.dub.mp3") == "lesson.dub.mp3"   # 單點不動
    r = publish.rewrite_media('<audio src="lesson.mp3">', "https://m.x", "Think.. Here")
    assert r[0] == '<audio src="https://m.x/Think.%20Here/lesson.mp3">'


def test_publish_media_key_collision_is_refused(tmp_path):
    """收斂後撞名就停下來，不要靜靜蓋掉別站的檔。"""
    import pytest
    ws, d = _ws(tmp_path)
    (d / "plan.html").write_text("x", encoding="utf-8")
    for nm in ("S.. A", "S. A"):           # 兩個站收斂後同名
        o = ws / nm
        (o / "frames").mkdir(parents=True)
        (o / "frames" / "s01_1.jpg").write_text("i")
        (o / "plan.html").write_text("x")
    with pytest.raises(SystemExit, match="媒體 key 衝突"):
        publish.build(ws, tmp_path / "dist", tmp_path / "m", "/media")


def test_plan_hub_links_carry_only_filter(tmp_path):
    """從某支影片的文字解析點「筆記／練習」→ 帶 ?only=<id>，那一頁預設只篩這一支。
    語音解析不帶（播放器要能自動接下一集）；這一站沒有那份資料就不顯示連結。"""
    import shutil

    import render
    fx = Path(__file__).parent / "fixtures/ws"
    ws = tmp_path / "ws"
    shutil.copytree(fx, ws)
    d = ws / "測試影片 A: B"
    for n in ("listen.html", "notes.html", "digest.html"):
        (ws / n).write_text("x", encoding="utf-8")
    (d / "notes.json").write_text(json.dumps(
        {"video_id": "abcdefghijk", "created": "2026-01-01T00:00:00+00:00",
         "notes": [{"id": 1, "kind": "concept", "seg_id": 1, "text": "x"}]}, ensure_ascii=False), encoding="utf-8")
    (d / "digest.json").write_text(json.dumps({"video_id": "abcdefghijk", "items": []}, ensure_ascii=False), encoding="utf-8")
    render.main(["--workspace", str(ws)])
    html = (d / "plan.html").read_text(encoding="utf-8")
    assert 'href="../notes.html?only=abcdefghijk#abcdefghijk"' in html
    assert 'href="../digest.html?only=abcdefghijk#abcdefghijk"' in html
    assert "listen.html" not in html          # 這站沒有 lesson.mp3
    # 另一站有 digest.json 但沒有 notes.json → 只連練習，不連筆記
    other = (ws / "測試影片 C" / "plan.html").read_text(encoding="utf-8")
    assert "digest.html?only=zzzzzzzzzzz#zzzzzzzzzzz" in other
    assert "notes.html?only=" not in other


def test_search_macro_supports_only_param():
    """?only= 的 chip 走精確 id 比對，而且不出現在 autocomplete 裡。"""
    js = (Path(__file__).parent.parent / "templates/_search.html.j2").read_text(encoding="utf-8")
    assert 'URLSearchParams(location.search).get("only")' in js
    assert 'ch.kind === "vid" ? c.id === ch.value' in js      # 精確比對，不是 includes
    assert "vid: UI.video" in js
    assert 'acItems.push({ kind: "vid"' not in js             # autocomplete 不提供
