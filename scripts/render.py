"""/learn-render：把 workspace 裡的 analysis/segments/meta/_overview 組成 plan.html。

用法：uv run scripts/render.py [--workspace workspace] [--out workspace/plan.html] [--ids a,b]
截圖以相對路徑引用，plan.html 放在 workspace/ 下，frames 在 workspace/<id>/frames/。
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    DEFAULT_WORKSPACE,
    default_output_lang,
    find_video_dir,
    fmt_dur,
    fmt_ts,
    is_blog,
    load_json,
    print_step,
    template_dirs,
    video_id,
    write_text,
)
from i18n import Strings, norm_lang

SENT_END = re.compile(r"(?<=[。！？!?])\s*|(?<=[.;])\s+")


def paras(text: str, per: int = 3) -> list[str]:
    """一整陀文字切成段落：本來就有換行就照換行，否則每 `per` 句一段。"""
    text = (text or "").strip()
    if not text:
        return []
    if "\n" in text:
        return [b.strip() for b in re.split(r"\n\s*\n|\n", text) if b.strip()]
    sents = [s for s in SENT_END.split(text) if s and s.strip()]
    return ["".join(sents[i : i + per]).strip() for i in range(0, len(sents), per)] or [text]


def _term_pat(word: str) -> re.Pattern:
    """英文術語要對齊單字邊界（agent 不該配到 agents 裡的一半），中文不需要。"""
    esc = re.escape(word)
    if word[:1].isascii() and word[:1].isalnum():
        esc = r"\b" + esc
    if word[-1:].isascii() and word[-1:].isalnum():
        esc = esc + r"\b"
    return re.compile(esc, re.IGNORECASE)


def _first_free(texts: dict[str, str], taken: dict[str, list], cands) -> tuple[str, int, int] | None:
    """依 texts 的順序找第一個還沒被別的術語佔走的位置。"""
    for key, text in texts.items():
        if not text:
            continue
        for cand in cands:
            if not cand:
                continue
            for m in _term_pat(cand).finditer(text):
                if not any(m.start() < e and s < m.end() for s, e in taken[key]):
                    return key, m.start(), m.end()
    return None


def _weave(text: str, spans: list[tuple[int, int, dict]], more: str) -> Markup:
    out: list[Markup] = []
    i = 0
    for a, b, t in spans:
        out.append(escape(text[i:a]))
        out.append(
            Markup('<span class="term" data-zh="{}">{}</span>'
                   '<button class="info" data-term="{}" title="{}" aria-label="{}">i</button>')
            .format(t.get("zh", ""), text[a:b], t["tid"], more, more)
        )
        i = b
    out.append(escape(text[i:]))
    return Markup("").join(out)


def mark_terms(texts: dict[str, str], terms: list[dict], more: str) -> tuple[dict[str, Markup], list[dict]]:
    """術語就地標在文章裡：第一次出現的地方加底線 + ⓘ，不再另外列一份表。
    一個術語只標一次（依 texts 的順序找）；文中找不到的回傳到 extra，由模板列成一行。"""
    taken: dict[str, list] = {k: [] for k in texts}
    spans: dict[str, list] = {k: [] for k in texts}
    extra: list[dict] = []
    # 長的先配，免得短術語吃掉長術語的一部分（agent 之於 agentic workflow）
    for t in sorted(terms, key=lambda x: -len(x["term"])):
        pos = _first_free(texts, taken, (t["term"], t.get("zh", "")))
        if pos is None:
            extra.append(t)
            continue
        key, a, b = pos
        taken[key].append((a, b))
        spans[key].append((a, b, t))
    order = {id(t): i for i, t in enumerate(terms)}
    extra.sort(key=lambda t: order[id(t)])
    return {k: _weave(v, sorted(spans[k]), more) for k, v in texts.items()}, extra


def _norm_timings(t: dict) -> dict:
    """容忍 agent 手寫的 timings.json：值寫成純秒數時補成 {"sec": …}。"""
    return {k: (v if isinstance(v, dict) else {"sec": v}) for k, v in t.items()}


def seeker(meta: dict, vdir: Path):
    """回傳 at(t) → (連到來源那個位置的網址, 顯示文字)。
    影片：url&t=Ns 與 m:ss；文章：text fragment 連結與 ¶段落編號（時間軸是閱讀秒數，顯示出來沒意義）。"""
    url = meta.get("url") or ""
    if not is_blog(meta):
        sep = "&" if "?" in url else "?"
        return lambda t, end=False, text=None: (f"{url}{sep}t={int(t)}s", fmt_ts(t))
    import blog

    tp = vdir / "transcript.json"
    events = load_json(tp).get("events", []) if tp.exists() else []

    def at(t, end=False, text=None):
        # 段落的 end 等於下一段的 start：當結尾看時要算前一個段落
        t = t - 0.01 if end else t
        return blog.source_href(url, events, t, text), blog.pos_label(events, t)

    return at


def load_video(vdir: Path, href_prefix: str, S: Strings) -> dict | None:
    need = ["meta.json", "segments.json", "analysis.json"]
    if not all((vdir / n).exists() for n in need):
        return None
    v = {n.split(".")[0]: load_json(vdir / n) for n in need}
    v["id"] = v["meta"]["video_id"]
    v["dir"] = vdir.name
    v["kind"] = "blog" if is_blog(v["meta"]) else "youtube"
    v["source_name"] = S.blog_link if v["kind"] == "blog" else "YouTube"
    v["dur_label"] = (S.reading + " " if v["kind"] == "blog" else "") + fmt_dur(v["meta"].get("duration") or 0)
    at = seeker(v["meta"], vdir)
    v["estimate"] = load_json(vdir / "estimate.json") if (vdir / "estimate.json").exists() else None
    v["lesson"] = load_json(vdir / "lesson.json") if (vdir / "lesson.json").exists() else None
    st = vdir / "lesson.status.json"
    v["lesson_status"] = load_json(st) if st.exists() and not v["lesson"] else None
    v["lesson_src"] = href_prefix + "lesson.mp3"
    if v["lesson"]:
        v["lesson"]["href"] = href_prefix + quote(v["lesson"]["file"])
        if v["lesson"].get("dub"):
            v["lesson"]["dub"]["href"] = href_prefix + quote(v["lesson"]["dub"]["file"])
    v["timings"] = _norm_timings(load_json(vdir / "timings.json") if (vdir / "timings.json").exists() else {})
    seg_by_id = {s["id"]: s for s in v["segments"]["segments"]}
    for s in v["analysis"]["segments"]:
        src = seg_by_id.get(s["id"], {})
        s["start"], s["end"] = src.get("start", 0), src.get("end", 0)
        s["start_href"], s["start_label"] = at(s["start"])
        s["end_label"] = at(s["end"], end=True)[1]
        s["summary"] = src.get("summary", "")
        s["shots"] = [sh for sh in src.get("shots", []) if sh.get("file")]
        for sh in s["shots"]:
            sh["href"] = href_prefix + quote(sh["file"])
            sh["seg_title"] = s["title"]
            sh["t_label"] = at(sh["t"])[1]
        for iss in s.get("issues", []):
            iss["href"], iss["t_label"] = at(iss.get("t", 0), text=iss.get("quote"))
    # PACER 練習（digest.json）：每段列出這段的資訊類別與該做的事，連到 digest.html 那一筆
    dg = load_json(vdir / "digest.json") if (vdir / "digest.json").exists() else None
    for s in v["analysis"]["segments"]:
        s["digest"] = [dict(it, href=f"../digest.html#{v['id']}-d{it['id']}")
                       for it in (dg["items"] if dg else []) if it["seg_id"] == s["id"]]
    # 術語就地標在 summary / reasoning / explanation 裡（第一次出現處），不再列成 dl
    for s in v["analysis"]["segments"]:
        for i, t in enumerate(s.get("terms", []), 1):
            t["tid"] = f'{v["id"]}-{s["id"]}-{i}'
        texts = {k: s.get(k) or "" for k in ("summary", "reasoning", "explanation")}
        marked, s["terms_extra"] = mark_terms(texts, s.get("terms", []), S.more)
        for k, html in marked.items():
            s[k + "_html"] = html
    v["all_shots"] = [sh for s in v["analysis"]["segments"] for sh in s["shots"]]
    for i, sh in enumerate(v["all_shots"]):
        sh["idx"] = i
    v["issues"] = [
        dict(iss, seg_id=s["id"], seg_title=s["title"])
        for s in v["analysis"]["segments"] for iss in s.get("issues", [])
    ]
    v["issues"].sort(key=lambda x: (x["level"] != "wrong", x["seg_id"], x["t"]))
    # 推理鏈本來就是一條線（每段接下一段），畫成 mermaid 沒有比文字多給資訊，所以只留文字
    v["reasoning_paras"] = paras(v["analysis"].get("author_reasoning", ""))
    v["chain_desc"] = [
        {"id": s["id"], "title": s["title"], "leads_to": s["leads_to"]} for s in v["analysis"]["segments"]
    ]
    return v


def atlas_context(ws: Path, vid: str, S: Strings) -> dict | None:
    """這支影片與其他站的關係：region、進出 route（含對方 plan.html 的相對路徑）。"""
    p = ws / "atlas.json"
    if not p.exists():
        return None
    atlas = load_json(p)
    titles = {}
    for d in ws.iterdir():
        if d.is_dir() and not d.name.startswith((".", "_")) and (d / "meta.json").exists():
            m = load_json(d / "meta.json")
            titles[m["video_id"]] = {"title": m["title"], "href": f"../{quote(d.name)}/plan.html"}
    region = next((r for r in atlas["regions"] if vid in r["waypoints"]), None)
    links = []
    for e in atlas["routes"]:
        undirected = e["type"] != "next"          # related 沒有先後，不畫箭頭
        if vid == e["from"] and e["to"] in titles:
            links.append({"dir": "—" if undirected else "→", "type": S.route(e["type"]), "via": e["via"], **titles[e["to"]]})
        elif vid == e["to"] and e["from"] in titles:
            links.append({"dir": "—" if undirected else "←", "type": S.route(e["type"]), "via": e["via"], **titles[e["from"]]})
    if region is None and not links:
        return {"atlas_href": "../atlas.html", "region": None, "links": []}
    return {"atlas_href": "../atlas.html", "region": region, "links": links}


def render(overview_path: Path, video_dirs: list[Path], out: Path) -> None:
    overview = load_json(overview_path)
    order = [o["video_id"] for o in overview["outline"]]
    by_id = {}
    for d in video_dirs:
        if (d / "meta.json").exists():
            by_id[load_json(d / "meta.json")["video_id"]] = d
    videos = []
    # 輸出語言：第一支影片的 meta.output_lang（/learn 依對話語言寫入），預設 zh-TW
    first = by_id.get(order[0]) if order else None
    S = Strings(norm_lang((load_json(first / "meta.json").get("output_lang") if first else None)
                          or default_output_lang()))
    for vid in order:
        vdir = by_id.get(vid)
        # 截圖相對路徑：plan.html 跟 frames 同資料夾就不用前綴
        prefix = "" if vdir and vdir == out.parent else (f"{quote(vdir.name)}/" if vdir else "")
        v = load_video(vdir, prefix, S) if vdir else None
        if v is None:
            print(f"略過 {vid}：缺 meta/segments/analysis")
            continue
        videos.append(v)
    if not videos:
        raise SystemExit("沒有任何可 render 的影片")
    ws = out.parent.parent if out.parent != overview_path.parent.parent else out.parent
    atlas = atlas_context(ws, videos[0]["id"], S) if len(videos) == 1 else None
    # workspace 層級的其他頁。筆記與練習帶 ?only=<id>：點過去預設只篩這一支（見 _search.html.j2）。
    # 判準是「這一站自己有沒有那份資料」——沒有的話連過去只會看到 0 筆，不如不顯示。
    hub = {}
    if len(videos) == 1:
        vid, vdir = videos[0]["id"], out.parent
        if (ws / "atlas.html").exists():
            hub["atlas"] = "../atlas.html"                   # 回到全部影片的列表，不篩
        if (ws / "listen.html").exists() and (vdir / "lesson.mp3").exists():
            hub["listen"] = f"../listen.html#{vid}"          # 播放器要能自動接下一集，不篩
        if (ws / "notes.html").exists() and (vdir / "notes.json").exists():
            hub["notes"] = f"../notes.html?only={vid}#{vid}"
        if (ws / "digest.html").exists() and (vdir / "digest.json").exists():
            hub["digest"] = f"../digest.html?only={vid}#{vid}"
    env = Environment(loader=FileSystemLoader(template_dirs()), autoescape=True)
    env.filters["ts"] = fmt_ts
    env.filters["dur"] = fmt_dur
    env.filters["yt_search"] = lambda q: "https://www.youtube.com/results?search_query=" + quote(q)
    html = env.get_template("plan.html.j2").render(
        overview=overview,
        videos=videos,
        tips={},
        atlas=atlas,
        hub=hub,
        S=S,
        h_reasoning=S.h_reasoning_blog if all(v["kind"] == "blog" for v in videos) else S.h_reasoning,
        generated=datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M"),
    )
    write_text(out, html)
    print(f"OK → {out}")
    print_step("render", str(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="video id 或 URL；不給 = workspace 下全部")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--combined", action="store_true", help="多支合併成一份 plan.html")
    ap.add_argument("--out", type=Path, help="--combined 時的輸出路徑，預設 workspace/plan.html")
    args = ap.parse_args(argv)

    ws = args.workspace
    if args.ids:
        dirs = []
        for x in args.ids:
            d = find_video_dir(video_id(x), ws)
            if not d:
                raise SystemExit(f"workspace 裡沒有 {x}")
            dirs.append(d)
    else:
        dirs = sorted(d for d in ws.iterdir() if d.is_dir() and not d.name.startswith((".", "_")) and (d / "meta.json").exists())

    if args.combined:
        ov = ws / "_overview.json"
        if not ov.exists():
            raise SystemExit(f"缺 {ov}：先由 agent 依 rules/overview.md 產生")
        render(ov, dirs, args.out or ws / "plan.html")
        return
    for d in dirs:
        ov = d / "_overview.json"
        if not ov.exists():
            print(f"略過 {d.name}：缺 _overview.json（agent 依 rules/overview.md 產生）")
            continue
        render(ov, [d], d / "plan.html")


if __name__ == "__main__":
    main()
