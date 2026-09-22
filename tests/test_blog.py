"""來源是部落格文章：抓正文、閱讀時間軸、文中圖片當截圖、render 顯示段落編號與原文連結。不碰網路。"""
import json
import shutil
import sys
from itertools import pairwise
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import atlas
import blog
import estimate
import fetch
import render
import screenshot
import validate
from common import load_json, load_yaml, video_id

FX = Path(__file__).parent / "fixtures"
HTML = (FX / "blog/post.html").read_text(encoding="utf-8")
URL = "https://blog.example.com/posts/attention"
CFG = load_yaml(Path(__file__).parent.parent / "config/estimate.yaml")


@pytest.fixture
def art():
    return blog.extract(HTML, URL, CFG["blog"])


def test_extract_paragraphs_as_timeline(art):
    assert art["title"] == "Why attention is all you need"
    assert art["author"] == "Jane Doe" and art["date"] == "20240315" and art["lang"] == "en"
    assert art["image"] == "https://blog.example.com/img/cover.png"
    ev = art["events"]
    assert [e["kind"] for e in ev][:4] == ["h1", "p", "h2", "p"]
    assert [e["para"] for e in ev] == list(range(1, len(ev) + 1))
    for a, b in pairwise(ev):                          # 時間軸連續：每段從上一段結束處開始
        assert abs(a["start"] + a["duration"] - b["start"]) < 0.02
    assert art["duration"] == round(ev[-1]["start"] + ev[-1]["duration"], 2)
    assert "Home" not in " ".join(e["text"] for e in ev)  # nav 不算正文
    assert any(e["kind"] == "code" for e in ev) and any(e["kind"] == "list" for e in ev)
    assert [c["title"] for c in art["chapters"]][1:] == ["Queries, keys and values", "Multiple heads"]


def test_extract_images_with_position(art):
    im = art["images"]
    assert [i["src"] for i in im] == ["https://blog.example.com/img/qkv.png", "https://cdn.example.com/heads.jpg"]
    assert im[0]["alt"] == "QKV diagram" and im[0]["t"] < im[1]["t"]
    assert blog.image_for(im, im[1]["t"] + 3)["src"] == im[1]["src"]           # 沒指定 src 就取最近的
    assert blog.image_for(im, 0, "https://x/y.png")["src"] == "https://x/y.png"  # 指定 src 就用它


def test_title_prefers_h1_and_strips_site_suffix():
    h = HTML.replace("<h1>Why attention is all you need</h1>", "").replace(
        "<title>Why attention is all you need</title>", "<title>Why attention is all you need | Example Blog</title>")
    assert blog.extract(h, URL, CFG["blog"])["title"] == "Why attention is all you need"
    assert blog.extract(HTML, URL, CFG["blog"])["title"] == "Why attention is all you need"


def test_reading_seconds_cjk_vs_words():
    cfg = {"cjk_chars_per_min": 300, "words_per_min": 200}
    assert blog.reading_seconds("一" * 300, cfg) == 60
    assert blog.reading_seconds("word " * 200, cfg) == 60
    assert blog.reading_seconds("x", cfg) == 1.0                # 至少 1 秒
    assert blog.guess_lang("<html><body>", "這是一篇中文文章的內容測試") == "zh"
    assert blog.guess_lang('<html lang="ja"><body>', "x") == "ja"


def test_source_href_and_pos_label(art):
    ev = art["events"]
    href = blog.source_href(URL, ev, ev[3]["start"] + 1)
    assert href.startswith(URL + "#:~:text=Every%20token%20produces")
    assert blog.pos_label(ev, ev[3]["start"] + 1) == "¶4"
    assert blog.pos_label(ev, 0) == "¶1" and blog.pos_label(ev, 10_000) == f"¶{len(ev)}"
    assert blog.snippet("你好，世界。這是測試") == "你好"
    assert blog.source_href(URL, [], 5) == URL


def test_download_image_picks_extension(tmp_path, monkeypatch):
    class R:
        def __init__(self, ctype):
            self.headers = {"Content-Type": ctype}

        def read(self):
            return b"img"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr(blog.urllib.request, "urlopen", lambda req, timeout=30: R("image/png"))
    assert blog.download_image("https://x/a.jpg", tmp_path / "s01_3").name == "s01_3.jpg"
    assert blog.download_image("https://x/a?id=9", tmp_path / "s01_4").name == "s01_4.png"


