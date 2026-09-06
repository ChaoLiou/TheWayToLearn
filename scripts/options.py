"""列出某個 skill 會用到的參數：預設值、意義、可選值。skill 開始前先跑這支，把表原樣給使用者看，
再問要不要調整。使用者已在指令中指定的參數會標成「已指定」。

  uv run scripts/options.py learn                       # /learn 會用到的全部參數
  uv run scripts/options.py learn-shot                  # 單一階段
  uv run scripts/options.py learn --set shots=none      # 標記已指定，其餘顯示預設
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEFAULT_WORKSPACE, config_file, load_yaml

# name -> (flag, 預設, 一句話意義, [(值, 說明)])
PARAMS: dict[str, tuple[str, str, str, list[tuple[str, str]]]] = {
    "shots": ("--shots", "auto", "要不要擷取影片畫面", [
        ("auto", "只截「看了才懂」的畫面（圖表、程式碼、白板）；整支都沒有就自動不截"),
        ("none", "完全不截圖，也不下載影片 —— 畫面沒資訊、重點都在講話時用，明顯更快更省"),
        ("many", "每段至少一張 —— 投影片型、逐頁講解的影片"),
    ]),
    "vision": ("--vision", "true", "AI 要不要逐張看截圖再寫說明", [
        ("true", "看圖，說明能對照畫面內容（較慢、較多 token）"),
        ("false", "只讀字幕，截圖仍會放進文件但 AI 不看"),
        ("auto", "由 AI 依字幕裡的視覺指示語（「看這張圖」）自行判斷"),
    ]),
    "lang": ("--lang", "zh-TW,zh,en", "字幕語言優先序（抓得到哪個就用哪個）", []),
    "output_lang": ("--output-lang", "跟著你的對話語言", "產出文件與介面的語言", [
        ("zh-TW", "繁體中文"), ("en", "English"),
    ]),
    "force": ("--force", "false", "已有結果時是否重跑覆蓋", [
        ("false", "已存在就跳過（預設）"), ("true", "重新產生，覆蓋舊檔"),
    ]),
    "keep_video": ("--keep-video", "false", "抽完影格後是否保留影片檔", [
        ("false", "刪掉，省磁碟（預設）"), ("true", "保留，之後補截圖不必重載"),
    ]),
    "combined": ("--combined", "false", "多支影片要不要合併成一份 plan.html", [
        ("false", "每支影片各自一份（預設）"), ("true", "合併成一份，需要跨影片的 _overview.json"),
    ]),
    "narrate": ("--narrate", "true", "要不要順便產出聽力版（第 8 步）", [
        ("true", "產出 lesson.mp3：TTS 講解與作者原聲交錯，plan.html 有播放器與講稿（預設）"),
        ("false", "只產出網頁版，不做聲音；之後想要再跑 /learn-narrate 也可以"),
    ]),
    "clips": ("clips（在 segments.json）", "整段", "聽力版要播多長的作者原聲", [
        ("整段", "段落完整播出（預設）；超過 150 秒的段落取其中核心 60–120 秒"),
        ("精華", "只播 20–40 秒的關鍵句，聽力版較短但脈絡較少"),
        ("不放", "全部用 TTS 講解，不播原聲"),
    ]),
    "voice": ("--voice", "依語言自動選", "聽力版的 TTS 語音", [
        ("zh-TW-HsiaoChenNeural", "中文女聲，語氣友善（中文預設）"),
        ("zh-TW-YunJheNeural", "中文男聲"),
        ("en-US-AriaNeural", "英文女聲（英文預設）"),
    ]),
    "dub": ("dub（--no-dub 關掉）", "true", "原聲片段要不要另外做一版「翻譯配音」（網頁上可切換）", [
        ("true", "clip 有 translation 就多產 lesson.dub.mp3：原聲換成另一個聲音唸翻譯，講稿也換成翻譯（預設）"),
        ("false", "只做原聲版，檔案小一半、TTS 也快一點"),
    ]),
    "dub_voice": ("--dub-voice", "跟講解不同性別的同語言聲音", "唸原聲翻譯的語音", [
        ("zh-TW-YunJheNeural", "中文男聲（講解是女聲時的預設）"),
        ("zh-TW-HsiaoChenNeural", "中文女聲"),
        ("en-US-GuyNeural", "英文男聲"),
    ]),
    "rate": ("--rate", "+0%", "聽力版語速", [
        ("+0%", "原速（預設）"), ("+15%", "快一點，通勤聽適合"), ("-10%", "慢一點"),
    ]),
    "project_name": ("--project-name", "atlas-of-knowledge", "Cloudflare Pages 的專案名（決定網址）", []),
    "deploy": ("--deploy", "false", "整理完要不要直接部署", [
        ("false", "只整理 dist/，先看看內容（預設）"), ("true", "整理後用 wrangler 部署到 Cloudflare Pages"),
    ]),
    "max_height": ("config: download.max_height", "720", "下載影片的畫質上限（影響截圖清晰度與下載量）", []),
}

SKILL_PARAMS: dict[str, list[str]] = {
    "learn": ["shots", "vision", "narrate", "output_lang", "lang"],
    "learn-estimate": ["shots", "vision"],
    "learn-fetch": ["lang", "output_lang", "force"],
    "learn-segment": ["shots", "vision"],
    "learn-shot": ["force", "keep_video", "max_height"],
    "learn-analyze": ["vision", "force"],
    "learn-render": ["combined"],
    "learn-atlas": [],
    "learn-narrate": ["clips", "voice", "dub", "dub_voice", "rate", "force"],
    "learn-publish": ["project_name", "deploy"],
}


def _norm(v) -> str:
    return {True: "true", False: "false"}.get(v, str(v))


def effective(name: str, workspace: Path) -> str | None:
    """從 workspace/input.yaml 或 config 讀出目前生效的值（沒有就回 None）。"""
    if name == "max_height":
        return str(load_yaml(config_file("estimate.yaml"))["download"]["max_height"])
    p = workspace / "input.yaml"
    if not p.exists():
        return None
    data = load_yaml(p) or {}
    if name in ("lang", "output_lang"):
        v = data.get(name)
        return ",".join(v) if isinstance(v, list) else (_norm(v) if v is not None else None)
    vids = data.get("videos") or []
    vals = {_norm(v.get(name)) for v in vids if v.get(name) is not None}
    return vals.pop() if len(vals) == 1 else (" / ".join(sorted(vals)) if vals else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill", choices=list(SKILL_PARAMS))
    ap.add_argument("--set", action="append", default=[], metavar="k=v", help="使用者已指定的參數")
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    args = ap.parse_args(argv)

    given = dict(kv.split("=", 1) for kv in args.set if "=" in kv)
    names = SKILL_PARAMS[args.skill]
    if not names:
        print(f"/{args.skill} 沒有可調參數，直接執行。")
        return
    print(f"/{args.skill} 會用到的參數：")
    ask = []
    for n in names:
        flag, default, meaning, choices = PARAMS[n]
        cur = given.get(n) or effective(n, args.workspace)
        mark = "（你已指定）" if n in given else ("（沿用 input.yaml）" if cur else "（預設）")
        print(f"\n  {flag}  = {cur or default} {mark}")
        print(f"      {meaning}")
        for val, desc in choices:
            star = "→ " if (cur or default) == val else "  "
            print(f"      {star}{val:<6} {desc}")
        if n not in given:
            ask.append(n)
    if ask:
        print("\n以上是預設值。要調整哪一個？（不用調就說「用預設」）")
        print("可調：" + "、".join(PARAMS[n][0] for n in ask))


if __name__ == "__main__":
    main()
