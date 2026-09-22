"""/learn-atlas：文字說明列表（atlas.html）。workspace 下每個影片資料夾是一個 waypoint，atlas.json 記 route 與 region。

  uv run scripts/atlas.py --status      # 列出所有 waypoint、哪些還沒進 atlas.json、新站與既有站的共同術語
  uv run scripts/atlas.py               # 驗證 atlas.json 並 render workspace/atlas.html
  uv run scripts/atlas.py --merge p.json   # 把新站的 route/region 併進 atlas.json（-  = 讀 stdin）再 render
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import jsonschema
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blog import IMG_EXT
from common import (
    DEFAULT_WORKSPACE,
    SCHEMAS,
    STEP_CMD,
    STEPS,
    fmt_dur,
    fmt_ts,
    is_blog,
    load_json,
    locked,
    print_step,
    save_json,
    template_dirs,
    write_text,
)
from i18n import Strings, norm_lang
from render import PALETTE

# 舊的五種型態 → 現在的兩種（--migrate-routes 用）
ROUTE_MIGRATE = {"prerequisite": "next", "deepens": "next", "applies": "next",
                 "contrasts": "related", "related": "related"}


def fmt_ymd(s: str | None) -> str:
    """yt-dlp 的 upload_date（20210315）→ 2021-03-15。"""
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if s and len(s) == 8 and s.isdigit() else (s or "")


def days_since(ymd: str | None) -> int | None:
    """yt-dlp 的 upload_date（20210315）→ 距今幾天；格式不對回 None。"""
    if not (ymd and len(ymd) == 8 and ymd.isdigit()):
        return None
    up = datetime.strptime(ymd, "%Y%m%d").replace(tzinfo=UTC).date()
    return (datetime.now(UTC).astimezone().date() - up).days


def thumb(d: Path) -> str | None:
    """離線用的備援縮圖：該站第一張截圖；沒截圖就回 None。前端主圖是 YouTube 縮圖。"""
    frames = sorted(p for p in (d / "frames").iterdir() if p.suffix.lower() in IMG_EXT) if (d / "frames").is_dir() else []
    return f"{quote(d.name)}/frames/{quote(frames[0].name)}" if frames else None


def pipeline(d: Path, in_atlas: bool, multi: bool, S: Strings) -> list[dict]:
    """這一站在十步 pipeline 上走到哪。state：done｜partial｜todo｜skip｜running。
    partial 是「做過但缺一塊」——例如聽力版做了卻沒挑原聲片段、原聲沒翻譯、還沒做翻譯配音。"""
    seg = load_json(d / "segments.json") if (d / "segments.json").exists() else None
    lesson = load_json(d / "lesson.json") if (d / "lesson.json").exists() else None
    segs = seg["segments"] if seg else []
    clips = [c for x in segs for c in x.get("clips", [])]
    shots = [sh for x in segs for sh in x.get("shots", [])]

    def shot_state():
        if not seg:
            return "todo", ""
        if seg.get("shots_mode") == "none" or not shots:
            return "skip", S.n_no_shots
        if all(sh.get("file") for sh in shots):
            return "done", ""
        return "partial", ""

    def narrate_state():
        if (d / "lesson.status.json").exists() and not lesson:
            return "running", S.n_building
        if not lesson:
            return "todo", ""
        if not clips:
            return "partial", S.n_no_clips
        if any(not c.get("translation") for c in clips):
            return "partial", S.n_no_trans
        if not lesson.get("dub"):
            return "partial", S.n_no_dub
        return "done", ""

    def listen_state():
        # podcast 頁是 workspace 層級的：這站沒有聽力版就沒東西可列；有的話要 listen.html 與這站的 captions.js 都在
        if not lesson:
            return "skip", S.n_no_lesson
        ws = d.parent
        if (ws / "listen.html").exists() and (d / "captions.js").exists():
            return "done", ""
        return "todo", ""

    raw = {
        "estimate": (("done", "") if (d / "estimate.json").exists() else ("todo", "")),
        "fetch": (("done", "") if (d / "transcript.json").exists() else ("todo", "")),
        "segment": (("done", "") if seg else ("todo", "")),
        "shot": shot_state(),
        "analyze": (("done", "") if (d / "analysis.json").exists() else ("todo", "")),
        "digest": (("done", "") if (d / "digest.json").exists() else ("todo", "")),
        "render": (("done", "") if (d / "plan.html").exists() else ("todo", "")),
        "atlas": (("done", "") if in_atlas else ("todo", "")) if multi else ("skip", ""),
        "narrate": narrate_state(),
        "listen": listen_state(),
    }
    return [{"key": k, "n": i, "name": getattr(S, f"stg_{k}"), "state": raw[k][0], "note": raw[k][1]}
            for i, (k, _) in enumerate(STEPS, 1)]


def next_actions(w: dict, stages: list[dict], S: Strings) -> list[dict]:
    """「繼續做」選單：每個未完成的階段各一個選項，prompt 讓使用者複製去貼給 Claude Code。"""
    note_key = {S.n_no_clips: "np_note_clips", S.n_no_trans: "np_note_trans", S.n_no_dub: "np_note_dub"}
    left = [x for x in stages if x["state"] in ("todo", "partial")]

    def prompt(seq: list[dict]) -> str:
        cmds = [f"{i}. {STEP_CMD[x['key']]} {w['id']}" for i, x in enumerate(seq, 1)]
        notes = [getattr(S, note_key[x["note"]]) for x in seq if x["note"] in note_key]
        if len(seq) == 1 and not notes:
            return f"{STEP_CMD[seq[0]['key']]} {w['id']}"
        body = [S.f("np_lead", title=w["title"], id=w["id"]), "", *cmds, ""]
        return "\n".join([*body, *notes, S.np_tail])

    acts = [{"label": S.f("np_only" if i == 0 else "np_to", stage=x["name"]),
             "desc": S.f("np_steps", n=i + 1, list="、".join(y["name"] for y in left[:i + 1])),
             "prompt": prompt(left[:i + 1])}
            for i, x in enumerate(left)]
    if not acts:  # 全部做完了，還是給重跑最後兩步的入口
        acts = [{"label": S.f("np_redo", stage=x["name"]), "desc": S.np_redo_desc,
                 "prompt": f"{STEP_CMD[x['key']]} {w['id']} --force"}
                for x in stages if x["key"] in ("analyze", "digest", "render", "narrate")]
    return acts


def load_waypoints(ws: Path) -> list[dict]:
    wps = []
    for d in sorted(p for p in ws.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        if not all((d / f).exists() for f in ("meta.json", "_overview.json", "analysis.json")):
            continue
        meta, ov, an = (load_json(d / f) for f in ("meta.json", "_overview.json", "analysis.json"))
        terms = [t["term"] for s in an["segments"] for t in s.get("terms", [])]
        issues = [dict(i, seg_id=s["id"], seg_title=s["title"])
                  for s in an["segments"] for i in s.get("issues", [])]
        wps.append({
            "id": meta["video_id"], "dir": d.name, "title": meta["title"], "channel": meta.get("channel"),
            "duration": meta.get("duration", 0), "url": meta.get("url"), "topic": ov["topic"],
            "takeaways": ov.get("takeaways", []), "summary": ov["summary"], "terms": terms,
            "prerequisites": [p["concept"] for p in ov.get("prerequisites", [])],
            "n_segments": len(an["segments"]), "has_plan": (d / "plan.html").exists(),
            "issues": issues,
            "n_wrong": sum(1 for i in issues if i["level"] == "wrong"),
            "n_debatable": sum(1 for i in issues if i["level"] != "wrong"),
            "output_lang": norm_lang(meta.get("output_lang")),
            "href": f"{quote(d.name)}/plan.html",
            "upload_date": fmt_ymd(meta.get("upload_date")),
            "upload_days": days_since(meta.get("upload_date")),
            "thumb": thumb(d),
            "kind": "blog" if is_blog(meta) else "youtube",
            # 文章沒有 YouTube 縮圖：用 og:image，沒有就退回第一張文中圖片
            "yt_thumb": (meta.get("thumbnail") or None) if is_blog(meta)
            else f"https://i.ytimg.com/vi/{meta['video_id']}/mqdefault.jpg",
        })
    return wps


def errata_stats(w: dict, S: Strings) -> dict:
    """這一站（單支影片）的勘誤數：wrong = 確定錯誤／已過時（紅）；debatable = 見仁見智（橘）。
    卡片上只顯示件數，點下去開視窗看整張表。"""
    a = {"wrong": w["n_wrong"], "debatable": w["n_debatable"], "segments": w["n_segments"]}
    a["clean"] = not (a["wrong"] or a["debatable"])
    a["tip"] = S.f("err_tip_ok" if a["clean"] else "err_tip",
                   seg=a["segments"], w=a["wrong"], d=a["debatable"])
    return a


def load_atlas(ws: Path) -> dict:
    p = ws / "atlas.json"
    return load_json(p) if p.exists() else {"regions": [], "routes": []}


def merge_atlas(atlas: dict, patch: dict) -> dict:
    """把 patch 併進 atlas：同一對站的 route 以 patch 為準，region 依 id 合併 waypoints。
    用 patch 而不是整份覆寫，兩支影片同時跑 atlas 才不會互相蓋掉對方的 route。"""
    routes = {frozenset((e["from"], e["to"])): e for e in atlas["routes"]}
    for e in patch.get("routes", []):
        routes[frozenset((e["from"], e["to"]))] = e
    regions = {r["id"]: dict(r) for r in atlas["regions"]}
    for r in patch.get("regions", []):
        old = regions.get(r["id"])
        wps = list(dict.fromkeys((old["waypoints"] if old else []) + r.get("waypoints", [])))
        regions[r["id"]] = {**(old or {}), **r, "waypoints": wps}
    for r in patch.get("regions", []):  # 一個 waypoint 只能屬於一個 region：從別區移掉
        moved = set(r.get("waypoints", []))
        for other in regions.values():
            if other["id"] != r["id"]:
                other["waypoints"] = [w for w in other["waypoints"] if w not in moved]
    out = {**atlas, "regions": [r for r in regions.values() if r["waypoints"]], "routes": list(routes.values())}
    if patch.get("lang"):
        out["lang"] = patch["lang"]
    return out


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
        mark = "已連結" if w["id"] in linked else "★ 新站，尚未連結其他站"
        print(f"\n[{w['id']}] {w['title']}  —  {mark}")
        print(f"   topic: {w['topic']}")
        if w["takeaways"]:
            print("   takeaways: " + "；".join(w["takeaways"]))
        else:
            print("   !! _overview.json 沒有 takeaways，先補")
    new = [w for w in wps if w["id"] not in linked]
    if len(wps) < 2:
        print("\n只有一站，還不需要 route。")
        return
    if not new:
        print("\n所有站都已連結。")
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
    # 介面語言：atlas.json 的 lang，否則取多數站的 output_lang
    lang = atlas.get("lang") or (max({w["output_lang"] for w in wps}, key=[w["output_lang"] for w in wps].count) if wps else None)
    S = Strings(norm_lang(lang))
    # 每一站走到哪一步，以及「繼續做」要複製的 prompt
    linked = {x for r in atlas["regions"] for x in r["waypoints"]} | {x for e in atlas["routes"] for x in (e["from"], e["to"])}
    for w in wps:
        w["stages"] = pipeline(ws / w["dir"], w["id"] in linked, len(wps) >= 2, S)
        w["actions"] = next_actions(w, w["stages"], S)
        live = [x for x in w["stages"] if x["state"] != "skip"]
        w["n_done"] = sum(1 for x in live if x["state"] == "done")
        w["n_total"] = len(live)
        w["all_done"] = not [x for x in w["stages"] if x["state"] in ("todo", "partial")]
        w["note"] = (S.n_all_done if w["all_done"]
                     else next((x["note"] for x in live if x["note"]), ""))
    for w in wps:
        w["err"] = errata_stats(w, S)
    env = Environment(loader=FileSystemLoader(template_dirs()), autoescape=True)
    env.filters["dur"] = fmt_dur
    env.filters["ts"] = fmt_ts
    env.filters["ago"] = lambda d: S.ago_days(d) if d is not None else ""
    now = datetime.now(UTC).astimezone()
    steps_data = {w["id"]: {k: w[k] for k in ("title", "stages", "actions", "n_done", "n_total")} for w in wps}
    html = env.get_template("atlas.html.j2").render(
        waypoints=wps, regions=regions, unplaced=unplaced, routes=atlas["routes"], by_id=by_id,
        steps_data=steps_data,
        has_listen=(ws / "listen.html").exists(), has_notes=(ws / "notes.html").exists(),
        has_digest=(ws / "digest.html").exists(),
        tips={}, S=S,
        generated=now.strftime("%Y-%m-%d %H:%M"), generated_iso=now.isoformat(timespec="seconds"),
    )
    out = ws / "atlas.html"
    write_text(out, html)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--merge", metavar="PATCH.JSON",
                    help="把新站的 route/region 併進 atlas.json（- = 讀 stdin），再驗證並 render")
    ap.add_argument("--migrate-routes", action="store_true",
                    help="把舊的五種 route 型態換成 next / related（via 不動），再 render")
    args = ap.parse_args(argv)
    if args.status:
        status(args.workspace)
        return
    ws = args.workspace
    with locked(ws / ".atlas.lock", "atlas.json"):  # 共用檔，一次只給一個流程寫
        if args.migrate_routes:
            atlas = load_atlas(ws)
            n = 0
            for e in atlas["routes"]:
                new = ROUTE_MIGRATE.get(e["type"], e["type"])
                n += new != e["type"]
                e["type"] = new
            save_json(ws / "atlas.json", atlas)
            print(f"{len(atlas['routes'])} 條 route，其中 {n} 條換了型態 → {ws / 'atlas.json'}")
        if args.merge:
            patch = json.loads(sys.stdin.read()) if args.merge == "-" else load_json(Path(args.merge))
            atlas = merge_atlas(load_atlas(ws), patch)
            errs = check_atlas(atlas, load_waypoints(ws))
            if errs:
                raise SystemExit("併進去之後 atlas.json 會有問題，沒有寫入：\n  - " + "\n  - ".join(errs))
            save_json(ws / "atlas.json", atlas)
            print(f"併入 {len(patch.get('routes', []))} 條 route、{len(patch.get('regions', []))} 個 region → {ws / 'atlas.json'}")
        out = render(ws)
    print(f"OK → {out}")
    print_step("atlas", str(out))


if __name__ == "__main__":
    main()
