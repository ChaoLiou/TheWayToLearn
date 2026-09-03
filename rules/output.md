# 輸出規則（plan.html）

改這個檔案 + templates/plan.html.j2 就是改最終文件的長相。

固定五段順序，不可調換：
1. 前情提要 & Outline
2. YouTuber 的思維推導（每支影片一節，附推理鏈 flowchart）
3. 逐段說明（每段：時間戳、截圖、承上、推理、AI 補充、術語、留給下一段）
4. 總結（附跨影片 mindmap）
5. 推薦三個下一步

Mermaid 三張圖：
- `flowchart LR` 推理鏈：節點 = 段落，邊上文字 = leads_to 精簡版
- `mindmap`：根 = 整批主題；第二層 = 影片；第三層 = 段落標題；第四層 = 術語
- `graph LR` 術語關聯圖：邊 = analysis 裡 term.related

每支影片開頭標示：vision 模式、字幕語言、時長、estimate 的預估 vs 實際耗時（如果有記錄）。

互動：
- Mermaid 圖點擊 → 全視窗 viewer（滾輪縮放、拖曳、fit、1:1、Esc 關閉）
- 截圖點擊 → 同一個 viewer 當 lightbox：← → 輪流該影片所有截圖，同樣可縮放/拖曳/fit
- 術語顯示原文；hover 出中文翻譯；旁邊 ⓘ icon 點開置中 dialog 顯示 zh / definition / more / related
- 下一步的每個搜尋關鍵字是可點的 YouTube 搜尋連結（新分頁）
- 資料夾用影片標題命名，plan.html 內的圖片路徑要 URL-encode
