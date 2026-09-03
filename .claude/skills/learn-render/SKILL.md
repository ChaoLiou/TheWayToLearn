---
name: learn-render
description: 已有 analysis.json 時，產生跨影片彙整 _overview.json 並組成 plan.html（HTML + Mermaid）。只想重新產學習規劃、不重抓資源時用。
---

# /learn-render

兩步：

## 1. 跨影片彙整（agent 做）
- 讀 `rules/overview.md`。
- 讀所有 `workspace/*/analysis.json` 與 `meta.json`。
- 寫 `workspace/_overview.json`（格式 `schemas/overview.schema.json`）：topic、prerequisites、outline（決定影片順序）、summary、**固定三個** next_steps。
- `uv run scripts/validate.py overview workspace/_overview.json`。
- 只有一支影片也要做這步（prerequisites 與 next_steps 是它產的）。
- `--only-plan`：`_overview.json` 已存在就跳過這步。

## 2. 組 HTML（script）
```
uv run scripts/render.py [--workspace workspace] [--out workspace/plan.html] [--ids a,b]
```
- 版面在 `templates/plan.html.j2`，段落順序規則在 `rules/output.md`。
- Mermaid 三張圖由 script 從 analysis 自動產生，不用 agent 畫。
- 回報 `plan.html` 的絕對路徑；用瀏覽器開（Mermaid 走 CDN，需要網路）。
