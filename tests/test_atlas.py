import json
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
    assert 'href="../atlas.html"' in plan and "主題區：<b>A 與 B</b>" in plan
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
