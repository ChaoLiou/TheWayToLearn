---
name: learn-analyze
description: [步驟 5/8·逐段分析] 由 agent 逐段寫「承上／推理／AI 補充／術語／留給下一段」，遵守線性推進規則，寫出 analysis.json。換 vision 模式或重寫說明時用。
---

# /learn-analyze（agent 自己做，沒有 script）　—　步驟 5/8 逐段分析

**語言**：所有內文用該站 `meta.json` 的 `output_lang`（術語原文保留英文）。

輸入：`segments.json`、`transcript.json`、`meta.json`；vision 為 true 時再加 `frames/*.jpg`。
輸出：`workspace/<影片標題>/analysis.json`，格式 `schemas/analysis.schema.json`。

**核心規則在 `rules/narrative.md`（實際路徑看 `paths.py`，可能被 `./learn.rules/` 覆寫），先整份讀完。**

步驟：
1. 先寫 `author_reasoning`：整支影片作者從什麼出發、經過哪些步驟、得到什麼，一段文字。
2. **逐段生成，一次一段**。寫第 N 段時只看：
   - 第 N-1 段你已寫好的完整 analysis（特別是 `leads_to`）
   - 第 N 段的 segment summary + 該時間範圍的 transcript
   - vision 為 true 時，該段的 frames（用 Read 看圖）
   不要一次把整份 transcript 讀進來寫全部段落。
3. 每段填 `builds_on`（若這段有明顯錯誤或過時內容，另填 `issues`：逐字引文 + level + note，見 rules/narrative.md 第 6 條）（回應上一段 leads_to）、`reasoning`、`explanation`、`terms`、`leads_to`。每個 term：`term` 原文、`zh` 中文、`definition` 一句話、`more` 更多說明、`related` 寫成 `[{"term": "B", "rel": "關係 ≤12 字"}]`（見 rules/narrative.md 第 5 條）。
4. `vision_used` 填實際有沒有看圖；`frames` 填有看的圖路徑。
5. 寫檔後跑 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/validate.py analysis workspace/<影片標題>/analysis.json`，不過就修。
6. 把耗時寫進 `timings.json` 的 `analyze`，格式和其他階段一致——**值是物件不是數字**：
   `{"analyze": {"sec": 780, "at": "2026-09-08T22:10:17+08:00"}}`（`at` 用當地時間 ISO 8601；用 `python -c` 讀進來改再寫回，不要覆蓋既有欄位）。

已存在且沒有 `--force` 就跳過。`--vision true|false` 可覆蓋 segments.json 的設定。

## 開始前：確認參數

```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/options.py learn-analyze [--set k=v ...]
```
1. 使用者在指令裡已指定的參數用 `--set` 傳進去（例如 `--set shots=none`），它們會標成「你已指定」，**不要再問**。
2. 把 script 印出的表**原樣**給使用者看：每個參數的目前值、意義、可選值。
3. 用 AskUserQuestion 問一次「要用預設嗎？」：
   - 第一個選項固定是「用預設，直接開始（推薦）」。
   - 其餘選項是**這支 skill 實際可調且尚未指定**的參數，每個選項寫清楚改成什麼值、會有什麼差別（例如「不截圖 `--shots none`：快很多、省 token，適合畫面沒資訊的影片」）。
   - 使用者選了就照他的選擇跑；選「用預設」就直接進行。
4. 使用者這次已經在對話裡表達過偏好（例如「這支不用截圖」），視同已指定，不要重複問。

## 跑完印進度
```
uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/progress.py analyze "<一句話結果，例如 9 段>"
```
把它印出的兩行原樣回報給使用者。
