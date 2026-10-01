# 輸出規則（plan.html）

改這個檔案 + templates/plan.html.j2 就是改最終文件的長相。

固定五段順序，不可調換：
1. Outline（`_overview.json` 的 prerequisites 仍要寫——atlas 判 route 要用——但不顯示在頁面上）
2. 作者的思維推導（每支影片一節，`author_reasoning` 由 render 自動切成段落，別寫成一整陀）
3. 逐段說明（每段：時間戳、截圖、承上、推理、AI 補充、勘誤／過時（有才顯示）、留給下一段）
4. 總結（有勘誤時附「勘誤總整理」表，紅色 = 確定錯誤／已不存在，橘色 = 見仁見智）
5. 推薦三個下一步
最後：相鄰站與主題區（atlas nav）擺在文件最底下，開頭直接是內容。

**沒有 Mermaid 圖**（2026-09 拿掉）：推理鏈本來就是一條線，畫成圖不比文字多給資訊，改成收合的文字列表；mindmap 與術語關聯圖實際上沒人看。

每支影片開頭標示：vision 模式、字幕語言、時長；estimate 的預估 vs 實際耗時收在 `<details>` 裡。

互動：
- 截圖點擊 → 同一個 viewer 當 lightbox：← → 輪流該影片所有截圖，同樣可縮放/拖曳/fit
- 術語**就地標在文章裡**：`summary` / `reasoning` / `explanation` 第一次出現該術語的地方加底線，旁邊一顆小 ⓘ 點開 dialog（zh / definition / more / related）。文中完全沒出現的術語才收在段末一行 `.terms-extra`
- 語音解析卡片只留播放器與講稿鈕，章節收在 `<details>`
- 下一步的每個搜尋關鍵字是可點的 YouTube 搜尋連結（新分頁）
- 資料夾用影片標題命名，plan.html 內的圖片路徑要 URL-encode
