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
    for h in ["1. 前情提要", "2. YouTuber", "3. 逐段說明", "4. 總結", "5. 推薦三個下一步"]:
        assert h in html
    assert html.index("1. 前情提要") < html.index("2. YouTuber") < html.index("3. 逐段說明") \
        < html.index("4. 總結") < html.index("5. 推薦三個下一步")
    assert "flowchart TD" in html and "mindmap" in html and "graph TD" in html
    assert 'src="frames/s01_30.jpg"' in html
    assert "承上" in html and "留給下一段" in html


def test_mermaid_label_sanitized():
    assert '"' not in render.mm_label('a "b" [c]')
    assert len(render.mm_label("x" * 100)) == 24


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
    assert html.count('<details class="desc">') == 3
    assert "<details class=\"desc\" open" not in html
    assert '<span class="tag r">推理</span>' in html
    assert "<b>定義</b>" not in html


def test_combined_render_uses_dir_prefix(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    shutil.copy(ws / "測試影片 A: B" / "_overview.json", ws / "_overview.json")
    render.main(["--workspace", str(ws), "--combined"])
    html = (ws / "plan.html").read_text(encoding="utf-8")
    assert 'src="%E6%B8%AC%E8%A9%A6%E5%BD%B1%E7%89%87%20A%3A%20B/frames/s01_30.jpg"' in html
