"""digest.json（PACER 工作單）的 schema 與硬規則：rules/digest.md。"""
import copy
import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import digest
import publish
import render
import validate

FIX = Path(__file__).parent / "fixtures" / "ws" / "測試影片 C"
GOOD = json.loads((FIX / "digest.json").read_text())


def _errs(tmp_path, data):
    d = tmp_path / "站"
    d.mkdir(exist_ok=True)
    (d / "analysis.json").write_text((FIX / "analysis.json").read_text())
    (d / "digest.json").write_text(json.dumps(data, ensure_ascii=False))
    return validate.validate("digest", d / "digest.json")


def _with(item_id, **patch):
    data = copy.deepcopy(GOOD)
    for it in data["items"]:
        if it["id"] == item_id:
            for k, v in patch.items():
                if v is None:
                    it.pop(k, None)
                else:
                    it[k] = v
    return data


def test_fixture_is_valid():
    assert validate.validate("digest", FIX / "digest.json") == []


def test_each_kind_requires_its_fields(tmp_path):
    for item_id, field in [(2, "practice_task"), (2, "procedure"), (3, "known"), (1, "relations"),
                           (4, "supports"), (4, "rehearse_q"), (5, "a")]:
        errs = _errs(tmp_path, _with(item_id, **{field: None}))
        assert errs and field in " ".join(errs), (item_id, field, errs)


def test_kind_must_be_pacer(tmp_path):
    errs = _errs(tmp_path, _with(5, kind="skill"))
    assert errs and "kind" in errs[0]


def test_seg_id_must_exist_and_ids_unique(tmp_path):
    errs = _errs(tmp_path, _with(5, seg_id=99))
    assert any("seg_id 99" in e for e in errs)
    errs = _errs(tmp_path, _with(5, id=4))
    assert any("id 重複" in e for e in errs)


def test_relations_and_supports_point_to_known_concepts(tmp_path):
    errs = _errs(tmp_path, _with(1, relations=[{"to": "nope", "rel": "x"}]))
    assert any("nope" in e for e in errs)
    errs = _errs(tmp_path, _with(1, relations=[{"to": "X", "rel": "x"}]))
    assert any("指向自己" in e for e in errs)
    errs = _errs(tmp_path, _with(1, relations=[]))
    assert any("至少要有一條" in e for e in errs)
    # E 的 supports 只能指 C concept，不能指 term
    errs = _errs(tmp_path, _with(4, supports="A"))
    assert any("supports" in e for e in errs)
    # 沒有 analysis.json 時 relation 只能指同站 C
    data = _with(1, relations=[{"to": "B", "rel": "結論"}])
    (tmp_path / "digest.json").write_text(json.dumps(data, ensure_ascii=False))
    assert any("B" in e for e in validate.validate("digest", tmp_path / "digest.json"))


def test_concept_unique_per_station(tmp_path):
    data = copy.deepcopy(GOOD)
    data["items"].append({"id": 6, "seg_id": 3, "kind": "C", "text": "重複的 X", "concept": "x",
                          "relations": [{"to": "A", "rel": "r"}]})
    errs = _errs(tmp_path, data)
    assert any("只開一筆" in e for e in errs)


def test_concept_cap_per_station(tmp_path):
    data = copy.deepcopy(GOOD)
    for i in range(10):
        data["items"].append({"id": 10 + i, "seg_id": 1, "kind": "C", "text": f"概念 {i}", "concept": f"K{i}",
                              "relations": [{"to": "X", "rel": "r"}]})
    errs = _errs(tmp_path, data)
    assert any("C 有 11 筆，超過 10" in e for e in errs)


def test_text_length_cap(tmp_path):
    errs = _errs(tmp_path, _with(5, text="x" * 81))
    assert errs and "text" in errs[0]


# ---------- digest.py：頁面、積欠、plan.html 標籤 ----------
FX_WS = Path(__file__).parent / "fixtures" / "ws"


