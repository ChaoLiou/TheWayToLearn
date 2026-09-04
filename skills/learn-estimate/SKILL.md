---
name: learn-estimate
description: 只給 YouTube 連結就估「下載、分析各階段時間、token、磁碟」，分階段列出並加總，不下載影片。/learn 的第 0 步，也可單獨用。
---

# /learn-estimate

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/estimate.py <url> [<url> ...] [--vision true|false|auto]
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/estimate.py --input input.yaml
```

- 把 script 印出的表格**原樣**貼給使用者（每支影片分階段 + 小計；最後全部總和 + 跨影片彙整）。
- `vision=auto` 時以 false 估，並另列「若 true 再加多少」，讓使用者決定。
- 出現「沒有任何字幕」的警告要特別指出，那支影片目前跑不了。
- 係數在 `config/estimate.yaml`；使用者覺得估得不準就改係數，不改程式。
- 結果寫在 `workspace/<影片標題>/estimate.json`，render 會拿來跟實際耗時對照。
