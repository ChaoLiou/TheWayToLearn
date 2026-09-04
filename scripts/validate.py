"""驗證 agent 產出的 JSON：schema + 線性推進硬規則（rules/narrative.md）。

用法：uv run scripts/validate.py <segments|analysis|overview> <file.json>
非 0 exit = 有錯，錯誤逐行印出。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SCHEMAS, load_json

_FWD_REF = re.compile(r"第\s*(\d+)\s*段")


def check_schema(kind: str, data) -> list[str]:
    schema = load_json(SCHEMAS / f"{kind}.schema.json")
    v = jsonschema.Draft202012Validator(schema)
    return [f"schema: {'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in v.iter_errors(data)]


def check_segments(data) -> list[str]:
    errs = []
    segs = data["segments"]
    for i, s in enumerate(segs, 1):
        if s["id"] != i:
            errs.append(f"segment {s['id']}: id 必須從 1 連續遞增（位置 {i}）")
        if s["end"] <= s["start"]:
            errs.append(f"segment {s['id']}: end 必須 > start")
        if i > 1 and s["start"] < segs[i - 2]["end"] - 1:
            errs.append(f"segment {s['id']}: start 與上一段 end 重疊")
        for sh in s.get("shots", []):
            if not (s["start"] <= sh["t"] <= s["end"]):
                errs.append(f"segment {s['id']}: shot t={sh['t']} 不在段落時間內")
    return errs


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def check_analysis(data, transcript: dict | None = None) -> list[str]:
    """rules/narrative.md 硬規則 1–4、6。transcript 給了才比對 issues 的逐字引文。"""
    errs = []
    segs = data["segments"]
    seen_terms: dict[str, int] = {}
    full = _norm(" ".join(e["text"] for e in transcript["events"])) if transcript else None
    for i, s in enumerate(segs, 1):
        if s["id"] != i:
            errs.append(f"segment {s['id']}: id 必須從 1 連續遞增")
        # 規則 3：前向引用
        for field in ("builds_on", "reasoning", "explanation", "leads_to"):
            for m in _FWD_REF.finditer(s.get(field, "")):
                if int(m.group(1)) > i:
                    errs.append(f"segment {i}.{field}: 前向引用「第{m.group(1)}段」")
        # 規則 4：術語只在首次出現的段落定義
        for t in s.get("terms", []):
            key = t["term"].strip().lower()
            if key in seen_terms:
                errs.append(f"segment {i}: 術語「{t['term']}」已在第 {seen_terms[key]} 段定義過")
            else:
                seen_terms[key] = i
        # 規則 6：勘誤引文必須逐字來自 transcript
        for j, iss in enumerate(s.get("issues", []), 1):
            if full is not None and _norm(iss["quote"]) not in full:
                errs.append(f"segment {i}.issues[{j}]: quote 不是 transcript 逐字引文：「{iss['quote'][:40]}…」")
    return errs


def check_overview(data) -> list[str]:
    return []


def check_narration(data) -> list[str]:
    errs = []
    for i, b in enumerate(data["blocks"], 1):
        if b["kind"] == "say":
            if not b.get("text", "").strip():
                errs.append(f"blocks[{i}]: kind=say 必須有 text")
            elif len(b["text"]) > 90:
                errs.append(f"blocks[{i}]: say 太長（{len(b['text'])} 字），拆成多個 block")
        else:
            if b.get("start") is None or b.get("end") is None:
                errs.append(f"blocks[{i}]: kind=clip 必須有 start 與 end")
            elif b["end"] <= b["start"]:
                errs.append(f"blocks[{i}]: clip 的 end 必須大於 start")
            elif b["end"] - b["start"] > 180:
                errs.append(f"blocks[{i}]: clip {b['end'] - b['start']:.0f} 秒太長（上限 180 秒）")
    return errs


CHECKS = {"segments": check_segments, "analysis": check_analysis, "overview": check_overview,
          "narration": check_narration}


def validate(kind: str, path: Path) -> list[str]:
    data = load_json(path)
    errs = check_schema(kind, data)
    if errs:
        return errs
    if kind == "analysis":
        tp = path.parent / "transcript.json"
        return check_analysis(data, load_json(tp) if tp.exists() else None)
    return CHECKS[kind](data)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=list(CHECKS))
    ap.add_argument("file", type=Path)
    args = ap.parse_args(argv)
    errs = validate(args.kind, args.file)
    if errs:
        print(f"FAIL {args.file}: {len(errs)} 個問題")
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print(f"OK {args.file}")


if __name__ == "__main__":
    main()
