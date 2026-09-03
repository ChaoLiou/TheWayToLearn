---
name: learn-shot
description: 依 segments.json 的 shots 下載影片並用 ffmpeg 抽幀到 workspace/<影片標題>/frames/。改了時間點後重截時用。
---

# /learn-shot

```
uv run scripts/screenshot.py <id> [--force] [--keep-video]
```

- 需要 `ffmpeg`（`sudo apt install ffmpeg`）。
- 影片只下載一次（≤ `config/estimate.yaml` 的 max_height），抽完預設刪除。
- 會把 `frames/sNN_<秒>.jpg` 路徑寫回 `segments.json` 的 `shots[].file`。
- segments 沒有任何 shots 時直接結束，不下載。
