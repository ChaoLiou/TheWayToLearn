"""/learn-narrate：把 narration.json（agent 寫的口語講稿）＋ 原聲片段，合成一份可以用聽的學習內容。

  uv run scripts/narrate.py <id|url> [--voice ...] [--rate +10%] [--force] [--keep-parts]

輸出：workspace/<影片標題>/lesson.mp3（TTS 與原聲交錯）與 lesson.json（章節時間軸）。
需要 ffmpeg；TTS 用 edge-tts（免費、需網路）。
"""
from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    DEFAULT_WORKSPACE,
    Timer,
    fmt_dur,
    load_json,
    print_step,
    save_json,
    video_dir,
    video_id,
)

AR, AC = "24000", "1"  # edge-tts 的輸出規格；原聲片段轉成一樣才能直接 concat
DEFAULT_VOICE = {"zh-TW": "zh-TW-HsiaoChenNeural", "zh": "zh-CN-XiaoxiaoNeural", "en": "en-US-AriaNeural"}


def voice_for(lang: str) -> str:
    return DEFAULT_VOICE.get(lang) or DEFAULT_VOICE.get(lang.split("-")[0], DEFAULT_VOICE["en"])


def ensure_audio(vid: str, vdir: Path) -> Path:
    """只抓音訊（比影片小很多）。已存在就沿用。"""
    existing = list(vdir.glob("audio.*"))
    if existing:
        return existing[0]
    subprocess.run(
        ["yt-dlp", "--no-playlist", "-f", "ba/b", "-x", "--audio-format", "mp3",
         "-o", str(vdir / "audio.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"],
        check=True, capture_output=True, text=True,
    )
    return next(vdir.glob("audio.*"))


async def _tts(text: str, voice: str, rate: str, out: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def synth(text: str, voice: str, rate: str, out: Path) -> Path:
    asyncio.run(_tts(text, voice, rate, out))
    return out


def cut(audio: Path, start: float, end: float, out: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-to", f"{end:.2f}",
         "-i", str(audio), "-ar", AR, "-ac", AC, "-b:a", "64k", str(out)],
        check=True,
    )
    return out


def duration(p: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def concat_file(parts: list[Path]) -> str:
    """ffmpeg concat demuxer 的清單內容；單引號要跳脫。"""
    lines = []
    for p in parts:
        safe = str(p.resolve()).replace("'", "'\\''")
        lines.append(f"file '{safe}'\n")
    return "".join(lines)


def concat(parts: list[Path], out: Path) -> None:
    listing = out.parent / "_concat.txt"
    listing.write_text(concat_file(parts), encoding="utf-8")
    # 重新編碼而非 -c copy：串接後的 mp3 才有正確的時間戳與 Xing 標頭，章節跳轉才準
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c:a", "libmp3lame", "-q:a", "6", "-ar", AR, "-ac", AC, str(out)],
        check=True,
    )
    listing.unlink()


def chapters_of(timeline: list[dict]) -> list[dict]:
    out: list[dict] = []
    for e in timeline:
        if not out or out[-1]["seg_id"] != e["seg_id"]:
            out.append({"seg_id": e["seg_id"], "title": e["seg_title"], "at": e["at"]})
    return out


def build(vdir: Path, vid: str, voice: str | None, rate: str | None, keep_parts: bool) -> dict:
    nar = load_json(vdir / "narration.json")
    meta = load_json(vdir / "meta.json")
    titles = {s["id"]: s["title"] for s in load_json(vdir / "analysis.json")["segments"]}
    voice = voice or nar.get("voice") or voice_for(meta.get("output_lang", "zh-TW"))
    rate = rate or nar.get("rate", "+0%")

    blocks = nar["blocks"]
    audio = ensure_audio(vid, vdir) if any(b["kind"] == "clip" for b in blocks) else None
    parts_dir = vdir / "lesson_parts"
    parts_dir.mkdir(exist_ok=True)

    parts, timeline, t = [], [], 0.0
    for i, b in enumerate(blocks, 1):
        p = parts_dir / f"{i:03d}_{b['kind']}.mp3"
        if b["kind"] == "say":
            synth(b["text"], voice, rate, p)
        else:
            cut(audio, b["start"], b["end"], p)
        d = duration(p)
        timeline.append({
            "at": round(t, 2), "dur": round(d, 2), "kind": b["kind"], "seg_id": b["seg_id"],
            "seg_title": titles.get(b["seg_id"], ""),
            "text": b.get("text", ""), "label": b.get("label", ""),
            "source_start": b.get("start"), "source_end": b.get("end"),
        })
        parts.append(p)
        t += d

    out = vdir / "lesson.mp3"
    concat(parts, out)
    if not keep_parts:
        shutil.rmtree(parts_dir)

    lesson = {
        "video_id": vid, "voice": voice, "rate": rate,
        "duration": round(t, 2), "file": out.name,
        "chapters": chapters_of(timeline), "timeline": timeline,
    }
    save_json(vdir / "lesson.json", lesson)
    return lesson


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id")
    ap.add_argument("--voice", help="edge-tts 語音；預設依 output_lang")
    ap.add_argument("--rate", help="語速，例如 +15%%")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--keep-parts", action="store_true", help="保留每段音檔，方便重做單段")
    args = ap.parse_args(argv)

    if not shutil.which("ffmpeg"):
        raise SystemExit("找不到 ffmpeg：sudo apt install ffmpeg")
    vid = video_id(args.id)
    vdir = video_dir(vid, args.workspace)
    if not (vdir / "narration.json").exists():
        raise SystemExit(f"缺 {vdir / 'narration.json'}：先由 agent 依 rules/narration.md 產生")
    if (vdir / "lesson.mp3").exists() and not args.force:
        print(f"跳過：{vdir / 'lesson.mp3'} 已存在（--force 重做）")
        print_step("narrate", "已存在")
        return
    with Timer(vdir, "narrate"):
        lesson = build(vdir, vid, args.voice, args.rate, args.keep_parts)
    n_clip = sum(1 for e in lesson["timeline"] if e["kind"] == "clip")
    print(f"OK {fmt_dur(lesson['duration'])}（{len(lesson['chapters'])} 章、{n_clip} 段原聲）→ {vdir / 'lesson.mp3'}")
    print_step("narrate", f"{fmt_dur(lesson['duration'])} 聽力版")


if __name__ == "__main__":
    main()
