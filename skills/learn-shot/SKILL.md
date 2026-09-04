---
name: learn-shot
description: [步驟 4/7·截圖] 依 segments.json 的 shots 下載影片並用 ffmpeg 抽幀到 workspace/<影片標題>/frames/。改了時間點後重截時用。
---

# /learn-shot　—　步驟 4/7 截圖

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/screenshot.py <id> [--force] [--keep-video]
```

- 需要 `ffmpeg`（`sudo apt install ffmpeg`）。
- 影片只下載一次（≤ `config/estimate.yaml` 的 max_height），抽完預設刪除。
- 會把 `frames/sNN_<秒>.jpg` 路徑寫回 `segments.json` 的 `shots[].file`。
- segments 沒有任何 shots（`shots_mode: none` 或 agent 判斷都不值得截）時直接結束、不下載影片，並印出「跳過」的進度行。

## 進度
script 執行完會自己印 `[N/7] ✔ … 下一步 …` 兩行，把它原樣回報給使用者，不要改寫。
