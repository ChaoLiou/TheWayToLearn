# 站與站的關係（Atlas）規則

改這個檔案就是改 /learn-atlas 的行為。名詞：**waypoint** = 一支影片的資料夾（一站），**route** = 兩站之間的關聯，**region** = 主題區。

## 語言
- region 的 `name`/`blurb`、route 的 `via` 用多數站的 `output_lang`；可在 atlas.json 加 `"lang": "en"` 強制介面語言。

## 什麼時候更新
- workspace 下有 ≥ 2 個 waypoint 時，每新增一個就更新 `workspace/atlas.json`，然後重新 render `atlas.html`。
- 只需決定「新站」與既有各站的 route，以及新站屬於哪個 region；既有 route 不動，除非新站讓某條 route 的型態明顯該改。

## Route 型態（只有兩種）
| type | 意思 | 什麼時候用 |
|---|---|---|
| `next` | 看完 from 接著看 to（有方向） | to 用到 from 建立的概念、或 to 是 from 的下一步（更深、更完整、換到實作） |
| `related` | 兩站相關，但沒有先後（卡片詳細裡顯示，不標方向） | 談同一類東西可互相參照，但誰先誰後都行 |

- 判斷順序：先問「有沒有建議的觀看先後」——有就 `next`，方向是**先看的那一站 → 後看的那一站**；沒有才用 `related`。
- 兩站之間最多一條 route。
- `via` 寫**為什麼接著看**：共同術語（用 `atlas.py --status` 印出的重疊）或承接關係，≤ 40 字。例如「A 講完 broker，B 直接拿來用」。
- 沒有關聯就不要硬連；孤立的站是正常的。
- 盡量讓每個 region 內部用 `next` 連成一條看得出順序的線，卡片上「接著看」才有東西可點。

## Region
- 一站只屬於一個 region；不確定就先不分（會顯示在「未分區」）。
- region 命名用主題（「訊息系統」「分散式儲存」），不用影片名。
- `blurb` 一句話：這區學什麼、從哪站開始。

## 判斷依據
- 用各站的 `_overview.json`（topic、prerequisites、takeaways、summary）與 `analysis.json` 的術語；`atlas.py --status` 會把新站與每個既有站的共同術語印出來。
- `next` 的方向看 to 站的 `prerequisites` 是否被 from 站的 takeaways 覆蓋；覆蓋得越多，越該是 from → to。
