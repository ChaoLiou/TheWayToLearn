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

## 開始前：確認參數

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-shot [--set k=v ...]
```
1. 使用者在指令裡已指定的參數用 `--set` 傳進去（例如 `--set shots=none`），它們會標成「你已指定」，**不要再問**。
2. 把 script 印出的表**原樣**給使用者看：每個參數的目前值、意義、可選值。
3. 用 AskUserQuestion 問一次「要用預設嗎？」：
   - 第一個選項固定是「用預設，直接開始（推薦）」。
   - 其餘選項是**這支 skill 實際可調且尚未指定**的參數，每個選項寫清楚改成什麼值、會有什麼差別（例如「不截圖 `--shots none`：快很多、省 token，適合畫面沒資訊的影片」）。
   - 使用者選了就照他的選擇跑；選「用預設」就直接進行。
4. 使用者這次已經在對話裡表達過偏好（例如「這支不用截圖」），視同已指定，不要重複問。

## 進度
script 執行完會自己印 `[N/7] ✔ … 下一步 …` 兩行，把它原樣回報給使用者，不要改寫。
