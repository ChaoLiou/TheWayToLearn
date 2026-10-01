"""回收各站的中間檔：留下成品與 LLM 產出，刪掉「重跑就會再有」的東西。

  uv run scripts/prune.py                      # 只列出可以回收什麼、多少（不刪）
  uv run scripts/prune.py --delete             # 真的刪
  uv run scripts/prune.py --delete --keep-cache   # 留 lesson_parts/（只刪重抓成本低的）
  uv run scripts/prune.py <id|url> ...         # 只處理某幾站

分三類，風險由低到高：
  refetch  audio.mp3、subs.*.json3／vtt、.tmp-* 殘骸
           —— 重跑 yt-dlp 就會再有，transcript.json 已經是它們的成品。
  cache    lesson_parts/（TTS 與原聲切片的快取）
           —— 刪了 lesson.mp3 還在，只有「改講稿要重產」時才要重跑一次 TTS。
  keep     其他全部。特別是 LLM 產出（analysis／segments／digest／notes／narration／_overview）
           重跑要花錢又不會一樣，一律不動。

安全閥：一站只有在 lesson.mp3 已經產出時才回收它的 audio.mp3 / lesson_parts/，
免得把正在跑 narrate 的站清掉。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEFAULT_WORKSPACE, find_video_dir, video_id

# 成品與 LLM 產出：永遠不動
KEEP = {
    "meta.json", "transcript.json", "segments.json", "analysis.json", "_overview.json",
    "digest.json", "notes.json", "narration.json", "lesson.json", "estimate.json", "timings.json",
    "plan.html", "lesson.mp3", "lesson.dub.mp3", "captions.js", "lesson.status.json",
}


def human(n: int) -> str:
    return f"{n / 1e9:.2f} GB" if n >= 1e9 else (f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB")


def size_of(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size


def reclaimable(d: Path, keep_cache: bool = False) -> list[tuple[Path, str]]:
    """這一站可以回收的東西：[(路徑, 類別)]。"""
    out: list[tuple[Path, str]] = []
    narrated = (d / "lesson.mp3").exists()
    for p in sorted(d.iterdir()):
        if p.name in KEEP or p.name == "frames":
            continue
        if p.name.startswith(".tmp-"):
            out.append((p, "refetch"))
        elif p.is_file() and (p.stem == "audio" or p.name.startswith("subs.")):
            # audio.* 是切原聲用的來源，narrate.py 的 ensure_audio() 會自己重抓
            if p.stem != "audio" or narrated:
                out.append((p, "refetch"))
        elif p.name == "lesson_parts" and narrated and not keep_cache:
            out.append((p, "cache"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="video id 或 URL；不給 = workspace 下全部")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--delete", action="store_true", help="真的刪除（不給只是列出來看）")
    ap.add_argument("--keep-cache", action="store_true", help="留著 lesson_parts/，只回收重抓成本低的")
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
        dirs = sorted(d for d in ws.iterdir()
                      if d.is_dir() and not d.name.startswith((".", "_")) and (d / "meta.json").exists())

    by_kind: dict[str, int] = {}
    total = n_files = 0
    rows = []
    for d in dirs:
        items = reclaimable(d, args.keep_cache)
        if not items:
            continue
        s = sum(size_of(p) for p, _ in items)
        total += s
        n_files += sum(1 for _ in items)
        for p, kind in items:
            by_kind[kind] = by_kind.get(kind, 0) + size_of(p)
        rows.append((d, items, s))

    if not rows:
        print("沒有可以回收的中間檔。")
        return
    for d, items, s in rows:
        names = "、".join(f"{p.name}{'/' if p.is_dir() else ''}" for p, _ in items)
        print(f"  · {d.name[:46]:48} {human(s):>9}  {names}")
    print(f"\n可回收 {n_files} 項、共 {human(total)}"
          + ("".join(f"（{k} {human(v)}）" for k, v in sorted(by_kind.items()))))
    ws_total = sum(f.stat().st_size for f in ws.rglob("*") if f.is_file())
    print(f"workspace 現在 {human(ws_total)} → 回收後 {human(ws_total - total)}")

    if not args.delete:
        print("\n這只是列出來看。要真的刪：加 --delete（想留 TTS 快取再加 --keep-cache）")
        print("代價：refetch 類重跑 yt-dlp 就有；cache 類只有改講稿重產語音解析時要重跑一次 TTS。")
        return
    for d, items, _ in rows:
        for p, _ in items:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    print(f"\n已回收 {human(total)}。")


if __name__ == "__main__":
    main()
