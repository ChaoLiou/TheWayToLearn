"""/learn-fetch：抓 transcript（json3）+ metadata，不下載影片。
來源也可以是部落格文章：非 YouTube 的網址走 blog.py，正文段落當 transcript、閱讀時間當時間軸。

用法：uv run scripts/fetch.py <url|id> [--lang zh-TW,zh,en] [--force]
輸出：workspace/<id>/transcript.json, meta.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    DEFAULT_WORKSPACE,
    find_video_dir,
    is_blog,
    load_json,
    print_step,
    record_timing,
    save_json,
    video_dir,
    video_id,
)


def parse_json3(p: Path) -> list[dict]:
    """YouTube json3 → [{start, duration, text}]。"""
    data = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        out.append({
            "start": ev.get("tStartMs", 0) / 1000,
            "duration": ev.get("dDurationMs", 0) / 1000,
            "text": text,
        })
    return out


def parse_vtt(p: Path) -> list[dict]:
    """WebVTT → [{start, duration, text}]。有些自動字幕只有 vtt，沒有 json3。"""
    import re
    ts = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d\d\d)\s+-->\s+(\d+):(\d\d):(\d\d)\.(\d\d\d)")

    def sec(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    out, cur = [], None
    for line in p.read_text(encoding="utf-8").splitlines():
        m = ts.match(line.strip())
        if m:
            g = m.groups()
            cur = {"start": sec(*g[:4]), "duration": round(sec(*g[4:]) - sec(*g[:4]), 3), "text": ""}
            out.append(cur)
        elif cur is not None and line.strip():
            cur["text"] = (cur["text"] + " " + re.sub(r"<[^>]+>", "", line).strip()).strip()
        elif not line.strip():
            cur = None
    return [e for e in out if e["text"]]


def fetch(url: str, langs: list[str], vdir: Path, output_lang: str = "zh-TW") -> dict:
    cmd = [
        "yt-dlp", "--skip-download", "--no-playlist",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", ",".join(langs), "--sub-format", "json3",
        "--write-info-json", "-o", str(vdir / "subs"), "-o", f"infojson:{vdir / 'info'}",
        url,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    files = sorted(vdir.glob("subs.*.json3")) or sorted(vdir.glob("subs.*.vtt"))
    if not files:
        raise SystemExit(f"沒有拿到字幕（語言 {langs}）。用 yt-dlp --list-subs {url} 看有哪些。")
    # 依語言優先序挑
    by_lang = {f.name.split(".")[1]: f for f in files}
    chosen_lang = next((l for l in langs if l in by_lang), next(iter(by_lang)))
    chosen = by_lang[chosen_lang]
    events = parse_json3(chosen) if chosen.suffix == ".json3" else parse_vtt(chosen)
    for f in files:
        if f != by_lang[chosen_lang]:
            f.unlink()

    info = json.loads((vdir / "info.info.json").read_text(encoding="utf-8"))
    meta = {
        "video_id": info["id"],
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "duration": info.get("duration"),
        "url": info.get("webpage_url", url),
        "upload_date": info.get("upload_date"),
        "chapters": [{"title": c["title"], "start": c["start_time"], "end": c["end_time"]}
                     for c in (info.get("chapters") or [])],
        "transcript_lang": chosen_lang,
        "output_lang": output_lang,  # 產出文件的語言，/learn 依使用者對話語言決定
    }
    (vdir / "info.info.json").unlink()
    save_json(vdir / "meta.json", meta)
    save_json(vdir / "transcript.json", {"video_id": info["id"], "lang": chosen_lang, "events": events})
    return meta


def fetch_blog(url: str, vid: str, vdir: Path, output_lang: str = "zh-TW") -> dict:
    """部落格：正文段落 → transcript.json（start = 閱讀秒數），文章裡的圖片列在 images 給步驟 4 挑。"""
    import blog

    art = blog.extract(blog.fetch_html(url), url)
    meta = {
        "video_id": vid,
        "source": "blog",
        "title": art["title"],
        "channel": art["author"] or art["site"],
        "site": art["site"],
        "duration": art["duration"],  # 閱讀時間（秒）
        "url": url,
        "upload_date": art["date"],
        "thumbnail": art["image"],
        "chapters": art["chapters"],
        "transcript_lang": art["lang"],
        "output_lang": output_lang,
        "chars": art["chars"],
        "n_images": len(art["images"]),
    }
    save_json(vdir / "meta.json", meta)
    save_json(vdir / "transcript.json", {"video_id": vid, "source": "blog", "lang": art["lang"],
                                         "events": art["events"], "images": art["images"]})
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--lang", default="zh-TW,zh,en", help="字幕語言優先序")
    ap.add_argument("--output-lang", default="zh-TW", help="產出文件的語言（zh-TW / en …），跟著使用者的對話語言")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    vid = video_id(args.url)
    vdir = find_video_dir(vid, args.workspace)
    if vdir and (vdir / "transcript.json").exists() and not args.force:
        print(f"跳過：{vdir / 'transcript.json'} 已存在（--force 重抓）")
        return
    blog_src = is_blog(vid)
    if args.url.startswith("http"):
        url = args.url
    elif blog_src:  # 只給 id 的部落格站：網址要從已有的 meta.json / estimate.json 找
        src = next((load_json(vdir / f).get("url") for f in ("meta.json", "estimate.json")
                    if vdir and (vdir / f).exists()), None)
        if not src:
            raise SystemExit(f"{vid} 是部落格站但 workspace 裡沒有它的網址，請直接給 URL")
        url = src
    else:
        url = f"https://www.youtube.com/watch?v={vid}"
    # 資料夾名要用標題，但標題要抓完才知道：先下到暫存夾，再搬到正式資料夾
    tmp = args.workspace / f".tmp-{vid}"
    tmp.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    meta = (fetch_blog(url, vid, tmp, args.output_lang) if blog_src
            else fetch(url, args.lang.split(","), tmp, args.output_lang))
    vdir = video_dir(vid, args.workspace, title=meta["title"])
    for f in tmp.iterdir():
        f.replace(vdir / f.name)
    tmp.rmdir()
    record_timing(vdir, "fetch", time.monotonic() - t0)
    what = f"閱讀約 {meta['duration']:.0f}s、{meta['n_images']} 張圖" if blog_src else f"{meta['duration']}s, 字幕 {meta['transcript_lang']}"
    print(f"OK {meta['title']} ({what}) → {vdir}")
    print_step("fetch", meta["title"])


if __name__ == "__main__":
    main()
