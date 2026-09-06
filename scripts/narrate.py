"""/learn-narrate：把 narration.json（agent 寫的口語講稿）＋ 原聲片段，合成一份可以用聽的學習內容。

  uv run scripts/narrate.py <id|url> [--voice ...] [--rate +10%] [--dub-voice ...] [--no-dub] [--force]

輸出：workspace/<影片標題>/lesson.mp3（TTS 與原聲交錯）與 lesson.json（章節時間軸）。
clip 有 translation 時另外產 lesson.dub.mp3：原聲換成另一個聲音唸翻譯，網頁上可以切換。
需要 ffmpeg；TTS 用 edge-tts（免費、需網路）。
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from itertools import pairwise
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
CBR = "48k"  # lesson.mp3 用固定位元率，瀏覽器跳轉才精準（見 concat）
DEFAULT_VOICE = {"zh-TW": "zh-TW-HsiaoChenNeural", "zh": "zh-CN-XiaoxiaoNeural", "en": "en-US-AriaNeural"}
# 配音（唸原聲翻譯）用另一個性別的聲音，聽得出來不是講解者本人
DUB_VOICE = {"zh-TW": "zh-TW-YunJheNeural", "zh": "zh-CN-YunxiNeural", "en": "en-US-GuyNeural"}


def voice_for(lang: str) -> str:
    return DEFAULT_VOICE.get(lang) or DEFAULT_VOICE.get(lang.split("-")[0], DEFAULT_VOICE["en"])


def dub_voice_for(lang: str, main: str) -> str:
    """配音聲音：預設同語言的另一個性別；剛好跟講解者撞聲就換成講解的預設聲。"""
    v = DUB_VOICE.get(lang) or DUB_VOICE.get(lang.split("-")[0], DUB_VOICE["en"])
    return voice_for(lang) if v == main else v


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
    # 重新編碼而非 -c copy：串接後的 mp3 才有正確的時間戳，章節跳轉才準。
    # 固定位元率（不是 -q:a 的 VBR）：VBR 的話瀏覽器只能靠 Xing TOC（全檔 100 格）內插著跳，
    # 落點會差一兩秒，karaoke 高亮就跟原聲對不上；CBR 的時間↔位元組是線性的，跳轉才準。
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c:a", "libmp3lame", "-b:a", CBR, "-ar", AR, "-ac", AC, str(out)],
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


MERGE_SEC, MERGE_LEN = 6.0, 70
PRE_ROLL = 0.8  # 原聲往前多切一點，避免第一個字被切掉；這段不顯示文字  # 自動字幕一行常只有兩三個字，併成看得下去的長度


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
    for a, b in pairwise(out):  # 自動字幕的 duration 常蓋到下一句，會讓高亮慢一行
        a["dur"] = round(min(a["dur"], b["at"] - a["at"]), 2)
    return out


def mark(vdir: Path, state: str, **extra) -> None:
    """寫 lesson.status.json，讓步驟 6 產出的 plan.html 知道聽力版正在做。"""
    if state == "done":
        (vdir / "lesson.status.json").unlink(missing_ok=True)
        return
    save_json(vdir / "lesson.status.json", {"state": state, "at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"), **extra})


def part_name(i: int, b: dict, voice: str, rate: str) -> str:
    """檔名帶內容雜湊：內容沒變就重用，調整字幕合併或章節時不必重跑 TTS。"""
    key = ({"kind": "say", "text": b["text"], "voice": voice, "rate": rate}
           if b["kind"] == "say" else {"kind": "clip", "start": b["start"], "end": b["end"], "pre": PRE_ROLL})
    h = hashlib.sha1(json.dumps(key, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:8]
    return f"{i:03d}_{b['kind']}_{h}.mp3"


def dub_part_name(i: int, j: int, text: str, voice: str, rate: str) -> str:
    key = {"kind": "dub", "text": text, "voice": voice, "rate": rate}
    h = hashlib.sha1(json.dumps(key, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:8]
    return f"{i:03d}_dub{j:02d}_{h}.mp3"


DUB_MIN, DUB_MAX = 12, 60  # 一句配音的字數：太短就併回前一句，太長就再斷一次
SENT_END = re.compile(r"(?<=[。！？!?；;])|\n+")


def dub_lines(text: str) -> list[str]:
    """把整段翻譯切成一句一句：每句各自 TTS，長度就是 karaoke 高亮的依據，不必猜時間。"""
    out: list[str] = []
    for chunk in SENT_END.split(text):
        c = (chunk or "").strip()
        while len(c) > DUB_MAX:
            i = max((c.rfind(x, 0, DUB_MAX + 1) for x in "，、,：: "), default=-1)
            if i <= 0:
                i = DUB_MAX - 1
            out.append(c[:i + 1].strip())
            c = c[i + 1:].strip()
        if c:
            out.append(c)
    merged: list[str] = []
    for sline in out:
        if merged and len(merged[-1]) < DUB_MIN and len(merged[-1]) + len(sline) <= DUB_MAX:
            merged[-1] += sline
        else:
            merged.append(sline)
    return merged


def build(vdir: Path, vid: str, voice: str | None, rate: str | None,
          dub_voice: str | None, no_dub: bool, no_cache: bool) -> dict:
    nar = load_json(vdir / "narration.json")
    meta = load_json(vdir / "meta.json")
    lang = meta.get("output_lang", "zh-TW")
    titles = {s["id"]: s["title"] for s in load_json(vdir / "analysis.json")["segments"]}
    seg_clips = {s["id"]: s.get("clips", []) for s in load_json(vdir / "segments.json")["segments"]}
    voice = voice or nar.get("voice") or voice_for(lang)
    rate = rate or nar.get("rate", "+0%")
    dub_voice = dub_voice or nar.get("dub_voice") or dub_voice_for(lang, voice)

    blocks = nar["blocks"]
    has_clip = any(b["kind"] == "clip" for b in blocks)
    audio = ensure_audio(vid, vdir) if has_clip else None
    events = load_json(vdir / "transcript.json")["events"] if has_clip else []
    parts_dir = vdir / "lesson_parts"
    parts_dir.mkdir(exist_ok=True)

    parts, timeline, t, reused = [], [], 0.0, 0
    dparts, dtl, dt = [], [], 0.0  # 翻譯版：say 沿用同一個檔，clip 換成配音
    wanted = set()
    for i, b in enumerate(blocks, 1):
        p = parts_dir / part_name(i, b, voice, rate)
        wanted.add(p.name)
        cached = p.exists() and not no_cache
        at = t
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
            pre = min(PRE_ROLL, src[0])
            if not cached:
                cut(audio, src[0] - pre, src[1], p)
            else:
                reused += 1
            d = duration(p)
            lines = clip_lines(events, src[0], src[1], t + pre)
        entry = {
            "i": i, "at": round(t, 2), "dur": round(d, 2), "kind": b["kind"], "seg_id": b["seg_id"],
            "seg_title": titles.get(b["seg_id"], ""),
            "text": b.get("text", ""), "label": b.get("label", ""),
            "source_start": src[0], "source_end": src[1], "lines": lines,
            "translation": next((c.get("translation", "") for c in seg_clips.get(b["seg_id"], [])
                                 if b["kind"] == "clip" and abs(c["start"] - b["start"]) < 1), ""),
        }
        timeline.append(entry)
        parts.append(p)
        t += d

        if no_dub:
            continue
        if b["kind"] == "clip" and entry["translation"]:
            off, dl = 0.0, []
            for j, text in enumerate(dub_lines(entry["translation"]), 1):
                q = parts_dir / dub_part_name(i, j, text, dub_voice, rate)
                wanted.add(q.name)
                if q.exists() and not no_cache:
                    reused += 1
                else:
                    synth(text, dub_voice, rate, q)
                du = duration(q)
                dl.append({"at": round(dt + off, 2), "dur": round(du, 2), "text": text})
                dparts.append(q)
                off += du
            dtl.append(dict(entry, at=round(dt, 2), dur=round(off, 2), kind="dub", lines=dl,
                            orig_text=" ".join(x["text"] for x in lines)))
            dt += off
        else:  # say（同一個檔，不必重做）或沒有翻譯的 clip：兩軌一樣，只是時間偏移不同
            delta = dt - at
            dtl.append(dict(entry, at=round(dt, 2),
                            lines=[dict(x, at=round(x["at"] + delta, 2)) for x in lines]))
            dparts.append(p)
            dt += d

    for f in parts_dir.iterdir():  # 清掉已經用不到的舊片段
        if f.name not in wanted:
            f.unlink()
    out = vdir / "lesson.mp3"
    concat(parts, out)

    dub_out = vdir / "lesson.dub.mp3"
    dub = None
    if any(e["kind"] == "dub" for e in dtl):
        concat(dparts, dub_out)
        dub = {"file": dub_out.name, "voice": dub_voice, "duration": round(dt, 2),
               "chapters": chapters_of(dtl), "timeline": dtl}
    else:
        dub_out.unlink(missing_ok=True)

    lesson = {
        "video_id": vid, "voice": voice, "rate": rate,
        "duration": round(t, 2), "file": out.name,
        "chapters": chapters_of(timeline), "timeline": timeline,
        "dub": dub,
        "reused_parts": reused, "total_parts": len(parts) + (len(dparts) if dub else 0),
    }
    save_json(vdir / "lesson.json", lesson)
    return lesson


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id")
    ap.add_argument("--voice", help="edge-tts 語音；預設依 output_lang")
    ap.add_argument("--rate", help="語速，例如 +15%%")
    ap.add_argument("--dub-voice", help="唸原聲翻譯的語音；預設是跟講解不同性別的同語言聲音")
    ap.add_argument("--no-dub", action="store_true", help="不產 lesson.dub.mp3（原聲翻譯版）")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-cache", action="store_true", help="不重用 lesson_parts/ 裡的舊片段，全部重做")
    ap.add_argument("--mark-pending", action="store_true",
                    help="只標記「聽力版產生中」就結束；步驟 6 render 前先呼叫，plan.html 才會顯示處理中")
    args = ap.parse_args(argv)

    if not shutil.which("ffmpeg"):
        raise SystemExit("找不到 ffmpeg：sudo apt install ffmpeg")
    vid = video_id(args.id)
    vdir = video_dir(vid, args.workspace)
    if args.mark_pending:
        mark(vdir, "building")
        print(f"已標記聽力版產生中 → {vdir / 'lesson.status.json'}")
        return
    if not (vdir / "narration.json").exists():
        raise SystemExit(f"缺 {vdir / 'narration.json'}：先由 agent 依 rules/narration.md 產生")
    # 舊的 lesson.json 沒有 dub 這個 key：那是還沒做過翻譯配音的站，不必 --force 就補做
    lp = vdir / "lesson.json"
    done = (vdir / "lesson.mp3").exists() and (args.no_dub or (lp.exists() and "dub" in load_json(lp)))
    if done and not args.force:
        print(f"跳過：{vdir / 'lesson.mp3'} 已存在（--force 重做）")
        print_step("narrate", "已存在")
        return
    mark(vdir, "building")
    try:
        with Timer(vdir, "narrate"):
            lesson = build(vdir, vid, args.voice, args.rate, args.dub_voice, args.no_dub, args.no_cache)
    except Exception:
        mark(vdir, "failed")
        raise
    mark(vdir, "done")
    n_clip = sum(1 for e in lesson["timeline"] if e["kind"] == "clip")
    cache = f"，重用 {lesson['reused_parts']}/{lesson['total_parts']} 段" if lesson["reused_parts"] else ""
    print(f"OK {fmt_dur(lesson['duration'])}（{len(lesson['chapters'])} 章、{n_clip} 段原聲{cache}）→ {vdir / 'lesson.mp3'}")
    if lesson["dub"]:
        n_dub = sum(1 for e in lesson["dub"]["timeline"] if e["kind"] == "dub")
        print(f"   翻譯版 {fmt_dur(lesson['dub']['duration'])}（{n_dub} 段配音，{lesson['dub']['voice']}）→ {vdir / 'lesson.dub.mp3'}")
    print_step("narrate", f"{fmt_dur(lesson['duration'])} 聽力版")


if __name__ == "__main__":
    main()
