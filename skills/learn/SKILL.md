---
name: learn
description: 使用者貼 YouTube 連結並要求學習、整理、做筆記、做學習規劃時使用。總指揮：先估時間成本，再依序跑 fetch → segment → shot → analyze → render 產出 plan.html。
---

# /learn — 總指揮（7 個步驟）

```
[1/8] estimate  估成本       [5/8] analyze  逐段分析
[2/8] fetch     抓字幕       [6/8] render   產出 plan.html
[3/8] segment   切段         [7/8] atlas    更新知識地圖（≥ 2 站才需要）
[4/8] shot      截圖         [8/8] narrate  產出聽力版（選配）
```
每個階段跑完都會印一行 `[N/8] ✔ … ●●●○○○○` 與下一步，**原樣轉給使用者**，讓他隨時知道走到哪。跳過的步驟也要說明（例如「[2/8] fetch 跳過：transcript.json 已存在」）。

用法：
```
/learn <url> [--shots auto|none|many] [--vision true|false|auto] <url> ...
       # 選項只影響前一個 URL；預設 shots=auto、vision=true
/learn input.yaml
/learn --from <stage> <id>        # 從某階段往後重跑：fetch|segment|shot|analyze|render
/learn --dry-run <url> ...        # 只列各階段會跳過/執行
```

## 開始前：確認參數

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn [--set k=v ...]
```
1. 使用者在指令裡已指定的參數用 `--set` 傳進去（例如 `--set shots=none`），它們會標成「你已指定」，**不要再問**。
2. 把 script 印出的表**原樣**給使用者看：每個參數的目前值、意義、可選值。
3. 用 AskUserQuestion 問一次「要用預設嗎？」：
   - 第一個選項固定是「用預設，直接開始（推薦）」。
   - 其餘選項是**這支 skill 實際可調且尚未指定**的參數，每個選項寫清楚改成什麼值、會有什麼差別（例如「不截圖 `--shots none`：快很多、省 token，適合畫面沒資訊的影片」）。
   - 使用者選了就照他的選擇跑；選「用預設」就直接進行。
4. 使用者這次已經在對話裡表達過偏好（例如「這支不用截圖」），視同已指定，不要重複問。
5. `/learn` 只在開頭問一次，涵蓋整條流程；後面各階段不要再問。

## 執行位置
- 以 plugin 安裝時 `${CLAUDE_PLUGIN_ROOT}` 指向 plugin 目錄；clone repo 使用時未設定，`${CLAUDE_PLUGIN_ROOT:-.}` 會落到目前目錄。所有指令都寫成 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}/scripts/<x>.py"`。
- workspace 在使用者目前目錄的 `./workspace/`（或 `$LEARN_WORKSPACE`）。
- **第 0 步之前先跑** `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}/scripts/paths.py"`：它印出每個規則檔實際在哪（使用者可用 `./learn.rules/` 覆寫），之後讀規則就讀它印的路徑。

## 流程（每步都用對應的階段 skill，不要自己重做它的工作）

**準備**（不算步驟）：
- 跑 `paths.py` 確認規則檔實際路徑。
- **判定輸出語言**：看使用者這次下指令用的語言——中文 → `zh-TW`，英文 → `en`（其他語言用 BCP-47 碼）。寫進 `workspace/input.yaml` 的 `output_lang`，`/learn-fetch` 時帶 `--output-lang`（存進該站 `meta.json`，之後所有階段與 HTML 介面都跟著它）。使用者明說要哪種語言就照他說的。
- 沒有 `input.yaml` 就依參數寫一份到 `workspace/input.yaml`（格式見 `input.example.yaml`）。

**選項**
- `--shots`：`auto`（預設，只截看了才懂的畫面）｜`none`（完全不截圖，也不下載影片，步驟 4 直接跳過）｜`many`（投影片型影片，每段至少一張）。使用者說「畫面沒什麼東西」「重點都在講的內容」「不用截圖」就用 `none`。
- `--vision`：AI 要不要逐張讀截圖，預設 `true`；`--shots none` 時自動失效。
- 兩者都寫進 `workspace/input.yaml` 該支影片底下，並由 `/learn-segment` 寫進 `segments.json` 的 `shots_mode` / `vision`。

**[1/8] estimate**：跑 `/learn-estimate`（帶上 `--shots` / `--vision`），把分階段 + 總和的表格原樣給使用者看。`--shots none` 會明顯降低時間與 token，值得在確認時指出。使用者未明說「直接跑」時，等確認再繼續。

**[2/8]–[5/8]**：每支影片依序 `/learn-fetch` → `/learn-segment` → `/learn-shot` → `/learn-analyze`。
- 每階段先看輸出檔是否已存在，存在就跳過（除非 `--force` 或 `--from` 指定要重做）；跳過也要說「[N/7] X 跳過：<檔案> 已存在」。
- agent 產的 JSON 一定要過 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/validate.py <kind> <file>`，不過就修到過。

**[6/8] render**：每支影片各自 `/learn-render`（每支一份 `plan.html`，在自己的資料夾）。使用者明確要合併時才用 `--combined`。

**[7/8] atlas**：workspace 下有 ≥ 2 支影片時跑 `/learn-atlas`，把新站連進知識地圖。只有一站就說「[7/8] atlas 跳過：只有一站」。

**[8/8] narrate（選配）**：只有使用者要求「用聽的」「通勤聽」「做成 podcast」時才跑 `/learn-narrate`；否則收尾時提一句「想用聽的可以跑 /atlas:learn-narrate」。

**收尾回報**：`plan.html` 路徑、每支影片 vision 模式、estimate vs 實際耗時（`timings.json`）、atlas 上的新 route。

## 規則檔（改行為就改這些，不改程式）
- `rules/segment.md`（實際路徑看 `paths.py`，可能被 `./learn.rules/` 覆寫）、`rules/narrative.md`、`rules/overview.md`、`rules/output.md`
- `config/estimate.yaml`（估算係數）
- `schemas/*.json`（agent 輸出格式）

## 工作目錄
```
workspace/<影片標題>/               # 一站（waypoint）
  estimate.json  transcript.json  meta.json  segments.json  frames/  analysis.json  timings.json
  _overview.json  plan.html        # 每支影片各自一份
workspace/atlas.json               # 站與站的 route、主題區（agent 維護）
workspace/atlas.html               # 學習地圖總覽
```
