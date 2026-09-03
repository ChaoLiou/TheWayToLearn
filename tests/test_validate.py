import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate import check_analysis, check_schema, check_segments

FX = Path(__file__).parent / "fixtures/ws"
ANALYSIS = json.loads((FX / "測試影片 A: B/analysis.json").read_text())
SEGMENTS = json.loads((FX / "測試影片 A: B/segments.json").read_text())
OVERVIEW = json.loads((FX / "測試影片 A: B/_overview.json").read_text())


def test_fixtures_pass():
    assert check_schema("analysis", ANALYSIS) == []
    assert check_analysis(ANALYSIS) == []
    assert check_schema("segments", SEGMENTS) == []
    assert check_segments(SEGMENTS) == []
    assert check_schema("overview", OVERVIEW) == []


def test_forward_reference_rejected():
    a = copy.deepcopy(ANALYSIS)
    a["segments"][0]["explanation"] = "後面第 3 段會講"
    assert any("前向引用" in e for e in check_analysis(a))


def test_duplicate_term_rejected():
    a = copy.deepcopy(ANALYSIS)
    a["segments"][2]["terms"].append({"term": "x", "definition": "again"})
    assert any("已在第 1 段" in e for e in check_analysis(a))


def test_missing_builds_on_rejected():
    a = copy.deepcopy(ANALYSIS)
    a["segments"][1]["builds_on"] = ""
    assert check_schema("analysis", a)


def test_next_steps_must_be_three():
    o = copy.deepcopy(OVERVIEW)
    o["next_steps"].pop()
    assert check_schema("overview", o)


def test_shot_outside_segment():
    s = copy.deepcopy(SEGMENTS)
    s["segments"][0]["shots"][0]["t"] = 999
    assert any("不在段落時間內" in e for e in check_segments(s))
