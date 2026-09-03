"""/learn-shot：依 segments.json 的 shots 下載影片（一次）並用 ffmpeg 抽幀。

用法：uv run scripts/screenshot.py <id> [--force] [--keep-video]
輸出：workspace/<id>/frames/s<seg>_<秒>.jpg；同時把路徑寫回 segments.json 的 shots[].file
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    CONFIG,
    DEFAULT_WORKSPACE,
    Timer,
    load_json,
    load_yaml,
    save_json,
    video_dir,
    video_id,
)


def download(vid: str, vdir: Path, max_height: int) -> Path:
    existing = list(vdir.glob("video.*"))
    if existing:
        return existing[0]
    fmt = f"bv*[height<={max_height}]/b[height<={max_height}]/b"
    subprocess.run(
        ["yt-dlp", "--no-playlist", "-f", fmt, "-o", str(vdir / "video.%(ext)s"),
         f"https://www.youtube.com/watch?v={vid}"],
        check=True, capture_output=True, text=True,
    )
    return next(vdir.glob("video.*"))


def grab(video: Path, t: float, out: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video),
         "-frames:v", "1", "-q:v", "3", str(out)],
        check=True,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--keep-video", action="store_true", help="抽完不刪影片檔")
    args = ap.parse_args(argv)

    if not shutil.which("ffmpeg"):
        raise SystemExit("找不到 ffmpeg：sudo apt install ffmpeg")
    vid = video_id(args.id)
    vdir = video_dir(vid, args.workspace)  # 不存在會報錯：要先 fetch
    seg_path = vdir / "segments.json"
    if not seg_path.exists():
        raise SystemExit(f"缺 {seg_path}，先跑 /learn-segment")
    segs = load_json(seg_path)
    shots = [(s["id"], sh) for s in segs["segments"] for sh in s.get("shots", [])]
    if not shots:
        print("segments.json 沒有任何 shots，不需截圖")
        return

    frames = vdir / "frames"
    frames.mkdir(exist_ok=True)
    todo = [(sid, sh) for sid, sh in shots
            if args.force or not (frames / f"s{sid:02d}_{int(sh['t'])}.jpg").exists()]
    if not todo:
        print(f"跳過：{len(shots)} 張都已存在（--force 重截）")
        return

    cfg = load_yaml(CONFIG / "estimate.yaml")
    with Timer(vdir, "shot"):
        video = download(vid, vdir, cfg["download"]["max_height"])
        for sid, sh in todo:
            out = frames / f"s{sid:02d}_{int(sh['t'])}.jpg"
            grab(video, sh["t"], out)
            sh["file"] = f"frames/{out.name}"
        if not args.keep_video:
            video.unlink()
    for sid, sh in shots:
        sh.setdefault("file", f"frames/s{sid:02d}_{int(sh['t'])}.jpg")
    save_json(seg_path, segs)
    print(f"OK {len(todo)} 張 → {frames}")


if __name__ == "__main__":
    main()
