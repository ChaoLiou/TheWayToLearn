# TheWayToLearn

[English](../README.md) · **繁體中文**

把一串 YouTube 連結變成一份有結構的學習規劃：逐字稿、關鍵時間點截圖、作者一步步的推理、就地解釋的術語，以及一張把你看過的所有影片串起來的學習地圖。

本專案以 [Claude Code](https://claude.com/claude-code) 的 skill 形式交付，並附上這些 skill 會呼叫的確定性程式。

---

## 為什麼做這個

看完一支技術影片，留下的往往只有「好像懂了」的感覺，沒有任何可以回頭翻的東西。手抄筆記會漏掉推理過程；自動摘要把論證壓成條列，把概念出場的順序也一併抹掉。

這個專案保留順序。每一段的說明都**線性推進**：第 N 段留下的線索就是第 N+1 段的出發點；術語在第一次出現的那一段就地定義；禁止引用尚未出現的段落。讀起來像影片本身在論證，而不是一份目錄。

## 你會得到什麼

每支影片在 `workspace/<影片標題>/` 下有一份獨立的 `plan.html`，固定五個部分：

1. **前情提要 & Outline** —— 看這支影片前需要的背景，以及影片大綱
2. **YouTuber 的思維推導** —— 作者如何一步步推出結論
3. **逐段說明** —— 每段包含：附時間戳與截圖的摘要、AI 補充說明、就地解釋的術語（hover 看翻譯，點 icon 看更多），以及有逐字引文佐證的**勘誤／過時**標記
4. **總結**
5. **推薦三個下一步** —— 三個方向，各附建議在 YouTube 搜尋的關鍵字

每份 `plan.html` 內嵌三張 Mermaid 圖：推理鏈流程圖、心智圖（主題 → 各段 → 術語）、術語關聯圖。

有兩支以上影片後，`workspace/atlas.html` 就是**學習地圖（Atlas）**：每支影片是一站（waypoint），站與站之間的 route 有型別（prerequisite / deepens / contrasts / applies / related），並依主題分成 region。每份 plan 頂部都能回到地圖、跳到相鄰站。

中間產物（`transcript.json`、`segments.json`、`frames/`、`analysis.json`、`timings.json`）都落地成檔案，任何階段都能重跑，不必重抓影片。

## 怎麼用

### 在 Claude Code 裡（設計上的主要用法）

用 Claude Code 開啟本 repo，貼連結：

```
/learn https://www.youtube.com/watch?v=XXXXXXXXXXX https://youtu.be/YYYYYYYYYYY
/learn input.yaml
```

第 0 步一定先印出分階段與總和的成本估算（時間、token、磁碟），等你確認。之後每支影片依序跑 fetch → segment → shot → analyze → render；有兩支以上影片時再更新學習地圖。

選項：

```
/learn <url> --vision true|false|auto   # agent 是否逐張讀截圖（預設 true）；只影響前一個 URL
/learn --from <stage> <video_id>        # 從某階段往後重跑：fetch | segment | shot | analyze | render
/learn --dry-run <url> ...              # 只列各階段會執行或跳過
```

每個階段也是獨立 skill（`/learn-estimate`、`/learn-fetch`、`/learn-segment`、`/learn-shot`、`/learn-analyze`、`/learn-render`、`/learn-atlas`），慣例是 `/learn-<stage> <video_id> [--force]`。既有輸出預設不覆蓋，要重做加 `--force`。

批次輸入（`input.example.yaml`）：

```yaml
lang: [zh-TW, zh, en]   # 字幕語言優先序
out: workspace
videos:
  - url: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    vision: true         # true | false | auto
  - url: https://youtu.be/xxxxxxxxxxx
    vision: false
```

### 直接跑程式

確定性的階段是純 Python，不需要 agent 也能用：

| 指令 | 做什麼 |
|---|---|
| `uv run scripts/estimate.py <url> ...` | 分階段估時間／token／磁碟，不下載。 |
| `uv run scripts/fetch.py <url>` | 抓字幕（含時間戳）與 metadata，不下載影片。 |
| `uv run scripts/screenshot.py <id>` | 下載影片一次、依 `segments.json` 用 ffmpeg 抽幀、抽完刪影片（`--keep-video` 保留）。 |
| `uv run scripts/validate.py <segments\|analysis\|overview> <file.json>` | 用 schema 與線性推進規則驗證 agent 產出的 JSON。 |
| `uv run scripts/render.py [ids...]` | 每支影片各自產 `plan.html`；`--combined` 合併成一份。 |
| `uv run scripts/atlas.py --status` / `uv run scripts/atlas.py` | 列新站與共同術語／驗證 `atlas.json` 並產 `atlas.html`。 |

segment、analyze、overview 三個階段需要 LLM，由 agent 依 `rules/*.md` 執行。

## 依賴

| 依賴 | 用途 | 怎麼裝 |
|---|---|---|
| Python ≥ 3.11 | 程式 | 見下方 |
| [uv](https://docs.astral.sh/uv/) | 依賴與 venv 管理 | 見下方 |
| yt-dlp | 字幕、metadata、下載影片 | Python 套件，`uv sync` 會裝 |
| ffmpeg | 抽幀 | **系統套件，要另外裝** |
| Claude Code | 執行 `/learn-*` skill | [安裝說明](https://docs.claude.com/en/docs/claude-code) |

Python 套件（`pyproject.toml`）：`yt-dlp`、`pyyaml`、`jinja2`、`jsonschema`；開發用：`pytest`、`ruff`。

## 環境安裝

開發與測試環境是 WSL2（Ubuntu）。原生 macOS 與 Windows 應可運作；唯一跟作業系統有關的是把 `ffmpeg` 放進 `PATH`。

### Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # uv（需要時會自動裝 Python）
sudo apt install ffmpeg                             # Debian / Ubuntu
# sudo dnf install ffmpeg                           # Fedora（需啟用 RPM Fusion）
git clone <本 repo> && cd TheWayToLearn
uv sync
```

### macOS

```bash
brew install uv ffmpeg
git clone <本 repo> && cd TheWayToLearn
uv sync
```

### Windows

方法 A —— WSL2（建議，與測試環境相同）：從 Microsoft Store 裝 Ubuntu，然後在裡面照 Linux 步驟做。

方法 B —— 原生 PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
winget install Gyan.FFmpeg        # 或：choco install ffmpeg
# 開一個新的終端機讓 PATH 生效
git clone <本 repo>; cd TheWayToLearn
uv sync
```

### 確認可用

```bash
uv run yt-dlp --version
ffmpeg -version
uv run pytest -q          # 不碰網路；用 tests/fixtures/ws 當樣本 workspace
uv run scripts/estimate.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

最後一個指令印出分階段表格就代表環境 OK。

## 改行為不改程式

| 想改… | 改哪裡 |
|---|---|
| 切段、截圖挑選、`vision: auto` 判斷 | `rules/segment.md` |
| 線性推進規則與說明風格 | `rules/narrative.md`（硬規則由 `scripts/validate.py` 執行；新增硬規則要同步加檢查與測試） |
| 彙整、takeaways、三個下一步 | `rules/overview.md` |
| 學習地圖的 route / region 判斷 | `rules/atlas.md` |
| 文件版面 | `rules/output.md` + `templates/plan.html.j2` |
| 估算係數 | `config/estimate.yaml` |
| agent 輸出格式 | `schemas/*.json` |

## 開發

```bash
uv run pytest -q                         # 全部測試，不碰網路
uv run pytest tests/test_validate.py -k forward
uv run ruff check scripts tests
```

## 翻譯

英文版 `README.md` 是原始版本，其他語言放在 `docs/README.<lang>.md`，`<lang>` 用 [BCP 47](https://en.wikipedia.org/wiki/IETF_language_tag) 標籤；每個版本頂部都有同一列語言切換連結。

新增語言：把 `README.md` 複製成 `docs/README.<lang>.md` 翻譯，然後在**每一份** README 的語言列加上連結（包含這一份）。

| 語言 | 檔案 |
|---|---|
| English（原始版本） | `README.md` |
| 繁體中文 | `docs/README.zh-TW.md` |
