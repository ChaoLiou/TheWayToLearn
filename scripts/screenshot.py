"""/learn-shot：依 segments.json 的 shots 下載影片（一次）並用 ffmpeg 抽幀。
部落格站的 shot 是文章裡的圖片（transcript.images），直接下載，不需要 ffmpeg 也不下載影片。

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
    DEFAULT_WORKSPACE,
    Timer,
    config_file,
    is_blog,
    load_json,
    load_yaml,
    print_step,
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


def frame_path(frames: Path, sid: int, t: float) -> Path | None:
    """已存在的截圖檔（影片是 .jpg，文章圖片副檔名不一定）。"""
    return next(iter(frames.glob(f"s{sid:02d}_{int(t)}.*")), None)


def grab_images(frames: Path, todo: list, images: list[dict]) -> None:
    """部落格：每個 shot 對到文中一張圖（shot.src 或離 t 最近的），下載到 frames/。"""
    import blog

    for sid, sh in todo:
        im = blog.image_for(images, sh["t"], sh.get("src"))
        if not im:
            print(f"  segment {sid} t={sh['t']}：文章裡沒有圖片，跳過")
            continue
        try:
            out = blog.download_image(im["src"], frames / f"s{sid:02d}_{int(sh['t'])}")
        except (OSError, ValueError) as e:  # 一張圖抓不到不要讓整站停下來
            print(f"  segment {sid} t={sh['t']}：下載失敗 {im['src']}（{e}）")
            continue
        sh["src"] = im["src"]
        sh["file"] = f"frames/{out.name}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--keep-video", action="store_true", help="抽完不刪影片檔")
    args = ap.parse_args(argv)

    vid = video_id(args.id)
    vdir = video_dir(vid, args.workspace)  # 不存在會報錯：要先 fetch
    blog_src = is_blog(vid) or ((vdir / "meta.json").exists() and is_blog(load_json(vdir / "meta.json")))
    if not blog_src and not shutil.which("ffmpeg"):
        raise SystemExit("找不到 ffmpeg：sudo apt install ffmpeg")
    seg_path = vdir / "segments.json"
    if not seg_path.exists():
        raise SystemExit(f"缺 {seg_path}，先跑 /learn-segment")
    segs = load_json(seg_path)
    shots = [(s["id"], sh) for s in segs["segments"] for sh in s.get("shots", [])]
    if not shots:
        print("segments.json 沒有任何 shots，不需截圖（shots_mode="
              f"{segs.get('shots_mode', 'auto')}）")
        print_step("shot", "跳過：這支影片不截圖")
        return

    frames = vdir / "frames"
    frames.mkdir(exist_ok=True)
    todo = [(sid, sh) for sid, sh in shots if args.force or not frame_path(frames, sid, sh["t"])]
    if not todo:
        print(f"跳過：{len(shots)} 張都已存在（--force 重截）")
        print_step("shot", f"{len(shots)} 張已存在")
        return

    cfg = load_yaml(config_file("estimate.yaml"))
    with Timer(vdir, "shot"):
        if blog_src:
            images = load_json(vdir / "transcript.json").get("images", [])
            grab_images(frames, todo, images)
        else:
            video = download(vid, vdir, cfg["download"]["max_height"])
            for sid, sh in todo:
                out = frames / f"s{sid:02d}_{int(sh['t'])}.jpg"
                grab(video, sh["t"], out)
                sh["file"] = f"frames/{out.name}"
            if not args.keep_video:
                video.unlink()
    for sid, sh in shots:
        if "file" not in sh:
            p = frame_path(frames, sid, sh["t"])
            if p:
                sh["file"] = f"frames/{p.name}"
    save_json(seg_path, segs)
    got = sum(1 for _, sh in todo if sh.get("file"))
    print(f"OK {got} 張 → {frames}")
    print_step("shot", f"{sum(1 for _, sh in shots if sh.get('file'))} 張{'圖片' if blog_src else '截圖'}")


if __name__ == "__main__":
    main()
