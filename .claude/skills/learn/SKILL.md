---
name: learn
description: 使用者貼 YouTube 連結並要求學習、整理、做筆記、做學習規劃時使用。總指揮：先估時間成本，再依序跑 fetch → segment → shot → analyze → render 產出 plan.html。
---

# /learn — 總指揮

用法：
```
/learn <url> [--vision true|false|auto] <url> ...   # 選項只影響前一個 URL；預設 vision=true
/learn input.yaml
/learn --from <stage> <id>        # 從某階段往後重跑：fetch|segment|shot|analyze|render
/learn --dry-run <url> ...        # 只列各階段會跳過/執行
```

## 流程（每步都用對應的階段 skill，不要自己重做它的工作）

0. **估算**：先跑 `/learn-estimate`，把分階段 + 總和的表格原樣給使用者看。使用者未明說「直接跑」時，等確認再繼續。
1. 沒有 `input.yaml` 就依參數寫一份到 `workspace/input.yaml`（格式見 `input.example.yaml`）。
2. 對每支影片依序：`/learn-fetch` → `/learn-segment` → `/learn-shot` → `/learn-analyze`。
   - 每階段先看輸出檔是否已存在，存在就跳過（除非 `--force` 或 `--from` 指定要重做）。
   - agent 產的 JSON 一定要過 `uv run scripts/validate.py <kind> <file>`，不過就修到過。
3. 每支影片各自 `/learn-render`（每支一份 `plan.html`，在自己的資料夾）。使用者明確要合併時才用 `--combined`。
4. 回報：`plan.html` 路徑、每支影片 vision 模式、estimate vs 實際耗時（`timings.json`）。

## 規則檔（改行為就改這些，不改程式）
- `rules/segment.md`、`rules/narrative.md`、`rules/overview.md`、`rules/output.md`
- `config/estimate.yaml`（估算係數）
- `schemas/*.json`（agent 輸出格式）

## 工作目錄
```
workspace/<影片標題>/
  estimate.json  transcript.json  meta.json  segments.json  frames/  analysis.json  timings.json
  _overview.json  plan.html        # 每支影片各自一份
```
