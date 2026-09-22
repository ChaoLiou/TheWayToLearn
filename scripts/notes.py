"""成長筆記：把各站的 notes.json（agent 依 rules/notes.md 擷取的觀念／技巧）彙整成 workspace/notes.html。
新產出的站在上面；每條筆記連回 plan.html 的那一段；每條可按「留／刪」（存瀏覽器），
「匯出」下載 notes.keep.json，放到 workspace/ 後這裡會把它當預設狀態。

用法：uv run scripts/notes.py [--workspace DIR]
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas import fmt_ymd
from common import (
    DEFAULT_WORKSPACE,
    fmt_dur,
    is_blog,
    load_json,
    template_dirs,
    write_text,
)
from i18n import Strings, norm_lang
from listen import categories, ui_lang


def created_at(d: Path, notes: dict) -> datetime:
    if notes.get("created"):
        try:
            return datetime.fromisoformat(notes["created"])
        except ValueError:
            pass
    return datetime.fromtimestamp((d / "notes.json").stat().st_mtime, UTC).astimezone()


def load_stations(ws: Path) -> list[dict]:
    out, cats = [], categories(ws)
    for d in sorted(p for p in ws.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        if not all((d / f).exists() for f in ("meta.json", "notes.json")):
            continue
        meta, notes = load_json(d / "meta.json"), load_json(d / "notes.json")
        seg_titles = {}
        if (d / "analysis.json").exists():
            seg_titles = {s["id"]: s["title"] for s in load_json(d / "analysis.json")["segments"]}
        when = created_at(d, notes)
        vid = meta["video_id"]
        out.append({
            "id": vid, "dir": d.name, "title": meta["title"], "channel": meta.get("channel"),
            "category": cats.get(vid, ""), "kind": "blog" if is_blog(meta) else "youtube", "url": meta.get("url"),
            "created": when.isoformat(timespec="seconds"), "created_ymd": when.strftime("%Y-%m-%d"),
            "upload_date": fmt_ymd(meta.get("upload_date")),
            "plan": f"{quote(d.name)}/plan.html" if (d / "plan.html").exists() else None,
            "has_lesson": (d / "lesson.mp3").exists(),
            "yt_thumb": (meta.get("thumbnail") or None) if is_blog(meta)
            else f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            "output_lang": norm_lang(meta.get("output_lang")),
            "notes": [dict(n, key=f"{vid}:{n['id']}", seg_title=seg_titles.get(n["seg_id"], ""),
                           href=f"{quote(d.name)}/plan.html#{vid}-s{n['seg_id']}") for n in notes["notes"]],
        })
    out.sort(key=lambda s: s["created"], reverse=True)
    return out


def load_keep(ws: Path) -> dict[str, str]:
    """workspace/notes.keep.json：{"<vid>:<note id>": "keep" | "drop"}（網頁「匯出」下載的格式）。"""
    p = ws / "notes.keep.json"
    if not p.exists():
        return {}
    data = load_json(p)
    return {k: v for k, v in data.items() if v in ("keep", "drop")} if isinstance(data, dict) else {}


def render(ws: Path) -> Path:
    stations = load_stations(ws)
    keep = load_keep(ws)
    S = Strings(ui_lang(stations, ws))
    env = Environment(loader=FileSystemLoader(template_dirs()), autoescape=True)
    env.filters["dur"] = fmt_dur
    now = datetime.now(UTC).astimezone()
    n_notes = sum(len(s["notes"]) for s in stations)
    html = env.get_template("notes.html.j2").render(
        stations=stations, keep=keep, S=S, n_notes=n_notes,
        has_listen=(ws / "listen.html").exists(), has_atlas=(ws / "atlas.html").exists(),
        has_digest=(ws / "digest.html").exists(),
        generated=now.strftime("%Y-%m-%d %H:%M"),
    )
    out = ws / "notes.html"
    write_text(out, html)
    print(f"{len(stations)} 站、{n_notes} 條筆記 → {out}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    args = ap.parse_args(argv)
    render(args.workspace)


if __name__ == "__main__":
    main()