def test_probe_and_estimate_blog(monkeypatch):
    monkeypatch.setattr(blog, "fetch_html", lambda url: HTML)
    meta = estimate.probe(URL, 720)
    assert meta["source"] == "blog" and meta["id"] == video_id(URL) and meta["n_images"] == 2
    est = estimate.estimate_one(meta, "true", CFG, "auto", None)
    assert est["source"] == "blog" and est["url"] == URL
    assert est["assumed"]["frames"] == 2 and est["assumed"]["download_mb"] == 0  # 圖片數封頂、不下載影片
    assert est["stages"]["fetch"]["sec"] == CFG["blog"]["fetch_sec"]
    assert est["stages"]["shot"]["sec"] == 2 * CFG["blog"]["sec_per_image"]
    none = estimate.estimate_one(meta, "true", CFG, "none", None)
    assert none["assumed"]["frames"] == 0 and none["stages"]["shot"]["sec"] == 0


def _blog_station(ws: Path, monkeypatch) -> Path:
    """用假的 HTML 跑 fetch，再手寫 segments / analysis / _overview，得到一個完整的部落格站。"""
    monkeypatch.setattr(blog, "fetch_html", lambda url: HTML)
    fetch.main([URL, "--workspace", str(ws), "--output-lang", "zh-TW"])
    d = ws / "Why attention is all you need"
    assert d.is_dir()
    vid = video_id(URL)
    ev = load_json(d / "transcript.json")["events"]
    im = load_json(d / "transcript.json")["images"]
    end = ev[-1]["start"] + ev[-1]["duration"]
    segs = {
        "video_id": vid, "vision": True, "vision_reason": "有架構圖", "shots_mode": "auto",
        "segments": [
            {"id": 1, "start": 0, "end": ev[5]["start"], "title": "QKV", "summary": "三個向量。",
             "shots": [{"t": im[0]["t"], "why": "QKV 圖", "src": im[0]["src"]}],
             "clips": [{"start": ev[3]["start"], "end": ev[4]["start"], "why": "定義", "translation": "每個 token 產生三個向量。"}]},
            {"id": 2, "start": ev[5]["start"], "end": end, "title": "多頭", "summary": "平行多個 head。",
             "shots": [{"t": im[1]["t"], "why": "多頭示意圖"}]},
        ],
    }
    (d / "segments.json").write_text(json.dumps(segs, ensure_ascii=False), encoding="utf-8")
    an = {
        "video_id": vid, "vision_used": True, "author_reasoning": "從 RNN 的限制推到 attention。",
        "segments": [
            {"id": 1, "title": "QKV", "builds_on": "前情提要的 RNN。", "reasoning": "因為要一次看全部。",
             "explanation": "文中定義了 query/key/value。", "leads_to": "一張 map 不夠。",
             "terms": [{"term": "query", "definition": "問問題的向量", "zh": "查詢", "related": [{"term": "key", "rel": "配對"}]}],
             "issues": [{"level": "debatable", "t": ev[8]["start"], "quote": "Eight heads is the usual default.",
                         "note": "視模型大小而定。", "evidence": "原論文用 8，之後的模型不一定"}]},
            {"id": 2, "title": "多頭", "builds_on": "上一段說一張 map 不夠。", "reasoning": "所以平行多個 head。",
             "explanation": "", "leads_to": "順序資訊從哪來？",
             "terms": [{"term": "key", "definition": "宣告內容的向量", "zh": "鍵"}]},
        ],
    }
    (d / "analysis.json").write_text(json.dumps(an, ensure_ascii=False), encoding="utf-8")
    ov = {
        "topic": "Attention", "prerequisites": [{"concept": "RNN", "note": "循環網路"}],
        "outline": [{"video_id": vid, "role": "起點", "line": "建立 attention 的直覺"}],
        "summary": "attention 是可微分的字典查詢。",
        "next_steps": [{"direction": "位置編碼", "why": "文末留下的問題", "search_keywords": ["positional encoding"]}] * 3,
        "takeaways": ["QKV 是什麼", "多頭為什麼便宜", "attention 不看距離"],
    }
    (d / "_overview.json").write_text(json.dumps(ov, ensure_ascii=False), encoding="utf-8")
    return d


