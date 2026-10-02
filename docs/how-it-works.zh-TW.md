# 底層怎麼做的（技術版）

**繁體中文** · [English](how-it-works.md)

> 這份是給想知道內部怎麼跑的人。只想用的話看 [README](README.zh-TW.md)（[English](../README.md)）就夠了。

**一條把長影片變成可導覽文字成品的管線（pipeline）。** 給一支 YouTube 連結，它取源、切段、抽幀、逐段分析，產出線性推進的解析頁（plan.html），再把每支影片連成一份可搜尋的影片解析列表（atlas.html）；要用聽的，它會把 TTS 講解與作者原聲合成一軌。由 agent 驅動：**skill 只負責判斷，Python script 負責抓取、截圖、合軌、驗證與排版。**

---

## 管線

```mermaid
flowchart LR
  S["來源<br/>YouTube / 部落格文章"] --> E1["① estimate<br/>先估時間·token·磁碟"]
  E1 --> F2["② fetch<br/>字幕 + metadata<br/>（含時間戳）"]
  F2 --> G3["③ segment<br/>切意義段落<br/>挑截圖時間點"]
  G3 --> H4["④ shot<br/>依時間點抽幀"]
  H4 --> I5["⑤ analyze<br/>逐段分析"]
  I5 --> J6["⑥ render<br/>plan.html"]
  J6 --> K7["⑦ narrate / listen<br/>TTS × 原聲合軌"]
  J6 --> L8["⑧ atlas / notes<br/>跨影片索引"]
  J6 --> M9["⑨ publish<br/>Cloudflare Pages"]
```

### 每一階段誰做什麼

| # | 階段 | 判斷（skill） | 執行（script） | 產出 |
|---|---|---|---|---|
| ① | `estimate` | — | `estimate.py` ＋ `config/estimate.yaml` | 分階段的時間／token／磁碟預估，**跑之前就知道代價** |
| ② | `fetch` | 選字幕語言、判斷來源型別 | `fetch.py`（`yt-dlp`）、`blog.py` | `transcript.json`（逐句＋時間戳）、`meta.json`（章節） |
| ③ | `segment` | **切成意義段落、挑出值得截圖的時間點、決定要不要用 vision** | `validate.py` 驗結果 | `segments.json` |
| ④ | `shot` | — | `screenshot.py`（`yt-dlp` 下載一次 ＋ `ffmpeg -ss` 逐點抽幀） | `frames/s03_292.jpg`（檔名＝段號＋秒數） |
| ⑤ | `analyze` | **逐段寫承上／推理／術語／勘誤／留給下一段**（線性推進硬規則） | `validate.py` 驗 schema ＋ 規則 | `analysis.json` |
| ⑥ | `render` | 概覽與排序 | `render.py`（Jinja2 ＋ `templates/`） | `plan.html`：五段固定結構，每段掛回時間碼 |
| ⑦ | `narrate` / `listen` | 寫口語講稿、挑原聲片段 | `narrate.py`（edge-tts ＋ `ffmpeg` 切段、統一取樣率、concat）、`listen.py` | `lesson.mp3`（講解×原聲交錯）、`lesson.dub.mp3`（原聲換配音）、`listen.html`（podcast 頁、karaoke 講稿） |
| ⑧ | `atlas` / `notes` / `digest` / `canvas` | 連站、分主題、標記 PACER、挑要畫的概念 | `atlas.py`、`notes.py`、`digest.py` | `atlas.html`（各站／相鄰站／主題區，可搜尋）、`notes.html`、`digest.html`、tldraw 畫布 |
| ⑨ | `publish` | — | `publish.py` | `dist/`，可直接部署到 Cloudflare Pages |

---

## 工程上的幾個決定

**1. 時間碼（timecode）是唯一的黏著劑。** 字幕、段落、截圖檔名、分析段落、語音章節、karaoke 高亮全部掛在同一條時間軸上，任何一段成品都能點回原始素材的那一秒。索引做不到回溯，使用者就不會信它。

**2. 合出來的音檔刻意用固定位元率（CBR 48k）。** TTS 講解與 `ffmpeg` 切出的原聲先統一成同一個取樣率（24 kHz／mono）才 concat；位元率固定是因為**時間與位元組必須是線性關係，瀏覽器 seek 才精準**——用 VBR 的話落點會差一兩秒，karaoke 高亮就跟原聲對不上。

**3. 執行前先估成本。** 下載頻寬、截圖上限、每段的輸入／輸出 token 都寫在 `config/estimate.yaml`，改係數不用動程式。長影片先看估算再決定要不要跑 vision。

