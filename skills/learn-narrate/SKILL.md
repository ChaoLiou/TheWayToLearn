---
name: learn-narrate
description: [步驟 9/10·產出聽力版] 把 plan.html 的內容變成可以用聽的：TTS 口語講解與作者原聲片段交錯，產出 lesson.mp3 與章節。通勤、走路時學習用。
---

# /learn-narrate　—　步驟 8/8 產出聽力版

把 `analysis.json` 改寫成**寫給耳朵**的講稿，中間穿插作者的原聲片段，合成一份 `lesson.mp3`。

## 來源是部落格文章時
沒有原聲：`clip` 會用文章語言、跟講解不同的聲音逐句朗讀那幾段原文（`lesson.json` 的 `read_voice`），不下載任何音訊。講稿寫法見 `rules/narration.md` 最後一節。

## 開始前：確認參數

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-narrate [--set k=v ...]
```
把表原樣顯示，再用 AskUserQuestion 問一次要不要調整（第一個選項固定「用預設」）。使用者已指定的不要再問。

## 1. 挑原聲片段（agent，若 segments.json 還沒有 clips）
- 依 `rules/narration.md` 的「原聲片段」表：**預設整段**（≤150 秒直接用段落起訖；更長就取其中核心 60–120 秒）。
- 起訖秒數不必精算，`narrate.py` 會自動對齊 transcript 的句子邊界。
- 純過場、純清單的段落可以不放 clip。寫回 `segments.json` 後跑 `validate.py segments`。

## 2. 寫講稿（agent）
- 先整份讀 `rules/narration.md`（實際路徑看 `paths.py`）。
- 依 `analysis.json` 逐段寫，輸出 `workspace/<影片標題>/narration.json`（格式 `schemas/narration.schema.json`）。
- 節奏固定：引言 → 導聽 → 原聲 clip → 說明 → 術語（可選）→ 收束。開頭有總引言、結尾有總結與三個下一步。
- 每個 `say` block ≤ 60 字，語言用該站 `meta.output_lang`。

## 3. 合成（script）

被 `/learn` 呼叫時，步驟 6 render 之前應該已經跑過 `--mark-pending`；單獨執行這支 skill 時不需要，`narrate.py` 自己會標記狀態。
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/narrate.py <id> [--voice ...] [--rate +15%] [--dub-voice ...] [--no-dub] [--force]
```
- 需要網路（edge-tts）與 ffmpeg；會自動只下載音訊（`-f ba`，比影片小很多）。
- 產出 `lesson.mp3` 與 `lesson.json`（章節、時間軸、逐句字幕）。
- clip 有 `translation` 時另外產 `lesson.dub.mp3`：原聲片段換成另一個聲音唸翻譯（`--dub-voice`，預設是同語言不同性別），講解部分沿用同一份音檔。網頁上用「🎙 原聲 / 🗣 翻譯」切換，KTV 講稿跟著換，切換時停在同一個位置。不需要就加 `--no-dub`。舊站已經有 `lesson.mp3` 但還沒有翻譯版時，直接重跑就會補做（不必 `--force`，講解的 TTS 會重用快取）。
- 片段快取在 `lesson_parts/`：只改字幕合併或章節時會重用，不必重跑 TTS（`--no-cache` 可強制重做）。
- 之後重跑 `/learn-render`，`plan.html` 頂端會出現播放器、章節，以及「🎤 開啟講稿」的 karaoke 視窗。

## 進度
script 執行完會自己印 `[9/10] ✔ … ●●●●●●●●●○` 與下一步兩行，把它原樣回報給使用者，不要改寫。

## 產出後

`narrate.py` 跑完會自動重產 `workspace/listen.html`（podcast 頁，新的一集會排在最上面）；沒更新就手動跑 `scripts/listen.py`。
