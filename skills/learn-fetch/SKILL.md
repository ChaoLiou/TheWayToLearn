---
name: learn-fetch
description: [步驟 2/8·抓字幕] 抓 YouTube transcript（含時間戳）與 metadata 到 workspace/<影片標題>/，不下載影片。重抓資源、換字幕語言時用。
---

# /learn-fetch　—　步驟 2/8 抓字幕

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/fetch.py <url|id> [--lang zh-TW,zh,en] [--output-lang zh-TW|en] [--force]
```

- 輸出 `transcript.json`（events: start/duration/text）、`meta.json`（title/channel/duration/chapters/transcript_lang）。
- `--output-lang`：產出文件的語言，跟使用者對話語言一致（/learn 會決定）；存進 `meta.json` 的 `output_lang`。
- 已存在就跳過，`--force` 才重抓。
- 失敗常見原因：沒字幕（`yt-dlp --list-subs <url>` 看有哪些語言）、IP 被擋（換網路或加 `--cookies-from-browser`，需改 script）。

## 開始前：確認參數

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-fetch [--set k=v ...]
```
1. 使用者在指令裡已指定的參數用 `--set` 傳進去（例如 `--set shots=none`），它們會標成「你已指定」，**不要再問**。
2. 把 script 印出的表**原樣**給使用者看：每個參數的目前值、意義、可選值。
3. 用 AskUserQuestion 問一次「要用預設嗎？」：
   - 第一個選項固定是「用預設，直接開始（推薦）」。
   - 其餘選項是**這支 skill 實際可調且尚未指定**的參數，每個選項寫清楚改成什麼值、會有什麼差別（例如「不截圖 `--shots none`：快很多、省 token，適合畫面沒資訊的影片」）。
   - 使用者選了就照他的選擇跑；選「用預設」就直接進行。
4. 使用者這次已經在對話裡表達過偏好（例如「這支不用截圖」），視同已指定，不要重複問。

## 進度
script 執行完會自己印 `[N/8] ✔ … 下一步 …` 兩行，把它原樣回報給使用者，不要改寫。
