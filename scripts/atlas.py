"""/learn-atlas：學習地圖。workspace 下每個影片資料夾是一個 waypoint，atlas.json 記 route 與 region。

  uv run scripts/atlas.py --status      # 列出所有 waypoint、哪些還沒進 atlas.json、新站與既有站的共同術語
  uv run scripts/atlas.py               # 驗證 atlas.json 並 render workspace/atlas.html
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import jsonschema
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    DEFAULT_WORKSPACE,
    SCHEMAS,
    fmt_dur,
    load_json,
    print_step,
    template_dirs,
)
from i18n import Strings, norm_lang
from render import PALETTE, Tips, mm_label

ROUTE_ARROW = {"prerequisite": "-->", "deepens": "-->", "contrasts": "<-->", "applies": "-->", "related": "---"}


def load_waypoints(ws: Path) -> list[dict]:
    wps = []
    for d in sorted(p for p in ws.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        if not all((d / f).exists() for f in ("meta.json", "_overview.json", "analysis.json")):
            continue
        meta, ov, an = (load_json(d / f) for f in ("meta.json", "_overview.json", "analysis.json"))
        terms = [t["term"] for s in an["segments"] for t in s.get("terms", [])]
        wps.append({
            "id": meta["video_id"], "dir": d.name, "title": meta["title"], "channel": meta.get("channel"),
            "duration": meta.get("duration", 0), "url": meta.get("url"), "topic": ov["topic"],
            "takeaways": ov.get("takeaways", []), "summary": ov["summary"], "terms": terms,
            "prerequisites": [p["concept"] for p in ov.get("prerequisites", [])],
            "n_segments": len(an["segments"]), "has_plan": (d / "plan.html").exists(),
            "output_lang": norm_lang(meta.get("output_lang")),
            "href": f"{quote(d.name)}/plan.html",
        })
    return wps


def load_atlas(ws: Path) -> dict:
    p = ws / "atlas.json"
    return load_json(p) if p.exists() else {"regions": [], "routes": []}


def check_atlas(atlas: dict, wps: list[dict]) -> list[str]:
    errs = [f"schema: {'/'.join(map(str, e.path))}: {e.message}"
            for e in jsonschema.Draft202012Validator(load_json(SCHEMAS / "atlas.schema.json")).iter_errors(atlas)]
    if errs:
        return errs
    ids = {w["id"] for w in wps}
    seen: dict[str, str] = {}
    for r in atlas["regions"]:
        for w in r["waypoints"]:
            if w not in ids:
                errs.append(f"region {r['id']}: 未知 waypoint {w}")
            if w in seen:
                errs.append(f"waypoint {w} 同時在 region {seen[w]} 與 {r['id']}")
            seen[w] = r["id"]
    pairs = set()
    for e in atlas["routes"]:
        for k in ("from", "to"):
            if e[k] not in ids:
                errs.append(f"route {e['from']}→{e['to']}: 未知 waypoint {e[k]}")
        if e["from"] == e["to"]:
            errs.append(f"route {e['from']}: from 與 to 相同")
        key = frozenset((e["from"], e["to"]))
        if key in pairs:
            errs.append(f"route {e['from']}↔{e['to']}: 兩站之間只能有一條 route")
        pairs.add(key)
    return errs


def status(ws: Path) -> None:
    wps, atlas = load_waypoints(ws), load_atlas(ws)
    linked = {w for r in atlas["regions"] for w in r["waypoints"]} | {x for e in atlas["routes"] for x in (e["from"], e["to"])}
    print(f"workspace: {ws}  ·  {len(wps)} 個 waypoint  ·  atlas.json {'存在' if (ws / 'atlas.json').exists() else '不存在'}")
    for w in wps:
        mark = "已在地圖" if w["id"] in linked else "★ 新站，尚未連進地圖"
        print(f"\n[{w['id']}] {w['title']}  —  {mark}")
        print(f"   topic: {w['topic']}")
        if w["takeaways"]:
            print("   takeaways: " + "；".join(w["takeaways"]))
        else:
            print("   !! _overview.json 沒有 takeaways，先補")
    new = [w for w in wps if w["id"] not in linked]
    if len(wps) < 2:
        print("\n只有一站，還不需要地圖。")
        return
    if not new:
        print("\n所有站都已在地圖上。")
    for w in new:
        print(f"\n== 新站 {w['id']} 與既有站的共同術語 ==")
        mine = {t.lower(): t for t in w["terms"]}
        for o in wps:
            if o["id"] == w["id"]:
                continue
            common = sorted({mine[k] for k in mine if k in {t.lower() for t in o["terms"]}})
            pre_hit = [p for p in w["prerequisites"] if any(p.lower() in t.lower() or t.lower() in p.lower() for t in o["takeaways"] + o["terms"])]
            print(f"   ↔ [{o['id']}] {o['title']}")
            print(f"      共同術語 {len(common)}：{'、'.join(common) if common else '（無）'}")
            if pre_hit:
                print(f"      新站的 prerequisites 被此站涵蓋：{'、'.join(pre_hit)}  → 可能是 prerequisite")
    errs = check_atlas(atlas, wps)
    if errs:
        print("\natlas.json 問題：")
        for e in errs:
            print("  -", e)
    print(f"\n規則在 rules/atlas.md；更新 {ws / 'atlas.json'} 後跑 uv run scripts/atlas.py")


def map_mermaid(wps: list[dict], atlas: dict, tips: Tips, S: Strings) -> tuple[str, dict, list[dict]]:
    by_id = {w["id"]: w for w in wps}
    nid = {w["id"]: f"w{i}" for i, w in enumerate(wps)}
    lines = ["%%{init: {'flowchart': {'curve': 'basis', 'nodeSpacing': 40, 'rankSpacing': 70}}}%%", "graph LR"]
    links: dict[str, str] = {}
    placed = set()
    legend = []

    def node(w, indent="  "):
        lab = tips.add(mm_label(w["title"], 34), f"{w['title']}\n{w['topic']}\n\n" + "\n".join("• " + t for t in w["takeaways"]))
        links[lab.replace(" ", "")] = w["href"]
        lines.append(f'{indent}{nid[w["id"]]}["{lab}"]')

    for gi, r in enumerate(atlas["regions"]):
        color = PALETTE[gi % len(PALETTE)]
        legend.append({"name": r["name"], "color": color, "id": r["id"]})
        lines.append(f'  subgraph {r["id"]}["{mm_label(r["name"], 30)}"]')
        members = []
        for wid in r["waypoints"]:
            if wid in by_id:
                node(by_id[wid], "    "); placed.add(wid); members.append(nid[wid])
        lines.append("  end")
        lines.append(f"  style {r['id']} fill:transparent,stroke:{color},stroke-width:2px,stroke-dasharray:6 3")
        if members:
            lines.append(f"  classDef {r['id']} fill:{color},fill-opacity:0.3,stroke:{color},stroke-width:2px")
            lines.append(f"  class {','.join(members)} {r['id']}")
    for w in wps:
        if w["id"] not in placed:
            node(w)
    for e in atlas["routes"]:
        if e["from"] not in nid or e["to"] not in nid:
            continue
        lab = tips.add(S.route(e["type"]), f"{S.route(e['type'])}: {by_id[e['from']]['title']} → {by_id[e['to']]['title']}\n{e['via']}")
        lines.append(f'  {nid[e["from"]]} {ROUTE_ARROW[e["type"]]}|"{lab}"| {nid[e["to"]]}')
    lines.append("  linkStyle default stroke-width:2px,stroke-opacity:0.8")
    return "\n".join(lines), links, legend


def render(ws: Path) -> Path:
    wps, atlas = load_waypoints(ws), load_atlas(ws)
    errs = check_atlas(atlas, wps)
    if errs:
        raise SystemExit("atlas.json 有問題：\n  - " + "\n  - ".join(errs))
    by_id = {w["id"]: w for w in wps}
    for w in wps:
        w["routes_out"] = [dict(e, other=by_id.get(e["to"])) for e in atlas["routes"] if e["from"] == w["id"] and e["to"] in by_id]
        w["routes_in"] = [dict(e, other=by_id.get(e["from"])) for e in atlas["routes"] if e["to"] == w["id"] and e["from"] in by_id]
        w["region"] = next((r for r in atlas["regions"] if w["id"] in r["waypoints"]), None)
    regions = []
    for gi, r in enumerate(atlas["regions"]):
        regions.append(dict(r, color=PALETTE[gi % len(PALETTE)], members=[by_id[x] for x in r["waypoints"] if x in by_id]))
    unplaced = [w for w in wps if w["region"] is None]
    # 地圖語言：atlas.json 的 lang，否則取多數站的 output_lang
    lang = atlas.get("lang") or (max({w["output_lang"] for w in wps}, key=[w["output_lang"] for w in wps].count) if wps else None)
    S = Strings(norm_lang(lang))
    tips = Tips()
    mm, links, legend = map_mermaid(wps, atlas, tips, S)
    env = Environment(loader=FileSystemLoader(template_dirs()), autoescape=True)
    env.filters["dur"] = fmt_dur
    html = env.get_template("atlas.html.j2").render(
        waypoints=wps, regions=regions, unplaced=unplaced, routes=atlas["routes"], by_id=by_id,
        map_mermaid=mm, links=links, legend=legend, tips=tips, S=S,
        generated=datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M"),
    )
    out = ws / "atlas.html"
    out.write_text(html, encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args(argv)
    if args.status:
        status(args.workspace)
        return
    out = render(args.workspace)
    print(f"OK → {out}")
    print_step("atlas", str(out))


if __name__ == "__main__":
    main()
