# Atlas of Knowledge

給 YouTube 連結，產出一份**線性推進**的學習規劃（HTML + Mermaid），再把每支影片連成一張學習地圖。全部由你自己的 Claude Code 驅動：skill 負責判斷，Python script 負責抓取、截圖、驗證、排版。

## 需求

- [Claude Code](https://claude.com/claude-code)
- [uv](https://docs.astral.sh/uv/)（會自動裝 Python 依賴，含 yt-dlp）
- ffmpeg：`sudo apt install ffmpeg` / `brew install ffmpeg`

## 安裝

**方式 A：當 plugin 用（任何專案目錄都能用）**

在 Claude Code 裡：
```
/plugin marketplace add <本 repo 的 GitHub 位址或本機路徑>
/plugin install atlas-of-knowledge@thewaytolearn
```
或在終端機：`claude plugin marketplace add <位址>` 然後 `claude plugin install atlas-of-knowledge@thewaytolearn`。
之後在任何目錄：`/atlas-of-knowledge:learn https://youtu.be/...`。學習紀錄放在該目錄的 `./workspace/`（或設 `LEARN_WORKSPACE`）。

**方式 B：clone 下來在裡面用**
```
git clone <this-repo> && cd TheWayToLearn && uv sync
claude
```
`/learn https://youtu.be/...`

減少權限提示：在 `.claude/settings.json` 的 `permissions.allow` 加 `"Bash(uv run *)"`。

## 用法

| 指令 | 做什麼 |
|---|---|
| `/learn <url> [--vision true\|false\|auto]` | 估成本 → 抓字幕 → 切段 → 截圖 → 逐段分析 → 產 `plan.html` → 更新學習地圖 |
| `/learn-estimate <url>` | 只估時間／token／磁碟 |
| `/learn-render` | 已有資料，只重產 `plan.html` |
| `/learn-atlas` | 重整學習地圖 `workspace/atlas.html` |

## 客製規則（不用改程式）

plugin 更新會覆蓋 `rules/`、`config/`、`templates/`。要改，把檔案複製到目前目錄的 `./learn.rules/`（同名）再改，例如 `./learn.rules/narrative.md`、`./learn.rules/estimate.yaml`、`./learn.rules/templates/plan.html.j2`。`uv run scripts/paths.py` 會印出每個規則實際讀哪裡。

## 產出

```
workspace/<影片標題>/plan.html     # 五段固定結構：前情提要 → 作者推導 → 逐段（承上／推理／術語／勘誤／留給下一段）→ 總結 → 三個下一步
workspace/atlas.html               # 學習地圖：站、route、主題區
```
