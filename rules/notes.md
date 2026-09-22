# 成長筆記規則（/learn-notes）

改這個檔案就是改 `/learn-notes` 的行為。目的：把一支影片／一篇文章**留給我的東西**擷取成幾條筆記，彙整在 `workspace/notes.html`，每條都連回 `plan.html` 的那一段。

## 讀什麼

- `analysis.json`：每段的 `reasoning`、`explanation`、`terms`、`leads_to`——筆記的原料
- `_overview.json`：`takeaways`、`summary`——判斷哪些才是這支影片真正的重點
- 已有 `notes.json` 時：只在使用者說要重做（`--force`）時覆寫

## 挑什麼

- 每站 **3–8 條**，上限 12。少而準，不是摘要全片。
- 三種 `kind`，寫的時候先問自己是哪一種：
  | kind | 問句 | 例 |
  |---|---|---|
  | `concept` | 這是什麼、為什麼會這樣？ | 「LCP／INP／CLS 各量到渲染路徑的不同位置」 |
  | `skill` | 明天就能照做的一件事？ | 「先內聯首屏 CSS，其餘延後載入」 |
  | `insight` | 改變我判斷方式的準則？ | 「優化到極限就該換架構，架構換完再換組織」 |
- 只留**看完之後我才知道**的東西；常識、影片開場白、標題本身不算。
- 一條只講一件事。`text` 一句話（≤ 80 字），我三個月後看到還懂；`detail` 選填，補為什麼重要或怎麼用。
- 每條一定要有 `seg_id`：這條是從哪一段來的；找不到出處的就不要寫。
- `terms` 用英文原文，跟 `analysis.json` 一致。

## 語言

`text` / `detail` 用該站 `meta.json` 的 `output_lang`；術語永遠英文原文。

## 產出後

1. `scripts/validate.py notes <站>/notes.json`（schema + `seg_id` 必須存在於 `analysis.json`）
2. `scripts/notes.py` 重產 `workspace/notes.html`
3. 使用者在 notes.html 上可以對每條按「留」／「刪」，狀態存瀏覽器；「匯出」下載 `notes.keep.json`，放到 workspace/ 後 `notes.py` 會當成預設狀態