def _ws(tmp_path):
    ws = tmp_path / "ws"
    shutil.copytree(FX_WS, ws)
    return ws, ws / "測試影片 C"


def test_load_stations_groups_by_kind_and_links_back(tmp_path):
    ws, _ = _ws(tmp_path)
    st = digest.load_stations(ws)
    assert [s["id"] for s in st] == ["zzzzzzzzzzz"]          # 測試影片 A 沒有 digest.json
    s = st[0]
    assert {k: len(v) for k, v in s["by_kind"].items()} == {"P": 1, "A": 1, "C": 1, "E": 1, "R": 1}
    assert s["items"][0]["key"] == "zzzzzzzzzzz:1"
    assert s["rehearse_from"] == "2026-01-04"                  # created + 1 天才演練 E
    assert s["items"][0]["href"] is None                      # plan.html 還沒 render 就不連


def test_unread_station_is_not_backlog(tmp_path):
    """工作單產出來只是準備；沒按「讀完了」的站不算積欠、也不進 pending。"""
    ws, _ = _ws(tmp_path)
    today = date(2026, 1, 10)
    b = digest.backlog(ws, today)
    assert (b["total"], b["items"], b["unread"]) == (0, 5, 1)
    assert "未讀 1 站不計" in digest.backlog_line(ws)
    assert digest.pending(ws, "due", today) == []
    st = digest.mark(ws, "zzzzzzzzzzz", "read")
    assert st["read"] and json.loads((ws / "digest.state.json").read_text())["zzzzzzzzzzz:read"]["read"]
    # 讀完那天 E 還不到期（隔一天從讀完起算），所以是 4 不是 5
    b = digest.backlog(ws, digest._today())
    assert (b["total"], b["E"], b["unread"]) == (4, 0, 0) and "未讀" not in digest.backlog_line(ws)
    assert digest.load_stations(ws)[0]["rehearse_from"] == (digest._today() + digest.REHEARSE_AFTER).isoformat()
    assert digest.backlog(ws, digest._today() + digest.REHEARSE_AFTER)["E"] == 1
    digest.mark(ws, "zzzzzzzzzzz", "unread")
    assert digest.backlog(ws, today)["total"] == 0


def _read(ws, vid="zzzzzzzzzzz", at="2026-01-03T12:00:00"):
    p = ws / "digest.state.json"
    st = json.loads(p.read_text()) if p.exists() else {}
    st[f"{vid}:read"] = {"read": at}
    p.write_text(json.dumps(st))


def test_backlog_reads_state_file(tmp_path):
    ws, _ = _ws(tmp_path)
    today = date(2026, 1, 10)
    _read(ws)
    b = digest.backlog(ws, today)
    assert (b["P"], b["A"], b["C"], b["E"], b["R"], b["total"], b["items"]) == (1, 1, 1, 1, 1, 5, 5)
    (ws / "digest.state.json").write_text(json.dumps({
        "zzzzzzzzzzz:read": {"read": "2026-01-03T12:00:00"},
        "zzzzzzzzzzz:2": {"done": "2026-01-05T10:00:00"},
        "zzzzzzzzzzz:4": {"rehearsed": "2026-01-06T10:00:00"},
        "zzzzzzzzzzz:5": {"due": "2026-01-20", "ef": 2.5, "reps": 2, "interval": 6},
    }))
    b = digest.backlog(ws, today)
    assert (b["P"], b["E"], b["R"], b["total"]) == (0, 0, 0, 2)
    # 卡片到期那天就算
    assert digest.backlog(ws, date(2026, 1, 20))["R"] == 1
    # E 還沒隔一天不算積欠
    assert digest.backlog(ws, date(2026, 1, 3))["E"] == 0
    assert "P 0" in digest.backlog_line(ws) and "A 1" in digest.backlog_line(ws)


