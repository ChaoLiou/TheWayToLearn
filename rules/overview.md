# 彙整規則（每支影片各自一份 _overview.json；合併多支時同樣適用）

改這個檔案就是改 /learn-render 前置的 overview 產生行為。內文語言依該站 `meta.output_lang`（見 rules/narrative.md「輸出語言」）；`search_keywords` 用最可能搜到好影片的語言（通常英文）。

## 前情提要（prerequisites）
- 列出看這批影片前需要先懂的概念，每個 1–2 句。不解釋影片內會定義的術語。

## Outline
- 每支影片一條，含它的角色（起點 / 承接 / 對照 / 應用）；單支影片就一條「起點」。

## 總結（summary）
- 把所有影片的推理鏈接成一條：A 建立了 X → B 用 X 推出 Y → …

## Takeaways（3–5 條）
- 「看完這支影片你會懂什麼」，每條一句、以動詞或名詞開頭、≤ 40 字。給文字說明列表（atlas.html）的卡片用，讀者靠這幾句決定要不要點進來。

## 三個下一步（next_steps，固定 3 個）
- 每個方向：`direction`（方向名）、`why`（跟目前推理鏈的哪個缺口有關）、`search_keywords`（2–4 個可直接貼到 YouTube 搜尋的關鍵字，含英文）。
- 三個方向要分別是：往下挖深、往旁邊對照、往上應用。
