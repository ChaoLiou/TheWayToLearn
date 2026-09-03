---
name: learn-fetch
description: 抓 YouTube transcript（含時間戳）與 metadata 到 workspace/<影片標題>/，不下載影片。重抓資源、換字幕語言時用。
---

# /learn-fetch

```
uv run scripts/fetch.py <url|id> [--lang zh-TW,zh,en] [--output-lang zh-TW|en] [--force]
```

- 輸出 `transcript.json`（events: start/duration/text）、`meta.json`（title/channel/duration/chapters/transcript_lang）。
- `--output-lang`：產出文件的語言，跟使用者對話語言一致（/learn 會決定）；存進 `meta.json` 的 `output_lang`。
- 已存在就跳過，`--force` 才重抓。
- 失敗常見原因：沒字幕（`yt-dlp --list-subs <url>` 看有哪些語言）、IP 被擋（換網路或加 `--cookies-from-browser`，需改 script）。
