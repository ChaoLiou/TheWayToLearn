"""把 workspace 裡「要上線的檔案」整理成 dist/，可選擇直接部署到 Cloudflare Pages。

  uv run scripts/publish.py                          # 只整理 dist/ 並列出內容
  uv run scripts/publish.py --deploy                 # 整理後用 wrangler 部署
  uv run scripts/publish.py --project-name my-atlas --deploy

只複製：atlas.html、各站 plan.html、frames/、lesson.mp3、lesson.dub.mp3（外加一份 index.html = atlas.html）。
不複製：原始音訊 audio.mp3、TTS 片段快取 lesson_parts/、transcript 與各種 json（內容已內嵌在 html）。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEFAULT_WORKSPACE, locked

MAX_FILE = 25 * 1024 * 1024  # Cloudflare Pages 單檔上限
KEEP = ("plan.html", "lesson.mp3", "lesson.dub.mp3")


def human(n: int) -> str:
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"


def collect(ws: Path) -> list[tuple[Path, Path]]:
    """回傳 [(來源, dist 內的相對路徑)]。"""
    out: list[tuple[Path, Path]] = []
    atlas = ws / "atlas.html"
    if atlas.exists():
        out.append((atlas, Path("atlas.html")))
        out.append((atlas, Path("index.html")))  # 根網址直接進地圖
    for d in sorted(p for p in ws.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        for name in KEEP:
            f = d / name
            if f.exists():
                out.append((f, Path(d.name) / name))
        frames = d / "frames"
        if frames.is_dir():
            out += [(f, Path(d.name) / "frames" / f.name) for f in sorted(frames.iterdir()) if f.is_file()]
    return out


def build(ws: Path, dist: Path) -> list[tuple[Path, Path]]:
    items = collect(ws)
    if not items:
        raise SystemExit(f"{ws} 裡沒有可發佈的檔案（先跑 /learn 產生 plan.html）")
    if dist.exists():
        shutil.rmtree(dist)
    for src, rel in items:
        dst = dist / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return items


def report(ws: Path, dist: Path, items: list[tuple[Path, Path]]) -> int:
    total = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    big = [(rel, src.stat().st_size) for src, rel in items if src.stat().st_size > MAX_FILE]
    stations = sorted({rel.parts[0] for _, rel in items if len(rel.parts) > 1})
    print(f"dist: {dist}")
    print(f"  {len(items)} 個檔案、{human(total)}（workspace 全部是 {human(sum(f.stat().st_size for f in ws.rglob('*') if f.is_file()))}）")
    for s in stations:
        n = sum(1 for _, rel in items if rel.parts[0] == s)
        size = sum((dist / rel).stat().st_size for _, rel in items if rel.parts[0] == s)
        mp3 = dist / s / "lesson.mp3"
        print(f"  · {s[:52]:54} {n:3} 檔 {human(size):>9}{'  含聽力版' if mp3.exists() else ''}")
    for rel, size in big:
        print(f"  !! {rel} 是 {human(size)}，超過 Cloudflare Pages 單檔 25 MB 上限")
    return len(big)


def deploy(dist: Path, project: str) -> None:
    cmd = ["wrangler", "pages", "deploy", str(dist), "--project-name", project]
    if not shutil.which("wrangler"):
        cmd = ["npx", "--yes", "wrangler@latest", *cmd[1:]]
        if not shutil.which("npx"):
            raise SystemExit("找不到 wrangler 也沒有 npx：npm i -g wrangler 之後再跑 wrangler login")
    print("\n$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--out", type=Path, help="預設 <workspace 的上一層>/dist")
    ap.add_argument("--project-name", default="atlas-of-knowledge", help="Cloudflare Pages 專案名")
    ap.add_argument("--deploy", action="store_true", help="整理完直接用 wrangler 部署")
    args = ap.parse_args(argv)

    ws = args.workspace
    dist = args.out or ws.parent / "dist"
    with locked(ws / ".publish.lock", "dist/"):  # 兩個 publish 同時跑會互刪 dist/
        items = build(ws, dist)
        big = report(ws, dist, items)
        if args.deploy:
            if big:
                raise SystemExit("有檔案超過 25 MB，先處理再部署（降位元率或改用 --set clips=精華）")
            deploy(dist, args.project_name)
    if not args.deploy:
        print(f"\n要部署：uv run scripts/publish.py --deploy --project-name {args.project_name}")
        print("首次使用先 npm i -g wrangler && wrangler login；部署後到 Cloudflare Zero Trust → Access 加上登入限制。")


if __name__ == "__main__":
    main()
