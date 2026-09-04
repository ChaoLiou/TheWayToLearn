---
name: learn-segment
description: 讀 transcript.json，由 agent 切成意義段落、挑截圖時間點、決定 vision 模式，寫出 segments.json。覺得切得不好時重切。
---

# /learn-segment（agent 自己做，沒有 script）

**語言**：所有內文用該站 `meta.json` 的 `output_lang`（術語原文保留英文）。

輸入：`workspace/<影片標題>/transcript.json`、`meta.json`（有 chapters 可當參考，不必照抄）、input 的 vision 設定。
輸出：`workspace/<影片標題>/segments.json`，格式 `schemas/segments.schema.json`。

步驟：
1. 讀 `rules/segment.md`（實際路徑看 `paths.py`，可能被 `./learn.rules/` 覆寫）（切段與截圖規則、vision auto 的判斷法）。
2. 讀整份 transcript，切段、寫 title/summary、挑 shots。
3. `vision` 欄位：input 給 true/false 就照填；auto 就依規則判斷並寫 `vision_reason`。
4. 寫檔後跑 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/validate.py segments workspace/<影片標題>/segments.json`，不過就修。
5. 記錄耗時：把你這步大約花的秒數寫進 `timings.json` 的 `segment`（用 `python -c` 或直接編輯）。

已存在且沒有 `--force` 就跳過。
