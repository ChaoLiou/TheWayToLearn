# 敘述規則：線性推進（linear thematic progression）

改這個檔案就是改 AI 逐段說明的行為。analyze 階段的 skill 會把整份檔案讀進 prompt。

## 輸出語言
- 所有內文（summary、builds_on、reasoning、explanation、definition、more、note…）用該站 `meta.json` 的 `output_lang`：使用者用中文對話 → `zh-TW`；用英文 → `en`。
- 術語的 `term` **永遠是英文原文**，不翻譯。`zh` 欄位 = 用輸出語言寫的簡短對譯／注釋；輸出語言本身是英文時 `zh` 可留空字串。
- 勘誤的 `quote` 永遠是 transcript 原文，不翻譯。
- HTML 的固定介面文字由 `scripts/i18n.py` 依 `output_lang` 切換，不用管。

## 硬規則（validate.py 會檢查）
1. 第 N 段的 `builds_on` 必須回應第 N-1 段的 `leads_to`。第 1 段的 `builds_on` 描述「前情提要」中的哪個背景被用上。
2. 每段的 `leads_to` 必須留下一個具體線索、問題或未完成的推論給下一段。最後一段的 `leads_to` 寫「總結收束」。
3. 段落內不得引用尚未出現的段落（禁止「後面第 5 段會講」這類前向引用）。
4. 術語在**第一次出現的那一段**就地解釋，之後的段落不再重複定義，只可回指「（見第 N 段）」，N < 目前段。
5. 術語欄位：`term` 一律用**原文**（英文），`zh` 中文翻譯（hover 顯示），`definition` 一句話（內文顯示），`more` 更多說明（點 icon 開視窗，可寫 3–6 句：來龍去脈、常見誤解、跟相鄰術語的差異）。`related` 寫成 `{"term": "B", "rel": "關係"}`，rel ≤ 12 字、有方向（A → B），例如「對照組」「實作於」「前提」「一種」「相反」。

6. **勘誤／過時**：某段作者說的內容若明顯錯誤或已過時（問題已不存在、功能已移除或新增），寫進該段的 `issues`；沒有就不寫。
   - `quote` 必須是 transcript 的**逐字引文**（validator 會比對 `transcript.json`），不可用 AI 自己的轉述當判斷依據。
   - `level`：`wrong` = 確定錯誤或已不存在（紅）；`debatable` = 可能對可能錯、取決於版本或情境、見仁見智（橘）。
   - `note` 說明錯在哪、現況為何；`evidence` 給版本號／年份／文件名。
   - 只列「內容」的錯，不列口誤、簡化、個人偏好。

## 軟規則（風格）
- 每段的 `reasoning` 用「因為上一段…，所以作者接著…」的句式開頭，讓因果鏈可見。
- `explanation`（AI 補充）只補作者沒說清楚、但推理需要的部分；不重述 transcript。
- 用讀者已有的（前段建立的）概念解釋新概念；不要用尚未定義的術語解釋另一個術語。
- 作者說錯或跳步時，在 `explanation` 指出，並補上被跳過的那一步。

## 來源是部落格文章時

規則全部照舊；只有指涉方式不同：不要寫「影片裡」「作者說到 3:20 時」，改成「文中」「在〈小節標題〉一節」。
時間軸的秒數是閱讀時間，render 會顯示成段落編號（¶n），`issues[].t` 照樣填該段落的 `start` 秒數，`quote` 仍須逐字來自 `transcript.json`。
