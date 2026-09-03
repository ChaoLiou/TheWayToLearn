"""/learn-fetch：抓 transcript（json3）+ metadata，不下載影片。

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
from common import DEFAULT_WORKSPACE, find_video_dir, record_timing, save_json, video_dir, video_id


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


def fetch(url: str, langs: list[str], vdir: Path) -> dict:
    cmd = [
        "yt-dlp", "--skip-download", "--no-playlist",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", ",".join(langs), "--sub-format", "json3",
        "--write-info-json", "-o", str(vdir / "subs"), "-o", f"infojson:{vdir / 'info'}",
        url,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    files = sorted(vdir.glob("subs.*.json3"))
    if not files:
        raise SystemExit(f"沒有拿到字幕（語言 {langs}）。用 yt-dlp --list-subs {url} 看有哪些。")
    # 依語言優先序挑
    by_lang = {f.name.split(".")[1]: f for f in files}
    chosen_lang = next((l for l in langs if l in by_lang), next(iter(by_lang)))
    events = parse_json3(by_lang[chosen_lang])
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
    }
    (vdir / "info.info.json").unlink()
    save_json(vdir / "meta.json", meta)
    save_json(vdir / "transcript.json", {"video_id": info["id"], "lang": chosen_lang, "events": events})
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--lang", default="zh-TW,zh,en")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    vid = video_id(args.url)
    vdir = find_video_dir(vid, args.workspace)
    if vdir and (vdir / "transcript.json").exists() and not args.force:
        print(f"跳過：{vdir / 'transcript.json'} 已存在（--force 重抓）")
        return
    url = args.url if args.url.startswith("http") else f"https://www.youtube.com/watch?v={vid}"
    # 資料夾名要用標題，但標題要抓完才知道：先下到暫存夾，再搬到正式資料夾
    tmp = args.workspace / f".tmp-{vid}"
    tmp.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    meta = fetch(url, args.lang.split(","), tmp)
    vdir = video_dir(vid, args.workspace, title=meta["title"])
    for f in tmp.iterdir():
        f.replace(vdir / f.name)
    tmp.rmdir()
    record_timing(vdir, "fetch", time.monotonic() - t0)
    print(f"OK {meta['title']} ({meta['duration']}s, 字幕 {meta['transcript_lang']}) → {vdir}")


if __name__ == "__main__":
    main()
