"""/learn-estimate：只用 yt-dlp --dump-json 拿 metadata，估各階段時間/token/磁碟，不下載。

用法：
  uv run scripts/estimate.py <url|id> [<url|id> ...] [--vision true|false|auto] [--json]
  uv run scripts/estimate.py --input input.yaml
輸出：每支影片分階段表 + 每支小計 + 全部總和；同時寫 workspace/<id>/estimate.json。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    DEFAULT_WORKSPACE,
    config_file,
    fmt_dur,
    load_input,
    load_yaml,
    print_step,
    save_json,
    video_dir,
)


def probe(url: str, max_height: int) -> dict:
    """yt-dlp --dump-json（不下載）。回傳精簡 metadata。"""
    fmt = f"bv*[height<={max_height}]/b[height<={max_height}]/b"
    cmd = ["yt-dlp", "--dump-json", "--no-playlist", "--skip-download", "-f", fmt, url]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    info = json.loads(out.splitlines()[0])
    size = info.get("filesize") or info.get("filesize_approx") or 0
    subs = sorted(info.get("subtitles", {}).keys())
    auto = sorted(info.get("automatic_captions", {}).keys())
    return {
        "id": info["id"],
        "title": info.get("title", ""),
        "duration": info.get("duration") or 0,
        "filesize": size,
        "height": info.get("height"),
        "subtitles": subs,
        "automatic_captions": auto[:10],
        "has_any_subs": bool(subs or auto),
    }


def estimate_one(meta: dict, vision: str, cfg: dict, shots: str = "auto") -> dict:
    dur = meta["duration"]
    mins = dur / 60
    seg_cfg = cfg["segment"]
    n_seg = round(mins / seg_cfg["minutes_per_segment"])
    n_seg = max(seg_cfg["min_segments"], min(seg_cfg["max_segments"], n_seg))
    per_seg = {"none": 0, "auto": cfg["shot"]["frames_per_segment"], "many": cfg["shot"]["frames_per_segment"] + 1}[shots]
    n_frames = n_seg * per_seg
    # 沒有 transcript 時，字數用語速估：中文約 200 字/分
    words = mins * 200
    transcript_tokens = int(words * cfg["tokens_per_transcript_word"])

    # 沒有截圖就沒有 vision 可言
    vision_on = n_frames > 0 and vision == "true"  # auto 先以 false 估，另列上限
    mb_per_s = cfg["download"]["mbps"] / 8
    dl_mb = meta["filesize"] / 1e6 if n_frames else 0.0  # 不截圖就不下載影片
    dl_sec = cfg["download"]["overhead_sec"] + dl_mb / mb_per_s if dl_mb else 0

    a = cfg["analyze"]
    stages = {
        "fetch": {"sec": cfg["fetch"]["subs_sec"], "tokens": 0},
        "segment": {
            "sec": seg_cfg["base_sec"] + mins * seg_cfg["per_min_video_sec"],
            "tokens": transcript_tokens + 400 * 1,
        },
        "shot": {"sec": dl_sec + n_frames * cfg["shot"]["sec_per_frame"], "tokens": 0},
        "analyze": {
            "sec": n_seg * a["sec_per_segment"],
            "tokens": n_seg * (a["in_tokens_per_segment"] + a["out_tokens_per_segment"]),
        },
        "render": {"sec": cfg["render"]["sec"], "tokens": 0},
    }
    vision_extra = {
        "sec": n_frames * a["vision_sec_per_frame"],
        "tokens": n_frames * a["vision_tokens_per_frame"],
    }
    if vision_on:
        stages["analyze"]["sec"] += vision_extra["sec"]
        stages["analyze"]["tokens"] += vision_extra["tokens"]
    total = {
        "sec": sum(s["sec"] for s in stages.values()),
        "tokens": sum(s["tokens"] for s in stages.values()),
    }
    return {
        "video_id": meta["id"],
        "title": meta["title"],
        "duration": dur,
        "vision": vision,
        "shots": shots,
        "assumed": {"segments": n_seg, "frames": n_frames, "download_mb": round(dl_mb, 1)},
        "has_any_subs": meta["has_any_subs"],
        "stages": {k: {"sec": round(v["sec"]), "tokens": v["tokens"]} for k, v in stages.items()},
        "vision_extra_if_true": vision_extra if (not vision_on and n_frames) else None,
        "total": {"sec": round(total["sec"]), "tokens": total["tokens"]},
    }


def print_report(items: list[dict], cfg: dict) -> None:
    grand = {"sec": 0, "tokens": 0, "mb": 0.0}
    for e in items:
        print(f"\n## {e['title']}  ({e['video_id']}, {fmt_dur(e['duration'])}, shots={e.get('shots', 'auto')}, vision={e['vision']})")
        if not e["has_any_subs"]:
            print("   !! 沒有任何字幕，fetch 會失敗；需要改走語音轉文字（尚未實作）")
        a = e["assumed"]
        shot_note = "不截圖、不下載影片" if not a["frames"] else f"{a['frames']} 張截圖、下載 {a['download_mb']} MB"
        print(f"   假設：{a['segments']} 段、{shot_note}")
        print(f"   {'階段':<10}{'時間':>10}{'tokens':>12}")
        for k, v in e["stages"].items():
            print(f"   {k:<10}{fmt_dur(v['sec']):>10}{v['tokens']:>12,}")
        print(f"   {'小計':<10}{fmt_dur(e['total']['sec']):>10}{e['total']['tokens']:>12,}")
        if e["vision_extra_if_true"]:
            x = e["vision_extra_if_true"]
            print(f"   （若 vision=true 再加：+{fmt_dur(x['sec'])}, +{x['tokens']:,} tokens）")
        grand["sec"] += e["total"]["sec"]
        grand["tokens"] += e["total"]["tokens"]
        grand["mb"] += a["download_mb"]
    ov = cfg["overview"]
    ov_sec = ov["base_sec"] + ov["per_video_sec"] * len(items)
    grand["sec"] += ov_sec
    print(f"\n## 全部 {len(items)} 支")
    print(f"   跨影片彙整   {fmt_dur(ov_sec):>10}")
    print(f"   總時間       {fmt_dur(grand['sec']):>10}")
    print(f"   總 tokens    {grand['tokens']:>10,}")
    print(f"   總下載       {grand['mb']:>8.1f} MB")
    print(f"\n係數在 {config_file('estimate.yaml')}，改了重跑即可（plugin 模式：複製到 ./learn.rules/estimate.yaml 再改）。")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--input", type=Path)
    ap.add_argument("--vision", default="true", choices=["true", "false", "auto"])
    ap.add_argument("--shots", default="auto", choices=["auto", "none", "many"],
                    help="auto=只截看了才懂的畫面（預設）｜none=完全不截圖，也不下載影片｜many=每段至少一張")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--json", action="store_true", help="只輸出 JSON")
    args = ap.parse_args(argv)

    cfg = load_yaml(config_file("estimate.yaml"))
    if args.input:
        inp = load_input(args.input)
        videos = [(v["url"], str(v["vision"]).lower(), str(v.get("shots", "auto"))) for v in inp["videos"]]
        workspace = Path(inp["out"])
    else:
        videos = [(u, args.vision, args.shots) for u in args.urls]
        workspace = args.workspace
    if not videos:
        ap.error("要給 URL 或 --input")

    items = []
    for url, vision, shots in videos:
        meta = probe(url, cfg["download"]["max_height"])
        est = estimate_one(meta, vision, cfg, shots)
        save_json(video_dir(meta["id"], workspace, title=meta["title"]) / "estimate.json", est)
        items.append(est)

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print_report(items, cfg)
        print()
        print_step("estimate", f"{len(items)} 支影片")


if __name__ == "__main__":
    main()
