---
name: learn-atlas
description: 學習地圖（Atlas）：把 workspace 下所有影片（waypoint）用 route 連起來、分成主題區（region），產出 workspace/atlas.html 可綜觀、可點進各站。有 ≥ 2 支影片時，每新增一支就跑一次。
---

# /learn-atlas

名詞：**waypoint** = 一支影片的資料夾、**route** = 兩站之間的關聯（有型態）、**region** = 主題區。規則在 `rules/atlas.md`（實際路徑看 `paths.py`，可能被 `./learn.rules/` 覆寫）。

## 步驟
1. `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/atlas.py --status`
   - 列出所有 waypoint、哪些是「★ 新站」、新站與每個既有站的**共同術語**與 prerequisites 覆蓋情況。
   - 若某站沒有 takeaways，先補該站的 `_overview.json`（`rules/overview.md`）並重跑 `/learn-render`。
2. 依 `rules/atlas.md` 更新 `workspace/atlas.json`（格式 `schemas/atlas.schema.json`）：
   - 只處理新站：決定它與既有各站的 route（型態 + via），以及它屬於哪個 region（可新建 region）。
   - 沒有關聯就不要硬連。
3. `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/atlas.py` → 驗證並產出 `workspace/atlas.html`。
4. 重跑 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/render.py`（不帶參數）讓每站的 `plan.html` 頂部「學習地圖」區塊更新為最新 route。
5. 回報：atlas.html 路徑、新站連到了哪些站、進了哪個 region。

## 只有一站時
不需要 atlas.json；`atlas.py` 仍可 render 出只有一張卡片的 atlas.html。
