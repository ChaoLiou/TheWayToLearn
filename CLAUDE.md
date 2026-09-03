# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用指令

```bash
uv sync                                   # 安裝依賴（Python 3.11+，yt-dlp 走 pip；ffmpeg 要另外 apt install）
uv run pytest -q                          # 全部測試
uv run pytest tests/test_validate.py -k forward   # 單一測試
uv run ruff check scripts tests           # lint
uv run scripts/estimate.py <url> ...      # 估時間成本，不下載
uv run scripts/fetch.py <url>             # 抓字幕 + meta
uv run scripts/screenshot.py <id>         # 下載 + ffmpeg 抽幀（讀 segments.json）
uv run scripts/validate.py <segments|analysis|overview> <file.json>
uv run scripts/render.py                  # 每支影片各自產 plan.html
uv run scripts/atlas.py --status          # 學習地圖：列新站與共同術語
uv run scripts/atlas.py                   # 驗證 atlas.json、產 workspace/atlas.html
```
測試不碰網路：`tests/fixtures/ws/` 是一組完整的 workspace 樣本，改 schema / template / validator 後跑 pytest 就能驗。

## 專案目標

使用者給一串 YouTube 連結 → 程式抓取 transcript 與重要時間點的截圖 → 產出一份「學習規劃」文件。
最終交付形式是一個 **skill**（給 AI agent 使用），加上 agent 執行該 skill 所需的全部程式。

## 產出文件的固定結構（順序不可變）

1. **前情提要 & Outline** — 看這支影片前需要的背景，以及影片大綱
2. **YouTuber 的思維推導** — 作者如何一步步推出結論
3. **逐段說明** — 依影片分段，每段包含：
   - 該段內容摘要（附時間戳、對應截圖）
   - AI 補充說明
   - **該段出現的術語** 就地解釋（不集中到文末的 glossary）
4. **總結**
5. **推薦三個下一步** — 三個方向，各附建議在 YouTube 搜尋的關鍵字

## 預定架構（pipeline）

```
URL 列表
  → estimate:   yt-dlp --dump-json 拿時長/檔案大小/字幕有無 → 分階段估時間、token、磁碟（不下載）
  → fetch:      取得影片 metadata + transcript（含時間戳）
  → segment:    把 transcript 切成有意義的段落，選出每段的關鍵時間點
  → screenshot: 依關鍵時間點擷取影格（需要 ffmpeg / yt-dlp 類工具）
  → analyze:    LLM 對每段做說明、抽術語、推導作者思路
  → render:     組合成上述固定結構的文件（HTML，內嵌 Mermaid，截圖以相對路徑引用）
```

## 輸出格式

- `plan.html`：單一 HTML 檔，Mermaid 走 CDN。固定產三張圖：
  - `flowchart LR` 推理鏈：每段一節點，邊上寫該段留給下一段的線索
  - `mindmap`：主題 → 各段 → 術語
  - `graph` 術語關聯圖：術語間的依賴/對比
- 每支影片開頭註明使用的 vision 模式（見下）

## 線性推進（核心規則）

AI 的逐段說明必須「線性推進」（thematic progression / linear progression）：上一段留下的線索是下一段的出發點，不可跳段、不可引用尚未出現的段落。
實作方式：
- analyze 階段逐段生成，prompt 只帶上一段的完整 analysis，不一次餵整份 transcript
- `analysis.json` 每段必填 `builds_on` / `reasoning` / `leads_to`；第 N 段的 `builds_on` 必須回應第 N-1 段的 `leads_to`
- validator 檢查 `builds_on` 只指向更早的 segment；render 把承接句以「承上：…」顯示

## vision 模式（每支影片各自設定）

`input.yaml` 每個 URL 有 `vision: true | false | auto`（**預設 true**），決定 analyze 階段 agent 是否逐張讀截圖。`auto` 由 agent 在 segment 階段判斷並寫回 `segments.json`。

## 學習地圖（Atlas）

workspace 下每個影片資料夾是一個 **waypoint**；`workspace/atlas.json` 記 **route**（兩站關聯：prerequisite / deepens / contrasts / applies / related，含 via）與 **region**（主題區）；`scripts/atlas.py` 產 `workspace/atlas.html`，各站 `plan.html` 頂部有回到地圖與相鄰站的連結。≥ 2 站時每新增一站由 agent 依 `rules/atlas.md` 更新 atlas.json。模板共用 `templates/_base.html.j2`（viewer、mermaid、tooltip）。

## 輸出語言

跟著使用者下指令的語言：`/learn` 判定後寫進 `input.yaml` 的 `output_lang` 與各站 `meta.json`；agent 產的所有內文用它，術語 `term` 永遠英文原文；HTML 介面文字由 `scripts/i18n.py` 依語言切換（新語言只需加一組字串）。

## 改規則不改程式

行為都外置，改對應檔案即可：
- 切段 / 截圖挑選 / vision auto 判斷 → `rules/segment.md`
- 線性推進與 AI 說明風格 → `rules/narrative.md`（硬規則由 `scripts/validate.py check_analysis` 執行，新增硬規則要同步加檢查 + 測試）
- 彙整、takeaways、三個下一步 → `rules/overview.md`
- 學習地圖的 route / region 判斷 → `rules/atlas.md`
- 文件版面 → `rules/output.md` + `templates/plan.html.j2`
- 估算係數 → `config/estimate.yaml`
- agent 輸出格式 → `schemas/*.json`

## Skill 拆分

`.claude/skills/` 下：`/learn` 總指揮 + 七個階段 skill：`/learn-estimate`、`/learn-fetch`、`/learn-segment`、`/learn-shot`、`/learn-analyze`、`/learn-render`、`/learn-atlas`。
`/learn` 第 0 步一定先跑 estimate 並把分階段 + 總和給使用者看。
共用慣例：`/learn-<stage> <video_id> [--force] [--vision ...]`；預設不覆蓋既有輸出。`/learn` 另有 `--from <stage>`、`--dry-run`。

誰做什麼：estimate / fetch / shot / render 是 `scripts/*.py`（確定性）；segment / analyze / overview 由 agent 依 `rules/*.md` 產 JSON，再過 `scripts/validate.py`。

設計原則：
- 每個階段的輸入/輸出落地成檔案（transcript JSON、segments JSON、截圖目錄），讓中間結果可重用、失敗可從中斷點重跑，不必重抓影片。
- 每支影片獨立資料夾、獨立 `plan.html` 與 `_overview.json`（預設不合併）；使用者明確要求時才用 `render.py --combined` 合併多支。
- skill 定義（給 agent 的指令）與程式碼分開放：skill 負責「何時、如何呼叫」，程式負責確定性的抓取/切段/截圖；LLM 判斷（分段語意、術語、說明）留在 analyze 階段。

## 常用指令

（尚無。加入 build / test / lint 指令後在此補上，含「跑單一測試」的方式。）
