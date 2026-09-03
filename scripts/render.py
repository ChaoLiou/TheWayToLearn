"""/learn-render：把 workspace 裡的 analysis/segments/meta/_overview 組成 plan.html。

用法：uv run scripts/render.py [--workspace workspace] [--out workspace/plan.html] [--ids a,b]
截圖以相對路徑引用，plan.html 放在 workspace/ 下，frames 在 workspace/<id>/frames/。
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEFAULT_WORKSPACE, TEMPLATES, find_video_dir, fmt_dur, fmt_ts, load_json

PALETTE = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#b07aa1", "#76b7b2", "#edc948", "#ff9da7", "#9c755f", "#bab0ac"]


def mm_label(s: str, n: int = 24) -> str:
    """Mermaid 節點文字：去掉會壞語法的字元、截短。"""
    s = re.sub(r'["\[\]{}()<>|#;]', " ", s).strip()
    s = re.sub(r"\s+", " ", s)
    return (s[: n - 1] + "…") if len(s) > n else s


def tip_key(label: str) -> str:
    """tooltip 對照用的 key：去掉所有空白（mermaid 換行後 textContent 會多空白）。"""
    return re.sub(r"\s+", "", label)


class Tips(dict):
    """圖上顯示的短文字 → hover 時顯示的完整說明。"""

    def add(self, label: str, full: str) -> str:
        if full and full != label:
            self[tip_key(label)] = full
        return label


def rel_of(r) -> tuple[str, str]:
    """related 的元素可以是字串或 {term, rel}。"""
    if isinstance(r, dict):
        return r["term"], r.get("rel", "")
    return r, ""


def reasoning_chain(vid: str, analysis: dict, tips: Tips) -> str:
    lines = ["flowchart TD"]
    segs = analysis["segments"]
    for s in segs:
        lab = tips.add(mm_label(f'{s["id"]}. {s["title"]}', 40), f'{s["id"]}. {s["title"]}\n\n{s.get("summary", "")}')
        lines.append(f'  {vid}_{s["id"]}["{lab}"]')
    for a, b in pairwise(segs):
        lab = tips.add(mm_label(a["leads_to"], 24), f"留給下一段：{a['leads_to']}")
        lines.append(f'  {vid}_{a["id"]} -->|"{lab}"| {vid}_{b["id"]}')
    return "\n".join(lines)


def term_tip(t: dict) -> str:
    return f"{t['term']}｜{t.get('zh', '')}\n{t['definition']}"


def mindmap(overview: dict, videos: list[dict], tips: Tips) -> str:
    """層級用不同形狀區分：根=圓、影片=方、段落=圓角、術語=純文字。"""
    lines = [
        "%%{init: {'mindmap': {'padding': 16, 'maxNodeWidth': 240}}}%%",
        "mindmap",
        f"  root(({tips.add(mm_label(overview['topic'], 60), overview['topic'])}))",
    ]
    # mermaid 依「根的直接子節點」分色；只有一支影片時跳過影片層，讓每個段落各自一色
    single = len(videos) == 1
    for v in videos:
        pad = "    "
        if not single:
            lines.append(f"{pad}v[{tips.add(mm_label(v['meta']['title'], 40), v['meta']['title'])}]")
            pad += "  "
        for s in v["analysis"]["segments"]:
            lab = tips.add(mm_label(f"{s['id']}. {s['title']}", 40), f"{s['id']}. {s['title']}\n\n{s.get('summary', '')}")
            lines.append(f"{pad}s({lab})")
            for t in s.get("terms", []):
                lines.append(f"{pad}  {tips.add(mm_label(t['term'], 36), term_tip(t))}")
    return "\n".join(lines)


def term_graph(videos: list[dict], tips: Tips) -> tuple[str, list[dict], list[dict]]:
    """術語依「首次定義的段落」同色；邊有方向與關係說明；A↔B 互相關聯時合成一條雙向邊。
    回傳 (mermaid, edges, legend)。"""
    ids: dict[str, str] = {}
    defs: dict[str, dict] = {}
    group_of: dict[str, int] = {}
    legend: list[dict] = []
    for v in videos:
        for s in v["analysis"]["segments"]:
            gi = None
            for t in s.get("terms", []):
                key = t["term"].strip().lower()
                if key in ids:
                    continue
                if gi is None:
                    gi = len(legend)
                    legend.append({"title": f"{s['id']}. {s['title']}", "color": PALETTE[gi % len(PALETTE)]})
                ids[key] = f"t{len(ids)}"
                defs[key] = t
                group_of[key] = gi
    edges: list[dict] = []
    seen: dict[tuple[str, str], dict] = {}
    for v in videos:
        for s in v["analysis"]["segments"]:
            for t in s.get("terms", []):
                for r in t.get("related", []):
                    name, rel = rel_of(r)
                    a, b = t["term"].strip().lower(), name.strip().lower()
                    if a == b:
                        continue
                    if b not in ids:  # related 指到沒定義的術語：補一個節點
                        ids[b] = f"t{len(ids)}"
                        defs[b] = {"term": name, "definition": "（本片未單獨定義）"}
                    if (b, a) in seen:  # 反向已存在 → 合併成雙向
                        seen[(b, a)]["both"] = True
                        seen[(b, a)]["rel_back"] = rel
                        continue
                    if (a, b) in seen:
                        continue
                    e = {"a": t["term"], "b": name, "rel": rel, "ia": ids[a], "ib": ids[b], "both": False, "rel_back": ""}
                    seen[(a, b)] = e
                    edges.append(e)
    if not edges:
        return "", [], []
    lines = ["%%{init: {'flowchart': {'curve': 'basis', 'nodeSpacing': 24, 'rankSpacing': 60}}}%%", "graph TD"]
    for key, n in ids.items():
        lines.append(f'  {n}["{tips.add(mm_label(defs[key]["term"], 36), term_tip(defs[key]))}"]')
    for gi, g in enumerate(legend):
        members = [ids[k] for k, i in group_of.items() if i == gi]
        lines.append(f"  classDef g{gi} fill:{g['color']},fill-opacity:0.3,stroke:{g['color']},stroke-width:2px")
        lines.append(f"  class {','.join(members)} g{gi}")
    for e in edges:
        if e["both"]:  # 互相引用：雙箭頭，標籤前加 ⇄，hover 看兩個方向
            full = f"{e['a']} → {e['b']}：{e['rel']}；{e['b']} → {e['a']}：{e['rel_back']}"
            lab = tips.add("⇄ " + mm_label(e["rel"], 12), full)
            lines.append(f'  {e["ia"]} <-->|"{lab}"| {e["ib"]}')
        elif e["rel"]:
            lab = tips.add(mm_label(e["rel"], 14), f"{e['a']} → {e['b']}：{e['rel']}")
            lines.append(f'  {e["ia"]} -->|"{lab}"| {e["ib"]}')
        else:
            lines.append(f"  {e['ia']} --> {e['ib']}")
    lines.append("  linkStyle default stroke-width:2px,stroke-opacity:0.7")
    return "\n".join(lines), edges, legend


def load_video(vdir: Path, tips: Tips) -> dict | None:
    need = ["meta.json", "segments.json", "analysis.json"]
    if not all((vdir / n).exists() for n in need):
        return None
    v = {n.split(".")[0]: load_json(vdir / n) for n in need}
    v["id"] = v["meta"]["video_id"]
    v["dir"] = vdir.name
    v["estimate"] = load_json(vdir / "estimate.json") if (vdir / "estimate.json").exists() else None
    v["timings"] = load_json(vdir / "timings.json") if (vdir / "timings.json").exists() else {}
    seg_by_id = {s["id"]: s for s in v["segments"]["segments"]}
    for s in v["analysis"]["segments"]:
        src = seg_by_id.get(s["id"], {})
        s["start"], s["end"] = src.get("start", 0), src.get("end", 0)
        s["summary"] = src.get("summary", "")
        s["shots"] = [sh for sh in src.get("shots", []) if sh.get("file")]
        for sh in s["shots"]:
            sh["href"] = f"{quote(vdir.name)}/{quote(sh['file'])}"
            sh["seg_title"] = s["title"]
    v["all_shots"] = [sh for s in v["analysis"]["segments"] for sh in s["shots"]]
    for i, sh in enumerate(v["all_shots"]):
        sh["idx"] = i
    v["chain_mermaid"] = reasoning_chain(v["id"].replace("-", "_"), v["analysis"], tips)
    # 圖的文字描述（預設收合）
    v["chain_desc"] = [
        {"id": s["id"], "title": s["title"], "leads_to": s["leads_to"]} for s in v["analysis"]["segments"]
    ]
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ids", help="只包含這些 id（逗號分隔），預設全部")
    args = ap.parse_args(argv)

    ws = args.workspace
    ov_path = ws / "_overview.json"
    if not ov_path.exists():
        raise SystemExit(f"缺 {ov_path}：先由 agent 依 rules/overview.md 產生")
    overview = load_json(ov_path)
    order = [o["video_id"] for o in overview["outline"]]
    if args.ids:
        order = [i for i in args.ids.split(",") if i]
    videos, tips = [], Tips()
    for vid in order:
        vdir = find_video_dir(vid, ws)
        v = load_video(vdir, tips) if vdir else None
        if v is None:
            print(f"略過 {vid}：缺 meta/segments/analysis")
            continue
        videos.append(v)
    if not videos:
        raise SystemExit("沒有任何可 render 的影片")

    tg, edges, legend = term_graph(videos, tips)
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    env.filters["ts"] = fmt_ts
    env.filters["dur"] = fmt_dur
    env.filters["yt_search"] = lambda q: "https://www.youtube.com/results?search_query=" + quote(q)
    html = env.get_template("plan.html.j2").render(
        overview=overview,
        videos=videos,
        mindmap=mindmap(overview, videos, tips),
        term_graph=tg,
        term_edges=edges,
        term_legend=legend,
        tips=tips,
        generated=datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M"),
    )
    out = args.out or ws / "plan.html"
    out.write_text(html, encoding="utf-8")
    print(f"OK → {out}")


if __name__ == "__main__":
    main()
