import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import atlas
import pytest
import render
from i18n import Strings

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


def test_merge_keeps_other_routes(tmp_path):
    """兩支影片先後併入：後者不會蓋掉前者的 route（平行跑 atlas 的主要衝突點）。"""
    base = {"regions": [], "routes": []}
    a = atlas.merge_atlas(base, {"routes": [{"from": "a", "to": "b", "type": "related", "via": "x"}],
                                 "regions": [{"id": "r1", "name": "R1", "blurb": "", "waypoints": ["a"]}]})
    b = atlas.merge_atlas(a, {"routes": [{"from": "c", "to": "b", "type": "deepens", "via": "y"}],
                              "regions": [{"id": "r1", "name": "R1", "blurb": "", "waypoints": ["c"]}]})
    assert {(e["from"], e["to"]) for e in b["routes"]} == {("a", "b"), ("c", "b")}
    assert b["regions"][0]["waypoints"] == ["a", "c"]


def test_merge_replaces_same_pair_and_moves_region(tmp_path):
    a = {"regions": [{"id": "r1", "name": "R1", "blurb": "", "waypoints": ["a", "b"]}],
         "routes": [{"from": "a", "to": "b", "type": "related", "via": "舊"}]}
    b = atlas.merge_atlas(a, {"routes": [{"from": "b", "to": "a", "type": "prerequisite", "via": "新"}],
                              "regions": [{"id": "r2", "name": "R2", "blurb": "", "waypoints": ["b"]}]})
    assert len(b["routes"]) == 1 and b["routes"][0]["via"] == "新"        # 同一對站只留一條
    assert [r["waypoints"] for r in b["regions"]] == [["a"], ["b"]]        # b 換區，不會兩區都有


def test_merge_cli_writes_and_renders(tmp_path):
    ws = _ws(tmp_path)
    (ws / "atlas.json").write_text(json.dumps({"regions": [], "routes": []}), encoding="utf-8")
    patch = tmp_path / "patch.json"
    patch.write_text(json.dumps({"routes": [{"from": "abcdefghijk", "to": "zzzzzzzzzzz",
                                             "type": "deepens", "via": "共同術語"}]}), encoding="utf-8")
    atlas.main(["--workspace", str(ws), "--merge", str(patch)])
    assert json.loads((ws / "atlas.json").read_text())["routes"][0]["via"] == "共同術語"
    assert (ws / "atlas.html").exists()


def test_merge_cli_rejects_broken_patch(tmp_path):
    ws = _ws(tmp_path)
    before = (ws / "atlas.json").read_text()
    patch = tmp_path / "patch.json"
    patch.write_text(json.dumps({"routes": [{"from": "abcdefghijk", "to": "nope",
                                             "type": "deepens", "via": ""}]}), encoding="utf-8")
    with pytest.raises(SystemExit):
        atlas.main(["--workspace", str(ws), "--merge", str(patch)])
    assert (ws / "atlas.json").read_text() == before  # 驗證沒過就不寫入


def test_pipeline_and_next_actions(tmp_path):
    from i18n import Strings

    ws = _ws(tmp_path)
    S = Strings("zh-TW")
    d = ws / "測試影片 A: B"
    st = {x["key"]: x for x in atlas.pipeline(d, True, True, S)}
    assert st["fetch"]["state"] == "done" and st["segment"]["state"] == "done"
    assert st["analyze"]["state"] == "done" and st["atlas"]["state"] == "done"
    assert st["estimate"]["state"] == "todo"          # fixture 沒有 estimate.json
    assert st["narrate"]["state"] == "todo"           # 也還沒做聽力版
    assert atlas.pipeline(d, False, False, S)[6]["state"] == "skip"   # 只有一站時不需要上地圖

    # 做了聽力版但沒挑原聲片段 → 沒做完，而且說得出缺什麼
    (d / "lesson.json").write_text(json.dumps({"duration": 1, "dub": None}), encoding="utf-8")
    nar = {x["key"]: x for x in atlas.pipeline(d, True, True, S)}["narrate"]
    assert nar["state"] == "partial" and nar["note"] == S.n_no_clips

    w = next(x for x in atlas.load_waypoints(ws) if x["dir"] == d.name)
    acts = atlas.next_actions(w, atlas.pipeline(d, True, True, S), S)
    assert [a["prompt"] for a in acts if a["prompt"].startswith("/atlas:learn-estimate")]  # 單一階段就給指令
    # 沒做完的是 estimate / render / narrate，做到最後一步就把三步都寫進 prompt
    assert acts[-1]["prompt"].count("/atlas:learn-") == 3
    assert S.n_no_clips not in acts[-1]["prompt"] and "rules/narration.md" in acts[-1]["prompt"]


def test_atlas_html_has_stage_ui(tmp_path):
    ws = _ws(tmp_path)
    atlas.render(ws)
    html = (ws / "atlas.html").read_text(encoding="utf-8")
    assert 'id="nextstep"' in html and html.count('class="prog"') == 2
    data = json.loads(html.split('id="steps-data" type="application/json">')[1].split("</script>")[0])
    assert set(data) == {"abcdefghijk", "zzzzzzzzzzz"}
    assert len(data["abcdefghijk"]["stages"]) == 8 and data["abcdefghijk"]["actions"]


def test_author_error_rate_badge(tmp_path):
    ws = _ws(tmp_path)
    a = json.loads((ws / "測試影片 C/analysis.json").read_text(encoding="utf-8"))
    a["segments"][0]["issues"] = [{"level": "debatable", "t": 1, "quote": "看情況",
                                   "note": "取決於版本", "evidence": "本片第 1 段"}]
    (ws / "測試影片 C/analysis.json").write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    wps = atlas.load_waypoints(ws)
    st = atlas.author_stats(wps, Strings("zh-TW"))["Ch"]  # 兩支都是同一個頻道
    assert (st["videos"], st["segments"], st["wrong"], st["debatable"]) == (2, 6, 2, 1)
    assert st["clean"] is False
    html = atlas.render(ws).read_text(encoding="utf-8")
    assert html.count('class="err w"') == 2 and html.count('class="err d"') == 2
    assert "2 處確定錯誤" in html and "1 處見仁見智" in html
    assert "%" not in html.split('class="by"')[1].split("</div>")[0]  # 顯示件數不是比例


def test_map_nodes_use_image_shape(tmp_path):
    ws = _ws(tmp_path)
    html = atlas.render(ws).read_text(encoding="utf-8")
    assert html.count("@{ img: &#34;https://i.ytimg.com/vi/") == 2  # 兩站都帶縮圖
    nodes = json.loads(re.search(r'id="nodes-data"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))
    assert nodes["w0"] == "abcdefghijk" and set(nodes.values()) == {"abcdefghijk", "zzzzzzzzzzz"}
