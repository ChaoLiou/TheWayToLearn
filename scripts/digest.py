"""消化工作單：把各站的 digest.json（agent 依 rules/digest.md 標的 PACER 資訊）彙整成 workspace/digest.html。
每筆資訊顯示類別與該做的消化動作；P/A/C 做完按「做完了」、E 有「演練」、R 是 flashcard（SM-2 間隔重複）。
進度存瀏覽器；「匯出進度」下載 digest.state.json，放到 workspace/ 後這裡把它當預設狀態，
`backlog()` 也讀同一份給 /learn 算「消化積欠」。

用法：uv run scripts/digest.py [--workspace DIR]                 # 產 digest.html + 印積欠
      uv run scripts/digest.py --backlog                          # 只印積欠（/learn 平衡閥）
      uv run scripts/digest.py --pending [<vid>|due]              # 列還沒做的（JSON，/learn-digest 對話用）
      uv run scripts/digest.py --mark <vid>:<id> done|undo|rehearsed|grade [值]   # 寫 digest.state.json 再重產頁
      uv run scripts/digest.py --mark <vid> read|unread                    # 標「讀完了」：沒讀的站不算積欠
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas import fmt_ymd
from common import (
    DEFAULT_WORKSPACE,
    STEP_CMD,
    fmt_dur,
    is_blog,
    load_json,
    locked,
    print_step,
    template_dirs,
    write_text,
)
from i18n import Strings, norm_lang
from listen import categories, ui_lang

KINDS = ("P", "A", "C", "E", "R")
REHEARSE_AFTER = timedelta(days=1)   # E：讀完至少隔一天才演練（影片：一天或一週結束時）


def read_key(vid: str) -> str:
    """digest.state.json 裡「這站讀完了」的 key：{"<vid>:read": {"read": "<ISO>"}}。
    產出工作單只是消費期的準備，讀完才進消化期；沒讀的站不算積欠。"""
    return f"{vid}:read"


def read_at(vid: str, state: dict) -> str | None:
    return (state.get(read_key(vid)) or {}).get("read")


def created_at(d: Path, data: dict) -> datetime:
    if data.get("created"):
        try:
            return datetime.fromisoformat(data["created"])
        except ValueError:
            pass
    return datetime.fromtimestamp((d / "digest.json").stat().st_mtime, UTC).astimezone()


def load_state(ws: Path) -> dict[str, dict]:
    """workspace/digest.state.json：{"<vid>:<item id>": {...}}（網頁「匯出進度」下載的格式；/learn-digest 也寫這裡）。
    P/A/C：{done, note?, alike?, unlike?, breaks?}；E：{rehearsed, answer?}；R：{ef, reps, interval, due}。"""
    p = ws / "digest.state.json"
    if not p.exists():
        return {}
    data = load_json(p)
    return {k: v for k, v in data.items() if isinstance(v, dict)} if isinstance(data, dict) else {}


def load_stations(ws: Path) -> list[dict]:
    out, cats, state = [], categories(ws), load_state(ws)
    for d in sorted(p for p in ws.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        if not all((d / f).exists() for f in ("meta.json", "digest.json")):
            continue
        meta, dg = load_json(d / "meta.json"), load_json(d / "digest.json")
        seg_titles = {}
        if (d / "analysis.json").exists():
            seg_titles = {s["id"]: s["title"] for s in load_json(d / "analysis.json")["segments"]}
        when = created_at(d, dg)
        vid = meta["video_id"]
        read = read_at(vid, state)
        # E 的「隔一天」從讀完那天起算；還沒讀就先用產出日（頁面上未讀的站本來就不計）
        since = datetime.fromisoformat(read) if read else when
        plan = f"{quote(d.name)}/plan.html" if (d / "plan.html").exists() else None
        items = [dict(n, key=f"{vid}:{n['id']}", seg_title=seg_titles.get(n["seg_id"], ""),
                      href=f"{plan}#{vid}-s{n['seg_id']}" if plan else None) for n in dg["items"]]
        out.append({
            "id": vid, "dir": d.name, "title": meta["title"], "channel": meta.get("channel"),
            "category": cats.get(vid, ""), "kind": "blog" if is_blog(meta) else "youtube", "url": meta.get("url"),
            "created": when.isoformat(timespec="seconds"), "created_ymd": when.strftime("%Y-%m-%d"),
            "rehearse_from": (since + REHEARSE_AFTER).strftime("%Y-%m-%d"),
            "read": read, "read_ymd": read[:10] if read else None,
            "upload_date": fmt_ymd(meta.get("upload_date")),
            "plan": plan, "has_lesson": (d / "lesson.mp3").exists(),
            "yt_thumb": (meta.get("thumbnail") or None) if is_blog(meta)
            else f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            "output_lang": norm_lang(meta.get("output_lang")),
            "items": items,
            "by_kind": {k: [n for n in items if n["kind"] == k] for k in KINDS},
        })
    out.sort(key=lambda s: s["created"], reverse=True)
    return out


def backlog(ws: Path, today: date | None = None) -> dict:
    """消化積欠：P/A/C 未做、E 到期未演練、R 到期未回想。/learn 平衡閥用。
    只算**讀完的站**（`--mark <vid> read`）：工作單產出來還沒讀是消費期，不算積欠；`unread` 記幾站沒讀。"""
    today = today or _today()
    st = load_state(ws)
    n = {k: 0 for k in KINDS}
    total = unread = 0
    for s in load_stations(ws):
        total += len(s["items"])
        if not s["read"]:
            unread += 1
            continue
        for it in s["items"]:
            if is_pending(it, st.get(it["key"], {}), s["rehearse_from"], today):
                n[it["kind"]] += 1
    n["total"] = sum(n[k] for k in KINDS)
    n["items"] = total
    n["unread"] = unread
    return n


def _today() -> date:
    return datetime.now(UTC).astimezone().date()


def is_pending(item: dict, st: dict, rehearse_from: str, today: date) -> bool:
    """P/A/C 沒 done、E 到期沒 rehearsed、R 沒排或已到期。"""
    k = item["kind"]
    if k == "E":
        return not st.get("rehearsed") and rehearse_from <= today.isoformat()
    if k == "R":
        return not st.get("due") or st["due"] <= today.isoformat()
    return not st.get("done")


def pending(ws: Path, which: str = "due", today: date | None = None) -> list[dict]:
    """還沒做的筆，給 /learn-digest 對話用：which = video_id | "due"（全部站）。
    每筆只帶對話需要的欄位（答案卷 relations / critique_key / a 也帶，agent 給回饋用）。"""
    today = today or _today()
    st = load_state(ws)
    out = []
    for s in load_stations(ws):
        if which != "due" and s["id"] != which:
            continue
        if not s["read"]:
            continue    # 還沒讀就沒得消化
        for it in s["items"]:
            x = st.get(it["key"], {})
            if not is_pending(it, x, s["rehearse_from"], today):
                continue
            row = {k: it[k] for k in ("key", "kind", "text", "seg_id") if k in it}
            row.update({k: it[k] for k in ("procedure", "practice_task", "new", "known", "critique_key", "concept",
                                             "relations", "detail", "supports", "rehearse_q", "q", "a") if k in it})
            row["station"] = s["title"]
            if x:
                row["state"] = x
            out.append(row)
    return out


def sm2(st: dict, q: int, today: date | None = None) -> dict:
    """跟 digest.html.j2 裡的 JS 同一套：q = 0 忘了 / 3 難 / 5 會。"""
    today = today or _today()
    ef, reps, interval = float(st.get("ef", 2.5)), int(st.get("reps", 0)), int(st.get("interval", 0))
    if q < 3:
        reps, interval = 0, 1
    else:
        reps += 1
        interval = 1 if reps == 1 else 6 if reps == 2 else round(interval * ef)
    ef = max(1.3, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    return {"ef": round(ef, 2), "reps": reps, "interval": interval,
            "due": (today + timedelta(days=interval)).isoformat(), "last": today.isoformat()}


def mark(ws: Path, key: str, action: str, value: str = "") -> dict:
    """寫 workspace/digest.state.json 的一筆：done [心得] / undo / rehearsed [回答] / grade 0|3|5 / <欄位>=<值>。
    key 只給 <vid>（沒有冒號）時是整站：read = 讀完了、unread = 標回未讀。
    有檔案鎖；網頁「匯出進度」用同一種格式，所以兩邊可以互相覆蓋。"""
    p = ws / "digest.state.json"
    if ":" not in key:
        key = read_key(key)
    with locked(ws / ".digest.lock", "digest.state.json"):
        state = load_state(ws)
        st = dict(state.get(key, {}))
        now = datetime.now(UTC).astimezone().isoformat(timespec="seconds")
        if action == "read":
            st["read"] = now
        elif action == "unread":
            st.pop("read", None)
        elif action == "done":
            st["done"] = now
            if value:
                st["note"] = value
        elif action == "undo":
            for k in ("done", "rehearsed"):
                st.pop(k, None)
        elif action == "rehearsed":
            st["rehearsed"] = now
            if value:
                st["answer"] = value
        elif action == "grade":
            st.update(sm2(st, int(value)))
        elif "=" in action:
            k, v = action.split("=", 1)
            st[k] = v
        else:
            raise SystemExit(f"不認得的動作：{action}（done|undo|rehearsed|grade|<欄位>=<值>；整站 read|unread）")
        state[key] = st
        write_text(p, json.dumps(state, ensure_ascii=False, indent=2))
    return st


def backlog_line(ws: Path, S: Strings | None = None) -> str:
    b = backlog(ws)
    S = S or Strings(norm_lang(None))
    line = (f"{S.f('d_backlog', p=b['P'], a=b['A'], c=b['C'])} · {S.f('d_due_rehearse', n=b['E'])}"
            f" · {S.f('d_due_cards', n=b['R'])}")
    if b["unread"]:
        line += f" · {S.f('d_unread_skip', n=b['unread'])}"
    return line


def render(ws: Path) -> Path:
    stations = load_stations(ws)
    state = load_state(ws)
    S = Strings(ui_lang(stations, ws))
    env = Environment(loader=FileSystemLoader(template_dirs()), autoescape=True)
    env.filters["dur"] = fmt_dur
    now = datetime.now(UTC).astimezone()
    n_items = sum(len(s["items"]) for s in stations)
    html = env.get_template("digest.html.j2").render(
        stations=stations, state=state, S=S, n_items=n_items, kinds=KINDS,
        has_listen=(ws / "listen.html").exists(), has_atlas=(ws / "atlas.html").exists(),
        has_notes=(ws / "notes.html").exists(), cmd=STEP_CMD["digest"],
        generated=now.strftime("%Y-%m-%d %H:%M"),
    )
    out = ws / "digest.html"
    write_text(out, html)
    print(f"{len(stations)} 站、{n_items} 筆 → {out}")
    return out


def export_brain(ws: Path) -> None:
    """順便更新 Obsidian vault（workspace/brain/）；brain.py 反過來 import 這裡，所以在函式內 import。"""
    from brain import export
    n_st, n_c = export(ws, ws / "brain")
    print(f"second brain：{n_st} 站、{n_c} 個概念 → {ws / 'brain'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--backlog", action="store_true", help="只印消化積欠，不產頁")
    ap.add_argument("--pending", nargs="?", const="due", metavar="VID|due", help="列還沒做的筆（JSON）")
    ap.add_argument("--mark", nargs="+", metavar=("KEY", "ACTION"),
                    help="<vid>:<id> done|undo|rehearsed|grade [值]，或 <vid> read|unread，寫進 digest.state.json")
    args = ap.parse_args(argv)
    if args.backlog:
        print(backlog_line(args.workspace))
        return
    if args.pending:
        print(json.dumps(pending(args.workspace, args.pending), ensure_ascii=False, indent=1))
        return
    if args.mark:
        if len(args.mark) < 2:
            raise SystemExit("--mark 需要 <vid>:<id>（或 <vid>）與動作")
        st = mark(args.workspace, args.mark[0], args.mark[1], " ".join(args.mark[2:]))
        print(f"{args.mark[0]} → {json.dumps(st, ensure_ascii=False)}")
        render(args.workspace)
        export_brain(args.workspace)
        print(backlog_line(args.workspace))
        return
    out = render(args.workspace)
    export_brain(args.workspace)
    print(backlog_line(args.workspace))
    print_step("digest", str(out))


if __name__ == "__main__":
    main()