**4. agent 的產出一律過兩道驗證。** `schemas/*.json` 擋結構，`validate.py` 擋語意硬規則（例如「不准前向參照後面的段落」、一站的概念節點上限）。沒過不進下一階段。

**5. 規則可覆寫，不必改程式。** `rules/`、`config/`、`templates/` 可以複製到專案裡的 `./learn.rules/` 再改；`pacer paths` 會印出每個規則實際讀哪一份。更新不會蓋掉你的客製。

**6. 每個階段都是獨立 CLI。** `pacer <stage>` 可以單獨跑、單獨重跑；`pacer prune` 回收「重跑就會再有」的中間檔。

---

## 產出

```
workspace/<影片標題>/plan.html    # 五段固定結構：前情提要 → 作者推導 → 逐段 → 總結 → 三個下一步
workspace/<影片標題>/lesson.mp3   # 語音版（講解 × 原聲交錯），lesson.json 是章節時間軸
workspace/atlas.html              # 影片解析列表：各站、相鄰站（route）、主題區，可搜尋
workspace/listen.html             # podcast 頁：置底播放器、karaoke 講稿、記住聽到哪裡
workspace/notes.html              # 成長筆記：每條連回 plan.html 的那一段
workspace/brain/                  # Obsidian vault（`pacer brain`）：一站一檔、一概念一檔、[[wikilink]] 互連
dist/                             # publish 後的靜態站
```

---

## 需求

- 一個 coding agent：[Claude Code](https://claude.com/claude-code)，或任何讀 `SKILL.md` 的 agent（Cursor、Codex、Gemini CLI、OpenCode、Copilot…）
- [uv](https://docs.astral.sh/uv/)（自動裝 Python 依賴，含 `yt-dlp`）
- `ffmpeg`：`sudo apt install ffmpeg` / `brew install ffmpeg`
- 語音版另需網路（edge-tts，免費免金鑰）

## 安裝

**當 Claude Code plugin 用（任何專案目錄都能跑）**

```
/plugin marketplace add https://github.com/TheWayToLearn/PACER-Learn
/plugin install pacer@thewaytolearn
```

之後在任何目錄：`/pacer:learn https://youtu.be/...`。學習紀錄放在該目錄的 `./workspace/`（或設 `LEARN_WORKSPACE`）。

**裝進其他 agent**

```bash
npx skills add TheWayToLearn/PACER-Learn                           # 14 份 SKILL.md
uv tool install git+https://github.com/TheWayToLearn/PACER-Learn   # skill 裡呼叫的 `pacer` 指令
```

`npx skills add` 只把說明檔搬到那家 agent 放 skill 的位置，所以第二行才是把程式帶過去。裝完用 `pacer paths` 確認；`uvx --from git+https://github.com/TheWayToLearn/PACER-Learn pacer paths` 可以不安裝跑一次。

**clone 下來用**

```
git clone https://github.com/TheWayToLearn/PACER-Learn && cd PACER-Learn && uv sync
uv tool install -e .     # 讓 `pacer …` 指到這份工作目錄
claude
```

然後 `/learn https://youtu.be/...`。想少一點權限提示：在 `.claude/settings.json` 的 `permissions.allow` 加 `"Bash(pacer *)"`。

## 指令

| 指令 | 做什麼 |
|---|---|
| `/learn <url> [--shots auto\|none\|many] [--vision true\|false\|auto]` | 跑完整條管線：① → ⑨ |
| `/learn-estimate <url>` | 只估時間／token／磁碟 |
| `/learn-fetch` `/learn-segment` `/learn-shot` `/learn-analyze` | 單階段重跑（換字幕語言、重切段、改截圖點、換 vision 模式） |
| `/learn-render` | 只重產 `plan.html` |
| `/learn-narrate` `/learn-listen` | 產語音版、重整 podcast 頁 |
| `/learn-atlas` `/learn-notes` `/learn-digest` `/learn-canvas` | 影片解析列表、筆記、PACER 練習、tldraw 畫布 |
| `/learn-publish` | 整理 `dist/` 並部署到 Cloudflare Pages |

Claude Code 的 plugin 模式會在前面加 `/pacer:`。

## 開發

```
uv run pytest -q    # 183 passed
pacer paths         # 印出每個規則／範本實際讀哪一份
pacer prune         # 列出可回收的中間檔（加 --delete 才真的刪）
```

14 個 skill 在 `skills/`，對應的執行腳本在 `scripts/`，`pacer <名稱>` 可以單獨跑任何一支（dispatcher 是 `scripts/cli.py`，`tests/test_cli.py` 會在 script 與 SKILL.md 走鐘時擋下來）；agent 產出的結構定義在 `schemas/`，語意硬規則在 `rules/`。
