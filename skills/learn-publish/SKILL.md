---
name: learn-publish
description: [工具] 把 workspace 裡的 plan.html、atlas.html、截圖與聽力版整理成 dist/，可直接部署到 Cloudflare Pages，讓你在手機或其他電腦隨時看。
---

# /learn-publish　—　發佈到雲端（工具，不在 8 步流程內）

## 開始前：確認參數
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-publish [--set k=v ...]
```
把表原樣顯示，再問一次要不要調整。使用者已指定的不要再問。

## 1. 整理
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/publish.py
```
只複製 `atlas.html`（另存一份 `index.html` 當首頁）、各站 `plan.html`、`frames/`、`lesson.mp3`。
不複製原始音訊 `audio.mp3`、TTS 快取 `lesson_parts/` 與各種 json（內容已內嵌在 html）。
把印出的檔案清單與大小原樣給使用者看。

## 2. 部署（使用者同意才做）
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/publish.py --deploy --project-name <名稱>
```
- 首次要先 `npm i -g wrangler && wrangler login`（互動式登入，請使用者自己在終端機跑）。
- 部署完把網址給使用者，並提醒：**原聲片段是他人著作，建議到 Cloudflare Zero Trust → Access 設定只有自己的 email 能登入**，不要公開。
- 單檔超過 25 MB 會被擋下（Cloudflare Pages 限制），解法：降低 `narrate.py` 的音訊位元率、或該支影片改用 `--set clips=精華`。

## 之後更新
重跑同樣的指令即可，網址不變。
