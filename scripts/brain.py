"""second brain：把各站的 digest.json（PACER 工作單）與進度匯出成 Obsidian 能直接開的 markdown vault。
一站一檔（stations/）、一個概念一檔（concepts/，同名概念跨站合併，E 證據掛在它證明的概念下），
`[[wikilink]]` 互連，Obsidian 的 graph view 就是你的 knowledge network。

用法：uv run scripts/brain.py [--workspace DIR] [--out DIR]     # 預設 workspace/brain/
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEFAULT_WORKSPACE, load_json, write_text
from digest import KINDS, load_state, load_stations

_BAD = re.compile(r'[\\/:*?"<>|#^\[\]]+')
HEAD = {"P": "P 程序 → 練習", "A": "A 類比 → 批判", "C": "C 概念 → 地圖", "E": "E 證據 → 演練", "R": "R 參考 → 回想"}


def safe(name: str) -> str:
    return _BAD.sub("-", name).strip(" .")[:120] or "untitled"


def wl(name: str) -> str:
    """[[wikilink]]：檔名要過 safe()，顯示文字保留原名。"""
    f = safe(name)
    return f"[[{f}]]" if f == name else f"[[{f}|{name}]]"


def _terms(ws: Path, s: dict) -> dict[str, dict]:
    """analysis.json 的術語表（小寫 → term 物件），概念檔用它補定義。"""
    p = ws / s["dir"] / "analysis.json"
    if not p.exists():
        return {}
    return {t["term"].lower(): t for seg in load_json(p)["segments"] for t in seg.get("terms", [])}


def _box(done: bool) -> str:
    return "- [x]" if done else "- [ ]"


def station_md(ws: Path, s: dict, state: dict) -> str:
    plan = f"../../{quote(s['dir'])}/plan.html"
    out = [
        "---",
        f"video_id: {s['id']}",
        f"title: \"{s['title']}\"",
        f"url: {s['url'] or ''}",
        f"channel: \"{s['channel'] or ''}\"",
        f"region: \"{s['category'] or ''}\"",
        f"created: {s['created_ymd']}",
        "tags: [station]",
        "---",
        f"# {s['title']}",
        f"[原始來源]({s['url']}) · [文字說明]({plan})" if s["url"] else f"[文字說明]({plan})",
        "",
    ]
    for k in KINDS:
        items = s["by_kind"][k]
        if not items:
            continue
        out.append(f"## {HEAD[k]}")
        for it in items:
            x = state.get(it["key"], {})
            seg = f"（第 {it['seg_id']} 段）"
            if k == "P":
                out.append(f"{_box(bool(x.get('done')))} {it['text']} {seg}")
                out.append("  - 步驟：" + " → ".join(it["procedure"]))
                out.append(f"  - 今天就做：{it['practice_task']}")
                if x.get("note"):
                    out.append(f"  - 心得：{x['note']}")
            elif k == "A":
                out.append(f"{_box(bool(x.get('done')))} {it['text']} {seg}")
                out.append(f"  - 新：{it['new']}　⇄　像：{it['known']}")
                for f, label in (("alike", "哪裡像"), ("unlike", "哪裡不像"), ("breaks", "何時失效")):
                    if x.get(f):
                        out.append(f"  - {label}：{x[f]}")
            elif k == "C":
                out.append(f"{_box(bool(x.get('done')))} {wl(it['concept'])} — {it['text']} {seg}")
            elif k == "E":
                out.append(f"{_box(bool(x.get('rehearsed')))} {it['detail']} → 證明 {wl(it['supports'])} {seg}")
                out.append(f"  - 演練：{it['rehearse_q']}")
                if x.get("answer"):
                    out.append(f"  - 回答：{x['answer']}")
            elif k == "R":
                due = f"（下次 {x['due']}）" if x.get("due") else "（新卡）"
                out.append(f"- **{it['q']}** → {it['a']} {due}")
        out.append("")
    return "\n".join(out)


def build_concepts(ws: Path, stations: list[dict]) -> dict[str, dict]:
    """小寫概念名 → {name, defs[], rels[], evidence[], sources{}, term}；跨站合併。"""
    cs: dict[str, dict] = {}

    def get(name: str) -> dict:
        return cs.setdefault(name.lower(), {"name": name, "defs": [], "rels": [], "evidence": [], "sources": {}, "term": None})

    for s in stations:
        terms = _terms(ws, s)
        link = wl(s["title"])
        for it in s["by_kind"]["C"]:
            c = get(it["concept"])
            c["defs"].append((it["text"], link, it["seg_id"]))
            c["sources"][s["id"]] = link
            if not c["term"] and it["concept"].lower() in terms:
                c["term"] = terms[it["concept"].lower()]
            for r in it["relations"]:
                c["rels"].append((r["rel"], r["to"], link))
                get(r["to"])["sources"].setdefault(s["id"], link)
        for it in s["by_kind"]["E"]:
            c = get(it["supports"])
            c["evidence"].append((it["detail"], link, it["seg_id"]))
            c["sources"].setdefault(s["id"], link)
    return cs


def concept_md(c: dict) -> str:
    out = ["---", "tags: [concept]"]
    if c["term"] and c["term"].get("zh"):
        out.append(f"aliases: [\"{c['term']['zh']}\"]")
    out += ["---", f"# {c['name']}"]
    if c["term"]:
        out.append(f"> {c['term'].get('definition', '')}")
        if c["term"].get("more"):
            out.append(f"> {c['term']['more']}")
    if c["defs"]:
        out.append("\n## 是什麼")
        out += [f"- {t}（{link} 第 {seg} 段）" for t, link, seg in c["defs"]]
    if c["rels"]:
        out.append("\n## 連到")
        out += [f"- —{rel}→ {wl(to)}（{link}）" for rel, to, link in c["rels"]]
    if c["evidence"]:
        out.append("\n## 證據")
        out += [f"- {d}（{link} 第 {seg} 段）" for d, link, seg in c["evidence"]]
    if c["sources"]:
        out.append("\n## 來源")
        out += [f"- {link}" for link in c["sources"].values()]
    return "\n".join(out) + "\n"


def export(ws: Path, out: Path) -> tuple[int, int]:
    stations = load_stations(ws)
    state = load_state(ws)
    (out / "stations").mkdir(parents=True, exist_ok=True)
    (out / "concepts").mkdir(parents=True, exist_ok=True)
    for s in stations:
        write_text(out / "stations" / f"{safe(s['title'])}.md", station_md(ws, s, state))
    cs = build_concepts(ws, stations)
    for c in cs.values():
        write_text(out / "concepts" / f"{safe(c['name'])}.md", concept_md(c))
    idx = ["# second brain", "", f"更新於 {datetime.now(UTC).astimezone():%Y-%m-%d %H:%M}",
           "由 `scripts/brain.py` 從各站 `digest.json` + `digest.state.json` 匯出；改內容請改那兩個檔再重跑，這裡會被覆蓋。", "",
           "## 站", *[f"- {wl(s['title'])}（{s['created_ymd']}）" for s in stations], "",
           "## 概念", *[f"- {wl(c['name'])}" for c in sorted(cs.values(), key=lambda c: c["name"].lower())], ""]
    write_text(out / "README.md", "\n".join(idx))
    return len(stations), len(cs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--out", type=Path, help="vault 目錄，預設 <workspace>/brain")
    args = ap.parse_args(argv)
    out = args.out or (args.workspace / "brain")
    n_st, n_c = export(args.workspace, out)
    print(f"{n_st} 站、{n_c} 個概念 → {out}（用 Obsidian 開這個資料夾）")


if __name__ == "__main__":
    main()
