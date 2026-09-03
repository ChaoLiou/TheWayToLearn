---
name: learn-render
description: 已有 analysis.json 時，產生該影片的 _overview.json 並組成 plan.html（HTML + Mermaid）。只想重新產學習規劃、不重抓資源時用。
---

# /learn-render

預設**每支影片各自一份**：`workspace/<影片標題>/plan.html`，`_overview.json` 也放在該資料夾。

## 1. 彙整（agent 做，每支影片各做一次）
- 讀 `rules/overview.md`。
- 讀該影片的 `analysis.json` 與 `meta.json`。
- 寫 `workspace/<影片標題>/_overview.json`（格式 `schemas/overview.schema.json`）：topic、prerequisites、outline（一支影片就一條）、summary、**固定三個** next_steps。
- `uv run scripts/validate.py overview "workspace/<影片標題>/_overview.json"`。
- `--only-plan`：`_overview.json` 已存在就跳過這步。

## 2. 組 HTML（script）
```
uv run scripts/render.py <id|url>           # 指定影片
uv run scripts/render.py                    # workspace 下全部，各自 render
```
- 版面在 `templates/plan.html.j2`，段落順序規則在 `rules/output.md`。
- Mermaid 三張圖由 script 從 analysis 自動產生，不用 agent 畫。
- 回報 `plan.html` 的絕對路徑；用瀏覽器開（Mermaid 走 CDN，需要網路）。

## 合併多支（使用者明確要求時才用）
- agent 讀所有影片的 analysis，寫 `workspace/_overview.json`（outline 決定順序）。
- `uv run scripts/render.py --combined [--out workspace/plan.html] <id> <id> ...`
