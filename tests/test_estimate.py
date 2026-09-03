import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from common import CONFIG, load_yaml
from estimate import estimate_one

META = {"id": "abcdefghijk", "title": "t", "duration": 1800, "filesize": 150e6, "has_any_subs": True}


def test_breakdown_sums_to_total():
    cfg = load_yaml(CONFIG / "estimate.yaml")
    e = estimate_one(META, "false", cfg)
    assert e["total"]["sec"] == round(sum(s["sec"] for s in e["stages"].values()))
    assert set(e["stages"]) == {"fetch", "segment", "shot", "analyze", "render"}
    assert e["vision_extra_if_true"]["sec"] > 0


def test_vision_true_costs_more():
    cfg = load_yaml(CONFIG / "estimate.yaml")
    off, on = estimate_one(META, "false", cfg), estimate_one(META, "true", cfg)
    assert on["total"]["sec"] > off["total"]["sec"]
    assert on["vision_extra_if_true"] is None
