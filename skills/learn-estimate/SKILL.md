---
name: learn-estimate
description: [步驟 1/10·估成本] 只給 YouTube 連結或部落格網址就估「下載、分析各階段時間、token、磁碟」，分階段列出並加總，不下載影片。/learn 的第一步，也可單獨用。
---

# /learn-estimate　—　步驟 1/8 估成本

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/estimate.py <url> [<url> ...] [--shots auto|none|many] [--vision true|false|auto]
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/estimate.py --input input.yaml
```

- 把 script 印出的表格**原樣**貼給使用者（每支影片分階段 + 小計；最後全部總和 + 跨影片彙整）。
- 表格後面有一行「消化積欠：…（共 N，上限 M）」，也原樣貼。N > M 時 script 會多印一行 ⚠：這是 PACER 的平衡閥——沒消化的東西會忘掉九成，建議先 `/learn-digest do due`；使用者堅持才往下（`/learn --force`）。
- `--shots none` 時不計截圖與影片下載，analyze 也不含讀圖成本；表頭會顯示 `shots=none`。
- `vision=auto` 時以 false 估，並另列「若 true 再加多少」，讓使用者決定。
- 出現「沒有任何字幕」的警告要特別指出，那支影片目前跑不了。
- **部落格網址**（非 YouTube）：抓一次頁面算閱讀時間與圖片數，表頭顯示「文章，閱讀約 …」；截圖上限套用在文中圖片數上，沒有影片下載量。
- 係數在 `config/estimate.yaml`；使用者覺得估得不準就改係數，不改程式。
- 結果寫在 `workspace/<影片標題>/estimate.json`，render 會拿來跟實際耗時對照。

## 開始前：確認參數

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-estimate [--set k=v ...]
```
1. 使用者在指令裡已指定的參數用 `--set` 傳進去（例如 `--set shots=none`），它們會標成「你已指定」，**不要再問**。
2. 把 script 印出的表**原樣**給使用者看：每個參數的目前值、意義、可選值。
3. 用 AskUserQuestion 問一次「要用預設嗎？」：
   - 第一個選項固定是「用預設，直接開始（推薦）」。
   - 其餘選項是**這支 skill 實際可調且尚未指定**的參數，每個選項寫清楚改成什麼值、會有什麼差別（例如「不截圖 `--shots none`：快很多、省 token，適合畫面沒資訊的影片」）。
   - 使用者選了就照他的選擇跑；選「用預設」就直接進行。
4. 使用者這次已經在對話裡表達過偏好（例如「這支不用截圖」），視同已指定，不要重複問。

## 進度
script 執行完會自己印 `[N/10] ✔ … 下一步 …` 兩行，把它原樣回報給使用者，不要改寫。