def test_fetch_blog_writes_meta_and_transcript(tmp_path, monkeypatch):
    d = _blog_station(tmp_path / "ws", monkeypatch)
    meta = load_json(d / "meta.json")
    assert meta["source"] == "blog" and meta["video_id"].startswith("b_")
    assert meta["channel"] == "Jane Doe" and meta["upload_date"] == "20240315"
    assert meta["thumbnail"].endswith("cover.png") and meta["n_images"] == 2
    assert [c["title"] for c in meta["chapters"]][1:] == ["Queries, keys and values", "Multiple heads"]
    tr = load_json(d / "transcript.json")
    assert tr["source"] == "blog" and len(tr["images"]) == 2 and tr["events"][0]["kind"] == "h1"
    # 手寫的 segments / analysis 要過 validate（時間軸是秒數，規則不變）
    assert validate.validate("segments", d / "segments.json") == []
    assert validate.validate("analysis", d / "analysis.json") == []
    # 只給 id 再跑一次：從 meta.json 找回網址，且已存在就跳過
    fetch.main([meta["video_id"], "--workspace", str(tmp_path / "ws")])


def test_shot_downloads_article_images(tmp_path, monkeypatch):
    d = _blog_station(tmp_path / "ws", monkeypatch)
    got = []

    def fake_dl(src, stem):
        got.append(src)
        out = stem.with_suffix(".png" if src.endswith(".png") else ".jpg")
        out.write_bytes(b"x")
        return out

    monkeypatch.setattr(blog, "download_image", fake_dl)
    monkeypatch.setattr(screenshot.shutil, "which", lambda x: None)  # 沒有 ffmpeg 也能跑
    screenshot.main([load_json(d / "meta.json")["video_id"], "--workspace", str(tmp_path / "ws")])
    assert got == ["https://blog.example.com/img/qkv.png", "https://cdn.example.com/heads.jpg"]
    segs = load_json(d / "segments.json")
    files = [sh["file"] for s in segs["segments"] for sh in s["shots"]]
    assert files[0].startswith("frames/s01_") and files[0].endswith(".png")
    assert files[1].startswith("frames/s02_") and files[1].endswith(".jpg")
    assert segs["segments"][1]["shots"][0]["src"] == "https://cdn.example.com/heads.jpg"  # 沒寫 src 的補上
    # 第二次：都已存在就跳過，不再下載
    screenshot.main([load_json(d / "meta.json")["video_id"], "--workspace", str(tmp_path / "ws")])
    assert len(got) == 2


def test_render_blog_uses_paragraph_labels_and_text_fragments(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    d = _blog_station(ws, monkeypatch)
    (d / "frames").mkdir()
    (d / "frames" / "s01_24.png").write_bytes(b"x")
    segs = load_json(d / "segments.json")
    segs["segments"][0]["shots"][0]["file"] = "frames/s01_24.png"
    (d / "segments.json").write_text(json.dumps(segs), encoding="utf-8")
    render.main(["--workspace", str(ws)])
    html = (d / "plan.html").read_text(encoding="utf-8")
    assert "2. 作者的思維推導" in html and "YouTuber" not in html
    assert ">原文</a>" in html and "閱讀約" in html and "文章語言 en" in html
    assert 'href="https://blog.example.com/posts/attention#:~:text=' in html  # 段落連到原文
    assert "&amp;t=" not in html and ">¶1</a>–¶5" in html                   # 不是秒數，是段落編號
    assert 'src="frames/s01_24.png"' in html and "¶5 · QKV 圖" in html
    assert 'class="issue debatable"' in html and "#:~:text=Eight%20heads%20is" in html


def test_atlas_card_for_blog_uses_og_image(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    shutil.copytree(FX / "ws", ws)
    _blog_station(ws, monkeypatch)
    wps = atlas.load_waypoints(ws)
    w = next(x for x in wps if x["kind"] == "blog")
    assert w["yt_thumb"] == "https://blog.example.com/img/cover.png"
    assert w["channel"] == "Jane Doe" and w["upload_date"] == "2024-03-15"
    assert all(x["kind"] == "youtube" for x in wps if x is not w)
    atlas.main(["--workspace", str(ws)])
    html = (ws / "atlas.html").read_text(encoding="utf-8")
    assert html.count('class="wp"') == 3 and ">原文</a>" in html and html.count(">YouTube</a>") == 2


def test_narrate_reads_article_text_per_sentence(art):
    import narrate

    ev = art["events"]
    lines = narrate.read_texts(ev, ev[3]["start"], ev[5]["start"])   # 第 4、5 段
    assert lines[0].startswith("Every token produces") and any(x.startswith("Softmax") for x in lines)
    assert all(len(x) <= narrate.DUB_MAX * 3 for x in lines)
    assert len(narrate.dub_lines("A" * 100 + ". " + "B" * 50 + ".")) == 2   # 英文一句可以比中文長
    assert narrate.read_texts(ev, 0, 0) == []