def test_render_embeds_state_and_every_kind(tmp_path):
    ws, _ = _ws(tmp_path)
    (ws / "digest.state.json").write_text(json.dumps({"zzzzzzzzzzz:2": {"done": "2026-01-05T10:00:00", "note": "跑過"}}))
    out = digest.render(ws)
    html = out.read_text()
    assert out.name == "digest.html"
    assert 'id="zzzzzzzzzzz-d5"' in html and 'data-kind="R"' in html
    assert "B 的預設值是多少？" in html and "拿你手上的專案跑一次 A" in html
    assert '"zzzzzzzzzzz:2": {"done"' in html                 # 預設狀態內嵌
    for k in "PACER":
        assert f'class="grp" data-kind="{k}"' in html
    assert "digest.anki.tsv" in html and "digest.state.json" in html


def test_plan_shows_pacer_tags_and_hub_link(tmp_path):
    ws, d = _ws(tmp_path)
    digest.render(ws)
    render.main(["zzzzzzzzzzz", "--workspace", str(ws)])
    html = (d / "plan.html").read_text()
    assert 'class="pacer"' in html
    assert "digest.html#zzzzzzzzzzz-d2" in html                # 第 2 段的 P 連到工作單那一筆
    assert "../digest.html#zzzzzzzzzzz" in html                # 頂部 hub
    # render 過後工作單的「第 N 段 →」才連回 plan.html
    st = digest.load_stations(ws)
    assert st[0]["items"][0]["href"].endswith("plan.html#zzzzzzzzzzz-s1")


def test_publish_copies_digest_as_index_when_no_listen(tmp_path):
    ws, _ = _ws(tmp_path)
    digest.render(ws)
    dist = ws / "dist"
    publish.build(ws, dist)
    assert (dist / "digest.html").exists() and (dist / "index.html").read_text() == (dist / "digest.html").read_text()


def test_pending_and_mark_roundtrip(tmp_path):
    ws, _ = _ws(tmp_path)
    today = date(2026, 1, 10)
    _read(ws)
    rows = digest.pending(ws, "zzzzzzzzzzz", today)
    assert [r["kind"] for r in rows] == ["C", "P", "A", "E", "R"]
    assert rows[1]["practice_task"].startswith("拿你手上") and rows[0]["relations"]
    assert digest.pending(ws, "nope", today) == []
    st = digest.mark(ws, "zzzzzzzzzzz:2", "done", "跑過了")
    assert st["done"] and st["note"] == "跑過了"
    st = digest.mark(ws, "zzzzzzzzzzz:4", "rehearsed", "證明 X")
    assert st["rehearsed"] and st["answer"] == "證明 X"
    st = digest.mark(ws, "zzzzzzzzzzz:5", "grade", "5")
    assert st["reps"] == 1 and st["interval"] == 1 and st["due"] > digest._today().isoformat()
    st = digest.mark(ws, "zzzzzzzzzzz:3", "alike=都在擋")
    assert st["alike"] == "都在擋" and "done" not in st
    kinds = [r["kind"] for r in digest.pending(ws, "due", today)]
    assert kinds == ["C", "A"]                                  # P 做完、E 演練過、R 排到明天
    digest.mark(ws, "zzzzzzzzzzz:2", "undo")
    assert "P" in [r["kind"] for r in digest.pending(ws, "due", today)]
    saved = json.loads((ws / "digest.state.json").read_text())
    assert set(saved) == {"zzzzzzzzzzz:read", "zzzzzzzzzzz:2", "zzzzzzzzzzz:3", "zzzzzzzzzzz:4", "zzzzzzzzzzz:5"}


def test_sm2_matches_expected_schedule():
    d = date(2026, 1, 1)
    s = digest.sm2({}, 5, d)
    assert (s["reps"], s["interval"], s["due"]) == (1, 1, "2026-01-02")
    s = digest.sm2(s, 5, d)
    assert (s["reps"], s["interval"]) == (2, 6)
    s = digest.sm2(s, 3, d)
    assert s["reps"] == 3 and s["interval"] == round(6 * 2.6) and s["ef"] < 2.6
    s = digest.sm2(s, 0, d)
    assert (s["reps"], s["interval"]) == (0, 1) and s["ef"] >= 1.3


