import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import atlas
import render

FX = Path(__file__).parent / "fixtures/ws"


def _ws(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX, ws)
    return ws


def test_waypoints_and_check(tmp_path):
    ws = _ws(tmp_path)
    wps = atlas.load_waypoints(ws)
    assert {w["id"] for w in wps} == {"abcdefghijk", "zzzzzzzzzzz"}
    assert atlas.check_atlas(atlas.load_atlas(ws), wps) == []


def test_check_rejects_bad_routes(tmp_path):
    ws = _ws(tmp_path)
    wps = atlas.load_waypoints(ws)
    bad = {"regions": [{"id": "r", "name": "r", "blurb": "", "waypoints": ["nope"]}],
           "routes": [{"from": "abcdefghijk", "to": "abcdefghijk", "type": "related", "via": ""},
                      {"from": "abcdefghijk", "to": "zzzzzzzzzzz", "type": "deepens", "via": ""},
                      {"from": "zzzzzzzzzzz", "to": "abcdefghijk", "type": "related", "via": ""}]}
    errs = atlas.check_atlas(bad, wps)
    assert any("未知 waypoint" in e for e in errs)
    assert any("from 與 to 相同" in e for e in errs)
    assert any("只能有一條" in e for e in errs)


def test_render_atlas_and_plan_nav(tmp_path):
    ws = _ws(tmp_path)
    out = atlas.render(ws)
    html = out.read_text(encoding="utf-8")
    assert "graph LR" in html and "subgraph ab[" in html
    assert html.count('class="wp"') == 2
    assert 'href="%E6%B8%AC%E8%A9%A6%E5%BD%B1%E7%89%87%20C/plan.html"' in html
    assert "深入 →" in html and "深入 ←" in html
    render.main(["--workspace", str(ws)])
    plan = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
    assert 'href="../atlas.html"' in plan and "主題區: <b>A 與 B</b>" in plan
    assert 'href="../%E6%B8%AC%E8%A9%A6%E5%BD%B1%E7%89%87%20C/plan.html"' in plan


def test_status_reports_new_waypoint(tmp_path, capsys):
    ws = _ws(tmp_path)
    (ws / "atlas.json").unlink()
    atlas.status(ws)
    out = capsys.readouterr().out
    assert out.count("★ 新站") == 2 and "共同術語" in out


def test_overview_requires_takeaways():
    from validate import check_schema
    ov = json.loads((FX / "測試影片 A: B/_overview.json").read_text())
    assert check_schema("overview", ov) == []
    del ov["takeaways"]
    assert check_schema("overview", ov)


def test_atlas_cards_are_searchable(tmp_path):
    """各站是 YouTube 式卡片：縮圖 / 標題 / 作者 / 時間，且帶上搜尋用的 data-*。"""
    ws = _ws(tmp_path)
    (ws / "測試影片 C" / "frames").mkdir(exist_ok=True)
    (ws / "測試影片 C" / "frames" / "s01_1.jpg").write_bytes(b"")
    html = atlas.render(ws).read_text(encoding="utf-8")
    assert 'id="sinput"' in html and 'data-channel="Ch"' in html
    assert 'data-category="A 與 B"' in html          # 分類 = region 名，autocomplete 用
    assert "%E6%B8%AC%E8%A9%A6%E5%BD%B1%E7%89%87%20C/frames/s01_1.jpg" in html  # 有截圖就用截圖
    assert "https://i.ytimg.com/vi/abcdefghijk/mqdefault.jpg" in html           # 沒截圖退回 YouTube 縮圖


def _top_level_decls(html: str) -> list[str]:
    """module script 裡最外層（縮排 2 格）的 const/let 名稱。"""
    body = re.search(r'<script type="module">(.*?)</script>', html, re.DOTALL).group(1)
    return re.findall(r"^  (?:const|let) (\w+)", body, re.MULTILINE)


def test_module_script_has_no_duplicate_decls(tmp_path):
    """block js 與 _base.html.j2 撞名（例如 apply）會讓整個 module 掛掉，連 mermaid 都不 render。"""
    ws = _ws(tmp_path)
    atlas.render(ws)
    render.main(["--workspace", str(ws)])
    for f in (ws / "atlas.html", ws / "測試影片 A: B" / "plan.html"):
        names = _top_level_decls(f.read_text(encoding="utf-8"))
        dup = {n for n in names if names.count(n) > 1}
        assert not dup, f"{f.name} 重複宣告：{dup}"


def test_fmt_ymd():
    assert atlas.fmt_ymd("20210315") == "2021-03-15"
    assert atlas.fmt_ymd(None) == "" and atlas.fmt_ymd("bad") == "bad"
