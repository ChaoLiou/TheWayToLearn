---
name: learn-render
description: [步驟 7/10·產出 plan.html] 已有 analysis.json 時，產生該影片的 _overview.json 並組成 plan.html（HTML + Mermaid）。只想重新產學習規劃、不重抓資源時用。
---

# /learn-render　—　步驟 6/8 產出 plan.html

**語言**：所有內文用該站 `meta.json` 的 `output_lang`（術語原文保留英文）。

預設**每支影片各自一份**：`workspace/<影片標題>/plan.html`，`_overview.json` 也放在該資料夾。

## 開始前：確認參數

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-render [--set k=v ...]
```
1. 使用者在指令裡已指定的參數用 `--set` 傳進去（例如 `--set shots=none`），它們會標成「你已指定」，**不要再問**。
2. 把 script 印出的表**原樣**給使用者看：每個參數的目前值、意義、可選值。
3. 用 AskUserQuestion 問一次「要用預設嗎？」：
   - 第一個選項固定是「用預設，直接開始（推薦）」。
   - 其餘選項是**這支 skill 實際可調且尚未指定**的參數，每個選項寫清楚改成什麼值、會有什麼差別（例如「不截圖 `--shots none`：快很多、省 token，適合畫面沒資訊的影片」）。
   - 使用者選了就照他的選擇跑；選「用預設」就直接進行。
4. 使用者這次已經在對話裡表達過偏好（例如「這支不用截圖」），視同已指定，不要重複問。

## 1. 彙整（agent 做，每支影片各做一次）
- 讀 `rules/overview.md`（實際路徑看 `paths.py`，可能被 `./learn.rules/` 覆寫）。
- 讀該影片的 `analysis.json` 與 `meta.json`。
- 寫 `workspace/<影片標題>/_overview.json`（格式 `schemas/overview.schema.json`）：topic、prerequisites、outline（一支影片就一條）、summary、**固定三個** next_steps。
- `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/validate.py overview "workspace/<影片標題>/_overview.json"`。
- `--only-plan`：`_overview.json` 已存在就跳過這步。

## 2. 組 HTML（script）
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/render.py <id|url>           # 指定影片
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/render.py                    # workspace 下全部，各自 render
```
- 版面在 `templates/plan.html.j2`，段落順序規則在 `rules/output.md`。
- Mermaid 三張圖由 script 從 analysis 自動產生，不用 agent 畫。
- 回報 `plan.html` 的絕對路徑；用瀏覽器開（Mermaid 走 CDN，需要網路）。

## 合併多支（使用者明確要求時才用）
- agent 讀所有影片的 analysis，寫 `workspace/_overview.json`（outline 決定順序）。
- `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/render.py --combined [--out workspace/plan.html] <id> <id> ...`

## 進度
script 執行完會自己印 `[N/10] ✔ … 下一步 …` 兩行，把它原樣回報給使用者，不要改寫。