def test_cli_mark_rerenders(tmp_path, capsys):
    ws, _ = _ws(tmp_path)
    _read(ws)
    digest.main(["--workspace", str(ws), "--mark", "zzzzzzzzzzz:2", "done", "在", "專案跑了"])
    out = capsys.readouterr().out
    assert "zzzzzzzzzzz:2 →" in out and "P 0" in out
    assert (ws / "digest.html").exists()
    assert json.loads((ws / "digest.state.json").read_text())["zzzzzzzzzzz:2"]["note"] == "在 專案跑了"


def test_estimate_balance_gate(tmp_path, capsys):
    import estimate
    ws, _ = _ws(tmp_path)
    _read(ws)
    assert estimate.print_balance(ws, {"balance": {"max_backlog": 20}}) is True
    out = capsys.readouterr().out
    assert "消化積欠" in out and "上限 20" in out and "⚠" not in out
    assert estimate.print_balance(ws, {"balance": {"max_backlog": 2}}) is False
    assert "⚠" in capsys.readouterr().out
    assert estimate.print_balance(tmp_path / "empty", {}) is True     # 沒 workspace 就不擋


def test_brain_export_merges_concepts_across_stations(tmp_path):
    import brain
    ws, _ = _ws(tmp_path)
    # 第二站也講 X，且有一筆證據掛在 X 上 → 概念檔要合併兩站
    d2 = ws / "測試影片 A: B"
    dg = {"video_id": "abcdefghijk", "items": [
        {"id": 1, "seg_id": 1, "kind": "C", "text": "另一站對 X 的說法", "concept": "X", "relations": [{"to": "Y", "rel": "對照"}]},
        {"id": 2, "seg_id": 1, "kind": "C", "text": "Y", "concept": "Y", "relations": [{"to": "x", "rel": "前提"}]},
        {"id": 3, "seg_id": 1, "kind": "E", "text": "證據", "detail": "另一站的數據", "supports": "x", "rehearse_q": "它證明了什麼？"},
    ]}
    (d2 / "digest.json").write_text(json.dumps(dg, ensure_ascii=False))
    (ws / "digest.state.json").write_text(json.dumps({"zzzzzzzzzzz:2": {"done": "2026-01-05T10:00:00", "note": "跑過"},
                                                      "zzzzzzzzzzz:5": {"due": "2026-02-01"}}))
    n_st, n_c = brain.export(ws, ws / "brain")
    assert (n_st, n_c) == (2, 4)                                   # X, A, B, Y（A/B 只被連到也有檔）
    x = (ws / "brain" / "concepts" / "X.md").read_text()
    assert "X 是問題的核心概念" in x and "另一站對 X 的說法" in x    # 跨站合併（大小寫不分）
    assert "另一站的數據" in x and "—第一個解法→ [[A]]" in x and "[[測試影片 C]]" in x
    assert "[[測試影片]]" in x and (ws / "brain" / "stations" / "測試影片.md").exists()
    assert brain.wl("A: B") == "[[A- B|A: B]]"                       # 冒號換掉，顯示名保留
    st = (ws / "brain" / "stations" / "測試影片 C.md").read_text()
    assert "- [x] 用 A 解 X 的步驟" in st and "心得：跑過" in st and "（下次 2026-02-01）" in st
    assert "- [ ] 作者用 3 個案例證明 B" not in st and "案例 1/2/3 都在 10 秒內收斂 → 證明 [[X]]" in st
    assert "plan.html" in st and "[[X]]" in (ws / "brain" / "README.md").read_text()
    assert brain.safe('a/b:c*"d') == "a-b-c-d"
