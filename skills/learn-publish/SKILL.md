---
name: learn-publish
description: [工具] 把 workspace 裡的 atlas.html（全部影片，當首頁）、listen.html、notes.html、digest.html、各站 plan.html、截圖與語音解析整理成 dist/，可直接部署到 Cloudflare Pages，讓你在手機或其他電腦隨時看。
---

# /learn-publish　—　發佈到雲端（工具，不在 10 步流程內）

## 開始前：確認參數
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-publish [--set k=v ...]
```
把表原樣顯示，再問一次要不要調整。使用者已指定的不要再問。

## 1. 整理
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/publish.py
```
只複製 `atlas.html`（另存一份 `index.html` 當首頁；沒有 atlas.html 就依序退到 listen / digest / notes）、`listen.html`、`notes.html`、各站 `plan.html`、`frames/`、`lesson.mp3`、`lesson.dub.mp3`、`captions.js`。
不複製原始音訊 `audio.mp3`、TTS 快取 `lesson_parts/` 與各種 json（內容已內嵌在 html）。
把印出的檔案清單與大小原樣給使用者看。

### 混合式（mp3 分開放，建議站數多或影片長時用）
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/publish.py --media-base https://<你的 bucket 公開網址>/learn
```
`dist/` 只留 HTML 與 captions.js（上 Pages），`dist-media/` 放兩條 mp3 與 `frames/` 截圖（上 R2 / B2 / S3），HTML 裡的路徑自動改寫成絕對網址。
好處：Pages 每次部署只傳幾十 MB 而不是 1 GB，而且 object storage 沒有單檔上限（避開 25 MiB）。
媒體檔要另外同步，script 跑完會把指令印出來（`rclone sync dist-media r2:<bucket>/`）。

**走 R2 且要保持私密**時改成站內路徑 + worker：
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/publish.py --media-base /media --r2-binding MEDIA
```
會多產一份 `dist/_worker.js`：`/media/…` 讀 R2、其餘走靜態檔，所以 HTML 與 mp3 同一個 origin，Access 一設兩者都保護到。binding 要先在 `wrangler.toml` 宣告。
bucket 要**開公開讀取**且**支援 Range 請求**，不然進度條拖不動。

## 2. 部署（使用者同意才做）
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/publish.py --deploy --project-name <名稱>
```
- 首次要先 `npm i -g wrangler && wrangler login`（互動式登入，請使用者自己在終端機跑）。
- 部署完把網址給使用者，並提醒：**原聲片段是他人著作，建議到 Cloudflare Zero Trust → Access 設定只有自己的 email 能登入**，不要公開。
- 單檔超過 25 MB 會被擋下（Cloudflare Pages 限制），解法依序試：`--media-base` 把 mp3 分出去（最省事，直接沒有這個限制）、降低 `narrate.py` 的音訊位元率、該支影片改用 `--set clips=精華`。

## 之後更新
重跑同樣的指令即可，網址不變。

## 順手回收本機的中間檔（使用者要求時才做）
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/prune.py            # 只列出可回收什麼、多少
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/prune.py --delete   # 真的刪
```
清掉 `audio.mp3`、`subs.*.json3`、`.tmp-*`（重跑 yt-dlp 就有）與 `lesson_parts/`（TTS 快取，`--keep-cache` 可留）。
LLM 產出與成品一律不動。**一定先跑不帶 `--delete` 的版本、把清單與總量給使用者看、他同意才刪。**
