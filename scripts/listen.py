"""podcast 式的聽力頁：把 workspace 裡所有有 lesson.mp3 的站列成一集一集（新產出的在上面），
置底播放器可開字幕（講稿 karaoke）、切原聲／翻譯軌、連回 plan.html。

用法：uv run scripts/listen.py [--workspace DIR]

輸出：
  workspace/listen.html            播放清單 + 播放器
  workspace/<站>/captions.js       該站講稿的精簡版（逐句時間、章節），播放時才載入；
                                   用 <script> 而不是 fetch，所以 file:// 直接開也能有字幕
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas import fmt_ymd, thumb
from common import (
    DEFAULT_WORKSPACE,
    fmt_dur,
    fmt_ts,
    is_blog,
    load_json,
    locked,
    print_step,
    template_dirs,
    write_text,
)
from i18n import Strings, norm_lang


def slim(timeline: list[dict]) -> tuple[list[dict], list[list[float]]]:
    """lesson.json 的 timeline → 逐句 [{a,d,t,k,s,b}] 與每個 block 的 [at,dur]。
    k：s = 講解、c = 原聲、d = 翻譯配音；b = 第幾個 block（切軌時對位用）。"""
    lines, blocks = [], []
    for bi, e in enumerate(timeline):
        blocks.append([round(e["at"], 2), round(e["dur"], 2)])
        k = {"say": "s", "clip": "c", "dub": "d"}.get(e["kind"], "s")
        for j, ln in enumerate(e.get("lines", [])):
            row = {"a": round(ln["at"], 2), "d": round(ln["dur"], 2), "t": ln["text"], "k": k, "s": e["seg_id"], "b": bi}
            if k != "s" and j == 0 and e.get("label"):
                row["l"] = e["label"]
            lines.append(row)
    return lines, blocks


def captions(lesson: dict) -> dict:
    o, ob = slim(lesson["timeline"])
    cap = {"o": o, "ob": ob, "ch": [[round(c["at"], 2), c["title"], c["seg_id"]] for c in lesson["chapters"]],
           "segs": {str(c["seg_id"]): c["title"] for c in lesson["chapters"]}}
    if lesson.get("dub"):
        d, db = slim(lesson["dub"]["timeline"])
        cap["d"], cap["db"] = d, db
        cap["dch"] = [[round(c["at"], 2), c["title"], c["seg_id"]] for c in lesson["dub"]["chapters"]]
    return cap


def write_captions(d: Path, vid: str, lesson: dict) -> Path:
    out = d / "captions.js"
    body = json.dumps(captions(lesson), ensure_ascii=False, separators=(",", ":"))
    write_text(out, f'window.__cap=window.__cap||{{}};window.__cap[{json.dumps(vid)}]={body};\n')
    return out


def created_at(d: Path, lesson: dict) -> datetime:
    """這集是什麼時候產出的：lesson.json 的 created，舊檔沒有就看 lesson.mp3 的 mtime。"""
    if lesson.get("created"):
        try:
            return datetime.fromisoformat(lesson["created"])
        except ValueError:
            pass
    return datetime.fromtimestamp((d / lesson.get("file", "lesson.mp3")).stat().st_mtime, UTC).astimezone()


def categories(ws: Path) -> dict[str, str]:
    """video_id → atlas.json 的 region 名稱（分類）；沒進 atlas 的站沒有分類。"""
    p = ws / "atlas.json"
    if not p.exists():
        return {}
    return {vid: r["name"] for r in load_json(p).get("regions", []) for vid in r.get("waypoints", [])}


def load_episodes(ws: Path) -> list[dict]:
    eps, cats = [], categories(ws)
    for d in sorted(p for p in ws.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        if not all((d / f).exists() for f in ("meta.json", "lesson.json", "lesson.mp3")):
            continue
        meta, lesson = load_json(d / "meta.json"), load_json(d / "lesson.json")
        write_captions(d, meta["video_id"], lesson)
        when = created_at(d, lesson)
        dub = lesson.get("dub") or None
        eps.append({
            "id": meta["video_id"], "dir": d.name, "title": meta["title"], "channel": meta.get("channel"),
            "category": cats.get(meta["video_id"], ""),
            "kind": "blog" if is_blog(meta) else "youtube", "url": meta.get("url"),
            "duration": lesson["duration"], "dub_duration": dub["duration"] if dub else None,
            "n_chapters": len(lesson.get("chapters", [])),
            "created": when.isoformat(timespec="seconds"), "created_ymd": when.strftime("%Y-%m-%d"),
            "upload_date": fmt_ymd(meta.get("upload_date")),
            "plan": f"{quote(d.name)}/plan.html", "mp3": f"{quote(d.name)}/{quote(lesson['file'])}",
            "dub": f"{quote(d.name)}/{quote(dub['file'])}" if dub else None,
            "cap": f"{quote(d.name)}/captions.js",
            "has_notes": (d / "notes.json").exists(), "has_plan": (d / "plan.html").exists(),
            "thumb": thumb(d),
            "yt_thumb": (meta.get("thumbnail") or None) if is_blog(meta)
            else f"https://i.ytimg.com/vi/{meta['video_id']}/mqdefault.jpg",
            "output_lang": norm_lang(meta.get("output_lang")),
        })
    eps.sort(key=lambda e: e["created"], reverse=True)
    return eps


def ui_lang(items: list[dict], ws: Path) -> str:
    atlas = ws / "atlas.json"
    if atlas.exists():
        forced = load_json(atlas).get("lang")
        if forced:
            return norm_lang(forced)
    langs = [e["output_lang"] for e in items]
    return max(set(langs), key=langs.count) if langs else norm_lang(None)


def render(ws: Path) -> Path:
    eps = load_episodes(ws)
    S = Strings(ui_lang(eps, ws))
    env = Environment(loader=FileSystemLoader(template_dirs()), autoescape=True)
    env.filters["dur"] = fmt_dur
    env.filters["ts"] = fmt_ts
    now = datetime.now(UTC).astimezone()
    player = [{k: e[k] for k in ("id", "title", "channel", "url", "mp3", "dub", "cap", "plan", "yt_thumb", "thumb", "duration", "dub_duration")} for e in eps]
    html = env.get_template("listen.html.j2").render(
        episodes=eps, player=player, S=S, total=sum(e["duration"] for e in eps),
        has_notes=(ws / "notes.html").exists(), has_atlas=(ws / "atlas.html").exists(),
        has_digest=(ws / "digest.html").exists(),
        generated=now.strftime("%Y-%m-%d %H:%M"),
    )
    out = ws / "listen.html"
    write_text(out, html)
    print(f"{len(eps)} 集 → {out}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    args = ap.parse_args(argv)
    with locked(args.workspace / ".listen.lock", "listen.html"):
        out = render(args.workspace)
    print_step("listen", str(out))


if __name__ == "__main__":
    main()
