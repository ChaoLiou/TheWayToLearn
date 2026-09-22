---
name: learn-atlas
description: [步驟 8/10·連結各站] 文字說明列表（atlas.html）：把 workspace 下所有影片（waypoint）用 route 連起來、分成主題區（region），產出 workspace/atlas.html——所有文字說明的列表，可搜尋、可點進各站、看相鄰站。有 ≥ 2 支影片時，每新增一支就跑一次。
---

# /learn-atlas　—　步驟 7/8 連結各站

名詞：**waypoint** = 一支影片的資料夾、**route** = 兩站之間的關聯（只有 `next` = 接著看、`related` = 相關無先後）、**region** = 主題區。規則在 `rules/atlas.md`（實際路徑看 `paths.py`，可能被 `./learn.rules/` 覆寫）。

## 開始前

這支沒有可調參數，直接執行（`options.py learn-atlas` 會這樣說）。

## 步驟
1. `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/atlas.py --status`
   - 列出所有 waypoint、哪些是「★ 新站」、新站與每個既有站的**共同術語**與 prerequisites 覆蓋情況。
   - 若某站沒有 takeaways，先補該站的 `_overview.json`（`rules/overview.md`）並重跑 `/learn-render`。
2. 依 `rules/atlas.md` 寫一份**只含新東西的 patch**（不要整份重寫 `atlas.json`），格式同 `schemas/atlas.schema.json` 的 `regions` / `routes`：
   - 只處理新站：決定它與既有各站的 route（型態 + via），以及它屬於哪個 region（可新建 region）。
   - region 只列新站的 id 就好，`--merge` 會併進既有成員；同一對站再給一次 route 會取代舊的。
   - 沒有關聯就不要硬連。
3. `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/atlas.py --merge <patch.json>`
   → 併進 `atlas.json`、驗證、產出 `workspace/atlas.html`（整段有檔案鎖，兩支影片同時跑也不會互相蓋掉 route；驗證沒過就不寫入）。
   - 要重整全部關係（改區、刪 route）才直接改 `atlas.json`，然後跑不帶參數的 `atlas.py` 驗證 + render。
4. 重跑 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/render.py`（不帶參數）讓每站的 `plan.html` 頂部「文字說明列表」區塊更新為最新 route。
5. 回報：atlas.html 路徑、新站連到了哪些站、進了哪個 region。

## 各站的 pipeline 進度（自動，不用做事）
atlas.html 每張卡片會顯示這一站走到十步的哪一步，以及「▸ 繼續做」按鈕（選一個目標 → 複製 prompt → 使用者自己貼到 Claude Code）。這些是 `atlas.py` 讀檔案自己判定的，跑一次 `atlas.py` 就會更新；某一站補完東西（例如補了原聲片段與翻譯）之後，記得再跑一次 `atlas.py` 讓進度跟著更新。

## 只有一站時
不需要 atlas.json；`atlas.py` 仍可 render 出只有一張卡片的 atlas.html。

## 跑完印進度
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/progress.py atlas "<一句話結果，例如 9 段>"
```
把它印出的兩行原樣回報給使用者。
