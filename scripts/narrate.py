"""/learn-narrate：把 narration.json（agent 寫的口語講稿）＋ 原聲片段，合成一份可以用聽的學習內容。

  uv run scripts/narrate.py <id|url> [--voice ...] [--rate +10%] [--force] [--keep-parts]

輸出：workspace/<影片標題>/lesson.mp3（TTS 與原聲交錯）與 lesson.json（章節時間軸）。
需要 ffmpeg；TTS 用 edge-tts（免費、需網路）。
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
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


def snap(events: list[dict], start: float, end: float) -> tuple[float, float]:
    """把 clip 的起訖對齊到 transcript 的句子邊界，避免從半句開始或斷在半句。"""
    starts = [e["start"] for e in events]
    ends = [e["start"] + e["duration"] for e in events]
    lo = max((x for x in starts if x <= start + 0.6), default=starts[0] if starts else start)
    hi = min((x for x in ends if x >= end - 0.6), default=ends[-1] if ends else end)
    return (lo, max(hi, lo + 1))


MERGE_SEC, MERGE_LEN = 6.0, 70  # 自動字幕一行常只有兩三個字，併成看得下去的長度


def clip_lines(events: list[dict], start: float, end: float, offset: float) -> list[dict]:
    """clip 範圍內的字幕，併成順口的長度並換算成 lesson.mp3 的絕對時間，給 karaoke 用。"""
    out: list[dict] = []
    for e in events:
        a, b = e["start"], e["start"] + e["duration"]
        if b <= start or a >= end:
            continue
        a, b = max(a, start), min(b, end)
        at, dur, text = round(offset + a - start, 2), round(b - a, 2), e["text"].strip()
        last = out[-1] if out else None
        if last and last["dur"] < MERGE_SEC and len(last["text"]) + len(text) <= MERGE_LEN:
            last["text"] = f"{last['text']} {text}".strip()
            last["dur"] = round(at + dur - last["at"], 2)
        else:
            out.append({"at": at, "dur": dur, "text": text})
    return out


def part_name(i: int, b: dict, voice: str, rate: str) -> str:
    """檔名帶內容雜湊：內容沒變就重用，調整字幕合併或章節時不必重跑 TTS。"""
    key = ({"kind": "say", "text": b["text"], "voice": voice, "rate": rate}
           if b["kind"] == "say" else {"kind": "clip", "start": b["start"], "end": b["end"]})
    h = hashlib.sha1(json.dumps(key, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:8]
    return f"{i:03d}_{b['kind']}_{h}.mp3"


def build(vdir: Path, vid: str, voice: str | None, rate: str | None, no_cache: bool) -> dict:
    nar = load_json(vdir / "narration.json")
    meta = load_json(vdir / "meta.json")
    titles = {s["id"]: s["title"] for s in load_json(vdir / "analysis.json")["segments"]}
    voice = voice or nar.get("voice") or voice_for(meta.get("output_lang", "zh-TW"))
    rate = rate or nar.get("rate", "+0%")

    blocks = nar["blocks"]
    has_clip = any(b["kind"] == "clip" for b in blocks)
    audio = ensure_audio(vid, vdir) if has_clip else None
    events = load_json(vdir / "transcript.json")["events"] if has_clip else []
    parts_dir = vdir / "lesson_parts"
    parts_dir.mkdir(exist_ok=True)

    parts, timeline, t, reused = [], [], 0.0, 0
    wanted = set()
    for i, b in enumerate(blocks, 1):
        p = parts_dir / part_name(i, b, voice, rate)
        wanted.add(p.name)
        cached = p.exists() and not no_cache
        if b["kind"] == "say":
            if not cached:
                synth(b["text"], voice, rate, p)
            else:
                reused += 1
            d = duration(p)
            lines = [{"at": round(t, 2), "dur": round(d, 2), "text": b["text"]}]
            src = (None, None)
        else:
            src = snap(events, b["start"], b["end"])
            if not cached:
                cut(audio, src[0], src[1], p)
            else:
                reused += 1
            d = duration(p)
            lines = clip_lines(events, src[0], src[1], t)
        timeline.append({
            "at": round(t, 2), "dur": round(d, 2), "kind": b["kind"], "seg_id": b["seg_id"],
            "seg_title": titles.get(b["seg_id"], ""),
            "text": b.get("text", ""), "label": b.get("label", ""),
            "source_start": src[0], "source_end": src[1], "lines": lines,
        })
        parts.append(p)
        t += d

    for f in parts_dir.iterdir():  # 清掉已經用不到的舊片段
        if f.name not in wanted:
            f.unlink()
    out = vdir / "lesson.mp3"
    concat(parts, out)

    lesson = {
        "video_id": vid, "voice": voice, "rate": rate,
        "duration": round(t, 2), "file": out.name,
        "chapters": chapters_of(timeline), "timeline": timeline,
        "reused_parts": reused, "total_parts": len(parts),
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
    ap.add_argument("--no-cache", action="store_true", help="不重用 lesson_parts/ 裡的舊片段，全部重做")
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
        lesson = build(vdir, vid, args.voice, args.rate, args.no_cache)
    n_clip = sum(1 for e in lesson["timeline"] if e["kind"] == "clip")
    cache = f"，重用 {lesson['reused_parts']}/{lesson['total_parts']} 段" if lesson["reused_parts"] else ""
    print(f"OK {fmt_dur(lesson['duration'])}（{len(lesson['chapters'])} 章、{n_clip} 段原聲{cache}）→ {vdir / 'lesson.mp3'}")
    print_step("narrate", f"{fmt_dur(lesson['duration'])} 聽力版")


if __name__ == "__main__":
    main()
