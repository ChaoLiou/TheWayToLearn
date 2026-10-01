import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import render

FX = Path(__file__).parent / "fixtures/ws"


def test_render_produces_html(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    for h in ["1. Outline", "2. YouTuber", "3. 逐段說明", "4. 總結", "5. 推薦三個下一步"]:
        assert h in html
    assert html.index("1. Outline") < html.index("2. YouTuber") < html.index("3. 逐段說明") \
        < html.index("4. 總結") < html.index("5. 推薦三個下一步")
    assert 'src="frames/s01_30.jpg"' in html
    assert "承上" in html and "留給下一段" in html


def test_no_mermaid_diagrams(tmp_path):
    """推理鏈本來就是一條線、mindmap 與術語關聯圖沒人看 → plan.html 不再畫任何圖。"""
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert 'class="mermaid"' not in html
    for gone in ["flowchart TD", "mindmap\n", "graph TD", "看之前需要先懂", "作者說"]:
        assert gone not in html


def test_reasoning_split_into_paragraphs(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    body = html[html.index("2. YouTuber"):html.index("3. 逐段說明")]
    assert body.count("<p>") >= 1
    assert render.paras("一。二。三。四。五。六。七。") == ["一。二。三。", "四。五。六。", "七。"]
    assert render.paras("A\n\nB") == ["A", "B"]
    assert render.paras("") == []


def test_terms_marked_inline(tmp_path):
    """術語就地標在文章第一次出現的地方，不再另外列一份 dl。"""
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert '<dl class="terms"' not in html
    # 每個術語都還有 ⓘ 與 dialog（文中沒出現的收在 .terms-extra 那一行）
    assert html.count("<dialog id=\"term-") == html.count('class="info" data-term=')
    texts = {"summary": "先講 X 再說別的", "reasoning": "X 又出現一次，還有 Y"}
    terms = [{"term": "X", "zh": "X 中文", "tid": "t1"}, {"term": "Y", "zh": "Y 中文", "tid": "t2"},
             {"term": "Z", "zh": "Z 中文", "tid": "t3"}]
    marked, extra = render.mark_terms(texts, terms, "更多")
    assert marked["summary"].count('class="term"') == 1      # X 只標第一次
    assert marked["reasoning"].count('class="term"') == 1    # 只有 Y
    assert [t["term"] for t in extra] == ["Z"]               # 文中沒出現


def test_interactive_features_present(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert 'href="https://www.youtube.com/results?search_query=B%20tutorial"' in html
    assert 'class="term" data-zh="X（中文）"' in html
    assert "<dialog" in html and "更多說明" in html
    assert 'id="viewer"' in html and "mm-wrap" in html


def test_diagram_descriptions_collapsed(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert html.count('<details class="desc">') == 1   # 推理鏈文字（這份 fixture 沒有耗時、沒有語音解析）
    assert "<details class=\"desc\" open" not in html
    assert '<span class="tag r">推理</span>' in html
    assert "<b>定義</b>" not in html


def test_atlas_nav_at_bottom_and_chapters_collapsed(tmp_path):
    """相鄰站的列表擺在文件最後（開頭要直接是內容）；語音解析只留播放器，章節收合。"""
    import json
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    (ws / "atlas.json").write_text(json.dumps({
        "regions": [{"id": "r1", "name": "區", "waypoints": ["vid"]}],
        "routes": [{"from": "vid", "to": "vid2", "type": "next", "via": "接著看"}],
    }, ensure_ascii=False), encoding="utf-8")
    (ws / "測試影片 A: B" / "lesson.json").write_text(
        json.dumps(_lesson_fixture(), ensure_ascii=False), encoding="utf-8")
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert html.index("5. 推薦三個下一步") < html.index('class="card atlas-nav"') < html.index("</main>")
    # 章節在收合的 details 裡，播放器不在
    assert '<summary>章節（1）</summary>' in html
    assert html.index('<audio id="lesson"') < html.index("<summary>章節（1）</summary>")


def test_combined_render_uses_dir_prefix(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    shutil.copy(ws / "測試影片 A: B" / "_overview.json", ws / "_overview.json")
    render.main(["--workspace", str(ws), "--combined"])
    html = (ws / "plan.html").read_text(encoding="utf-8")
    assert 'src="%E6%B8%AC%E8%A9%A6%E5%BD%B1%E7%89%87%20A%3A%20B/frames/s01_30.jpg"' in html


def test_issues_rendered_per_segment_and_summary(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert html.count('class="issue wrong"') == 1
    assert "勘誤總整理" in html and '<tr class="wrong">' in html
    assert "方法 A 永遠不會失敗" in html


def test_english_output_lang_switches_ui(tmp_path):
    import json
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    mp = ws / "測試影片 A: B" / "meta.json"
    m = json.loads(mp.read_text()); m["output_lang"] = "en"; mp.write_text(json.dumps(m))
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert "1. Outline" in html and "Builds on" in html and 'lang="en"' in html
    assert "承上" not in html and "留給下一段" not in html


def _lesson_fixture():
    """一份兩軌的 lesson.json：say 兩軌共用，clip 在翻譯軌換成配音。"""
    say = {"i": 1, "at": 0.0, "dur": 4.0, "kind": "say", "seg_id": 1, "seg_title": "第一段",
           "text": "先聽作者怎麼說", "label": "", "source_start": None, "source_end": None,
           "lines": [{"at": 0.0, "dur": 4.0, "text": "先聽作者怎麼說"}], "translation": ""}
    clip = {"i": 2, "at": 4.0, "dur": 6.0, "kind": "clip", "seg_id": 1, "seg_title": "第一段",
            "text": "", "label": "作者的比喻", "source_start": 10.0, "source_end": 16.0,
            "lines": [{"at": 4.0, "dur": 6.0, "text": "a partition is like a wall"}],
            "translation": "partition 就像一道牆。"}
    dub = dict(clip, kind="dub", dur=3.0, orig_text="a partition is like a wall",
               lines=[{"at": 4.0, "dur": 3.0, "text": "partition 就像一道牆。"}])
    return {
        "video_id": "vid", "voice": "zh-TW-HsiaoChenNeural", "rate": "+0%", "duration": 10.0,
        "file": "lesson.mp3", "chapters": [{"seg_id": 1, "title": "第一段", "at": 0.0}],
        "timeline": [say, clip], "reused_parts": 0, "total_parts": 2,
        "dub": {"file": "lesson.dub.mp3", "voice": "zh-TW-YunJheNeural", "duration": 7.0,
                "chapters": [{"seg_id": 1, "title": "第一段", "at": 0.0}],
                "timeline": [say, dub]},
    }


def test_lesson_dub_toggle_rendered(tmp_path):
    import json
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    (ws / "測試影片 A: B" / "lesson.json").write_text(
        json.dumps(_lesson_fixture(), ensure_ascii=False), encoding="utf-8")
    render.main(["--workspace", str(ws)])
    html = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert 'data-mode="orig"' in html and 'data-mode="dub"' in html   # 切換鈕（卡片 + 講稿列）
    assert html.count('data-mode="dub"') == 2
    assert "lesson.dub.mp3" in html
    data = json.loads(html.split('id="lesson-data" type="application/json">')[1].split("</script>")[0])
    assert data["dub"]["href"].endswith("lesson.dub.mp3")
    assert data["dub"]["timeline"][1]["lines"][0]["text"] == "partition 就像一道牆。"
    # 沒有翻譯軌時不要出現切換鈕
    (ws / "測試影片 C" / "lesson.json").write_text(
        json.dumps(dict(_lesson_fixture(), dub=None), ensure_ascii=False), encoding="utf-8")
    render.main(["--workspace", str(ws)])
    assert 'data-mode=' not in (ws / "測試影片 C" / "plan.html").read_text(encoding="utf-8")
