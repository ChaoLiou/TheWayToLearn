---
name: learn-narrate
description: [步驟 8/8·產出聽力版·選配] 把 plan.html 的內容變成可以用聽的：TTS 口語講解與作者原聲片段交錯，產出 lesson.mp3 與章節。通勤、走路時學習用。
---

# /learn-narrate　—　步驟 8/8 產出聽力版（選配）

把 `analysis.json` 改寫成**寫給耳朵**的講稿，中間穿插作者的原聲片段，合成一份 `lesson.mp3`。

## 開始前：確認參數

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-narrate [--set k=v ...]
```
把表原樣顯示，再用 AskUserQuestion 問一次要不要調整（第一個選項固定「用預設」）。使用者已指定的不要再問。

## 1. 挑原聲片段（agent，若 segments.json 還沒有 clips）
- 讀 `transcript.json`，為值得原音重現的段落加 `clips`：`{start, end, why}`，每段 0–1 個、長度 10–40 秒。
- 只挑「原話比轉述更有價值」的：作者的比喻、關鍵定義、語氣強調、實際數字。
- 寫回 `segments.json` 後跑 `validate.py segments`。

## 2. 寫講稿（agent）
- 先整份讀 `rules/narration.md`（實際路徑看 `paths.py`）。
- 依 `analysis.json` 逐段寫，輸出 `workspace/<影片標題>/narration.json`（格式 `schemas/narration.schema.json`）。
- 節奏固定：引言 → 導聽 → 原聲 clip → 說明 → 術語（可選）→ 收束。開頭有總引言、結尾有總結與三個下一步。
- 每個 `say` block ≤ 60 字，語言用該站 `meta.output_lang`。

## 3. 合成（script）
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/narrate.py <id> [--voice ...] [--rate +15%] [--force]
```
- 需要網路（edge-tts）與 ffmpeg；會自動只下載音訊（`-f ba`，比影片小很多）。
- 產出 `lesson.mp3` 與 `lesson.json`（章節與時間軸）。
- 之後重跑 `/learn-render`，`plan.html` 頂端就會出現播放器與可點的章節。

## 進度
script 執行完會自己印 `[8/8] ✔ … ●●●●●●●●` 兩行，把它原樣回報給使用者，不要改寫。
