"""播放清單展開：貼一串 YouTube playlist 網址 → 依清單順序的影片列表（不下載、不抓字幕）。

用法：
  uv run scripts/playlist.py <url> [--items 1-10|--limit N] [--from-here] [--json|--urls]

`watch?v=…&list=…`（從清單裡點進某一支）也吃：預設列整份清單，`--from-here` 則從貼的那一支列到最後。

下游完全不必知道播放清單的存在：展開後每支都是單支 `watch?v=` 網址（去掉 `list=`），
順序就是清單順序，estimate / load_input 直接把它們當成使用者一個個貼進來的網址。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fmt_dur, is_playlist_url, playlist_id, video_id

# 清單裡失效的項目：yt-dlp 仍會列出來，標題就是這些
UNAVAILABLE = {"[private video]", "[deleted video]", "[unavailable video]", "[video unavailable]"}
# 列得出來但抓不到字幕的：會員限定、付費、需要登入。先擋在這裡，免得跑到 fetch 才整條停住
LOCKED = {"subscriber_only": "頻道會員限定", "premium_only": "付費影片",
          "needs_auth": "需要登入", "private": "私人影片"}


def _url_vid(url: str) -> str | None:
    try:
        return video_id(url)
    except ValueError:
        return None


def _spec(items: str | None, limit: int | None) -> list[str]:
    if items:
        return ["--playlist-items", items]
    if limit:
        return ["-I", f":{int(limit)}"]
    return []


def entries(url: str, items: str | None = None, limit: int | None = None,
            from_here: bool = False) -> dict:
    """yt-dlp --flat-playlist（只讀清單，不碰每支影片）。from_here=True 時從網址指定的那一支起算。

    回傳 {"title", "playlist_id", "videos": [{index, id, url, title, duration, channel}], "skipped": [...]}
    """
    cmd = ["yt-dlp", "--flat-playlist", "--dump-json", "--yes-playlist", "--ignore-errors",
           *_spec(items, limit), url]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)  # --ignore-errors 時 exit code 可能非 0
    videos, skipped, title = [], [], ""
    seen = set()
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        title = title or e.get("playlist_title") or e.get("playlist") or ""
        if e.get("_type") == "playlist":  # 清單裡還有清單（頻道頁），不遞迴展開
            skipped.append({"title": e.get("title", ""), "why": "巢狀清單"})
            continue
        vid, name = e.get("id"), e.get("title") or ""
        if not vid or name.strip().lower() in UNAVAILABLE:
            skipped.append({"title": name, "why": "已刪除或私人影片"})
            continue
        if e.get("availability") in LOCKED:  # 會員限定等：抓得到標題但抓不到字幕
            skipped.append({"title": name, "why": LOCKED[e["availability"]]})
            continue
        if vid in seen:  # 同一支在清單裡出現兩次，只做一次
            skipped.append({"title": name, "why": "清單內重複"})
            continue
        seen.add(vid)
        videos.append({
            "index": len(videos) + 1,
            "id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "title": name,
            "duration": e.get("duration") or 0,
            "channel": e.get("channel") or e.get("uploader") or "",
        })
    if from_here:  # `watch?v=X&list=…`＝「從這一支開始」：砍掉 X 之前的，重新編號
        here = next((i for i, v in enumerate(videos) if v["id"] == _url_vid(url)), 0)
        videos = [{**v, "index": i} for i, v in enumerate(videos[here:], 1)]
    if not videos:
        tail = (r.stderr or "").strip().splitlines()[-3:]
        raise RuntimeError(f"展不開這個播放清單：{url}\n" + "\n".join(tail))
    return {"title": title, "playlist_id": playlist_id(url) or "", "videos": videos, "skipped": skipped}


MODES = ("one", "all", "from-here")
_OWN = ("url", "id", "items", "limit", "playlist")  # 這些是展開用的鍵，不往下傳


def expand_videos(videos: list[dict], mode: str = "one") -> list[dict]:
    """input.yaml / 指令列的影片清單就地展開：播放清單網址換成該清單的每一支，順序不變。

    每支繼承原本那筆的 shots / vision / max_shots 等設定；`items`（"1-10"）／`limit` 可限定範圍。
    `/playlist?list=…`（純清單）一律展開；`watch?v=…&list=…` 是「清單裡的某一支」，由 mode 決定：
    `one`（預設）只做那一支、`all` 整份清單、`from-here` 從那一支開始到最後。
    input.yaml 可在該筆寫 `playlist: all|from-here` 單獨指定。
    """
    out: list[dict] = []
    for v in videos:
        url = str(v.get("url", ""))
        m = str(v.get("playlist") or mode)
        if m not in MODES:
            raise ValueError(f"playlist 只能是 {'、'.join(MODES)}：{m}")
        if not is_playlist_url(url, only=(m == "one")):
            out.append(v)
            continue
        opts = {k: val for k, val in v.items() if k not in _OWN}
        pl = entries(url, v.get("items"), v.get("limit"), from_here=(m == "from-here"))
        for e in pl["videos"]:
            out.append({**opts, "url": e["url"], "playlist_title": pl["title"] or pl["playlist_id"],
                        "playlist_index": e["index"]})
    return out


def print_list(pl: dict) -> None:
    total = sum(v["duration"] for v in pl["videos"])
    head = pl["title"] or pl["playlist_id"]
    print(f"播放清單：{head}　{len(pl['videos'])} 支，總時長 {fmt_dur(total)}")
    for v in pl["videos"]:
        dur = fmt_dur(v["duration"]) if v["duration"] else "?"
        print(f"  {v['index']:>3}. {v['title']}  ({v['id']}, {dur})")
    for s in pl["skipped"]:
        print(f"    -  跳過：{s['title']}（{s['why']}）")
    print("\n依這個順序一支一支跑：/learn <清單網址>，或挑範圍 --items 1-5、從某一支開始 --from-here")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--items", help="yt-dlp 的範圍語法，例如 1-10、3,5,7-9")
    ap.add_argument("--limit", type=int, help="只取前 N 支")
    ap.add_argument("--from-here", action="store_true",
                    help="網址是 watch?v=…&list=… 時，從那一支開始列到清單最後")
    ap.add_argument("--json", action="store_true", help="只輸出 JSON")
    ap.add_argument("--urls", action="store_true", help="只印網址，一行一個")
    args = ap.parse_args(argv)

    pl = entries(args.url, args.items, args.limit, args.from_here)
    if args.json:
        print(json.dumps(pl, ensure_ascii=False, indent=2))
    elif args.urls:
        print("\n".join(v["url"] for v in pl["videos"]))
    else:
        print_list(pl)


if __name__ == "__main__":
    main()
