# 學習地圖（Atlas）規則

改這個檔案就是改 /learn-atlas 的行為。名詞：**waypoint** = 一支影片的資料夾（一站），**route** = 兩站之間的關聯，**region** = 主題區。

## 語言
- region 的 `name`/`blurb`、route 的 `via` 用多數站的 `output_lang`；可在 atlas.json 加 `"lang": "en"` 強制介面語言。

## 什麼時候更新
- workspace 下有 ≥ 2 個 waypoint 時，每新增一個就更新 `workspace/atlas.json`，然後重新 render `atlas.html`。
- 只需決定「新站」與既有各站的 route，以及新站屬於哪個 region；既有 route 不動，除非新站讓某條 route 的型態明顯該改。

## Route 型態（有方向，from → to）
| type | 意思 | 什麼時候用 |
|---|---|---|
| `prerequisite` | 先看 from 再看 to | to 直接用了 from 建立的概念而沒重新解釋 |
| `deepens` | to 深入 from 的某個主題 | from 只講概念、to 講機制或實作 |
| `contrasts` | to 與 from 對照 | 兩支講同類東西但立場、產品、取捨不同 |
| `applies` | to 把 from 的概念用到具體場景 | from 是元件／原理、to 是完整系統或案例 |
| `related` | 相關，無方向 | 有共同概念但上面四種都不貼切 |

- 兩站之間最多一條 route，選最貼切的型態。
- `via` 寫**為什麼**：共同術語（用 `atlas.py --status` 印出的重疊）或承接關係，≤ 40 字。
- 沒有關聯就不要硬連；孤立的站是正常的。

## Region
- 一站只屬於一個 region；不確定就先不分（會顯示在「未分區」）。
- region 命名用主題（「訊息系統」「分散式儲存」），不用影片名。
- `blurb` 一句話：這區學什麼、從哪站開始。

## 判斷依據
- 用各站的 `_overview.json`（topic、prerequisites、takeaways、summary）與 `analysis.json` 的術語；`atlas.py --status` 會把新站與每個既有站的共同術語印出來。
- 「prerequisite」的判斷看 to 站的 `prerequisites` 是否被 from 站的 takeaways 覆蓋。
