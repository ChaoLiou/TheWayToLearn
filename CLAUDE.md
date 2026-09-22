# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 兩種使用模式

同一份 repo 既可 clone 進來直接用（`.claude/skills` 是 `skills/` 的 symlink），也可當 Claude Code plugin 安裝（plugin 名 `pacer`，marketplace 名 `thewaytolearn`；指令前綴 `/pacer:`）。SKILL.md 裡所有指令都寫成 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}/scripts/<x>.py"`，兩種模式都能跑。
- workspace：`$LEARN_WORKSPACE` > 目前目錄 `./workspace/`
- 規則覆寫：`$LEARN_RULES` > 目前目錄 `./learn.rules/`（同名檔案覆蓋 `rules/`、`config/`、`templates/`），`scripts/paths.py` 印出實際生效路徑
- 改 skill 就改 `skills/<name>/SKILL.md`

## 常用指令

```bash
uv sync                                   # 安裝依賴（Python 3.11+，yt-dlp 走 pip；ffmpeg 要另外 apt install）
uv run pytest -q                          # 全部測試
uv run pytest tests/test_validate.py -k forward   # 單一測試
uv run ruff check scripts tests           # lint
uv run scripts/estimate.py <url> ...      # 估時間成本，不下載（播放清單網址會自動展開）
uv run scripts/playlist.py <playlist_url> # 展開播放清單：依清單順序列出每一支（--items 1-10 / --urls / --json）
uv run scripts/fetch.py <url>             # 抓字幕 + meta（非 YouTube 網址 = 部落格文章，抓正文段落）
uv run scripts/screenshot.py <id>         # 下載 + ffmpeg 抽幀（讀 segments.json）
uv run scripts/validate.py <segments|analysis|overview> <file.json>
uv run scripts/render.py                  # 每支影片各自產 plan.html
uv run scripts/atlas.py --status          # 列新站與各站共同術語（決定 route 用）
uv run scripts/atlas.py                   # 驗證 atlas.json、產 workspace/atlas.html（文字說明列表）
uv run scripts/atlas.py --merge p.json    # 併入新站的 route/region（不整份覆寫）再 render
uv run scripts/atlas.py --migrate-routes  # 舊的五種 route 型態換成 next / related
uv run scripts/listen.py                  # podcast 頁：workspace/listen.html + 各站 captions.js
uv run scripts/notes.py                   # 成長筆記（工具）：彙整各站 notes.json → workspace/notes.html
uv run scripts/digest.py [--backlog|--pending [id]|--mark id:n 動作 [值]]   # PACER 工作單：digest.html + brain/ + 積欠
uv run scripts/brain.py [--out DIR]       # 只匯 Obsidian vault
uv run scripts/paths.py                   # 印出 workspace / 規則檔實際路徑
uv run scripts/publish.py [--deploy]      # 整理 dist/ 並可部署到 Cloudflare Pages（index.html = listen.html）
```
測試不碰網路：`tests/fixtures/ws/` 是一組完整的 workspace 樣本，改 schema / template / validator 後跑 pytest 就能驗。

## 專案目標

使用者給一串 YouTube 連結（或部落格文章網址）→ 程式抓取 transcript 與重要時間點的截圖 → 產出一份「學習規劃」文件。
最終交付形式是一個 **skill**（給 AI agent 使用），加上 agent 執行該 skill 所需的全部程式。

## 來源也可以是播放清單

貼 `youtube.com/playlist?list=…` 就是「這一串，照順序做」。展開集中在一個地方，下游完全不知道有播放清單這回事：
- `scripts/playlist.py`：`yt-dlp --flat-playlist --dump-json` 列出清單，`entries()` 回清單順序的影片（失效／私人／**會員限定、付費、需登入**（`availability`）／清單內重複的跳過並記在 `skipped`，免得跑到 fetch 才發現抓不到），每支換成乾淨的 `watch?v=` 網址（去掉 `list=`），所以 `--no-playlist` 不再有歧義。
- `expand_videos(videos, mode="one")`：就地把清單那筆換成它的每一支，順序不變、繼承同一筆的 `shots` / `vision` / `max_shots`；`items`（`1-10`）或 `limit` 可限定範圍。`common.load_input()` 與 `estimate.py` 的指令列各呼叫它一次（`load_input` 只在網址真的有 `list=` 時才 import，免得每次都載 yt-dlp）。
- **`watch?v=…&list=…&index=N`（從清單裡點進某一支）是有歧義的**，用 mode 決定：`one`（預設，只做那一支）／`all`（整份清單）／`from-here`（從那一支到最後，靠 `entries(from_here=True)` 砍掉前面的）。指令列是 `estimate.py --playlist one|all|from-here`、`playlist.py --from-here`，input.yaml 則在該筆寫 `playlist: all`。`/learn` 遇到這種網址一定問一次（三個選項），`estimate.py` 預設只做那一支但會印一行「註：…帶著播放清單 …」提醒還有另外兩條路。`common.playlist_index(url)` 讀 `index=N`。
- `video_id()` 拿到純清單網址會報「這是播放清單不是單支影片」並指向 `playlist.py`。
- `/learn` 拿到清單：先 `playlist.py` 展開給使用者看、問要做幾支（不預設全跑），再**一支跑完整條流程才跑下一支**（讀者可以先讀第一支的 `plan.html`）；已經有 `plan.html` 的站跳過，所以重貼同一個清單就是接續上次。atlas 時把清單連成一條 `next` 鏈、同一個 region。

## 來源也可以是部落格文章

非 YouTube 的 `http(s)` 網址一律當文章（`common.video_id()` 回 `b_` + 網址 sha1 前 9 碼，仍是 11 碼，所以 `find_video_dir` 等全部照用；`is_blog(id|meta)` 判斷）。設計原則是**讓文章長得跟影片一樣**，下游不分支：
- `scripts/blog.py`（trafilatura）：正文每個段落／標題／程式碼／清單／表格是一個 event，`start` = **閱讀秒數**（`config/estimate.yaml` 的 `blog.cjk_chars_per_min` / `words_per_min`），另有 `kind`、`para`；圖片列在 `transcript.images[{t, src, alt}]`；`meta.json` 有 `source: blog`、`thumbnail`（og:image）、`chapters`（各級標題）、`site`。
- estimate：`probe()` 看到非 YouTube 網址就抓頁面算閱讀時間與圖片數，截圖數以文中圖片數封頂、無下載量。
- shot：`screenshot.py` 遇到 blog 站不下載影片、不需要 ffmpeg，每個 shot 依 `src`（或離 `t` 最近的圖）下載到 `frames/sNN_<秒>.<原副檔名>`；segments schema 的 shot 多一個選填 `src`。
- render：`seeker()` 回 `at(t)`：影片給 `url&t=Ns` + `m:ss`，文章給 text fragment 連結（`#:~:text=`，勘誤直接對 `quote`）+ `¶段落編號`；模板只用 `s.start_href` / `s.start_label` / `sh.t_label` / `iss.href`，不自己拼網址。全部都是文章時標題換成「作者的思維推導」。
- narrate：沒有原聲，clip 改成用文章語言、跟講解不同的聲音（`read_voice`）逐句朗讀原文（`read_texts()`），一句一個檔，長度就是 karaoke 節奏；`translation` 一樣會產 dub 軌。`dub_lines` 對英文句子放寬到三倍長度並在句點後接大寫時切句。
- atlas：卡片縮圖用 `thumbnail`，沒有就退回第一張文中圖片；連結文字「原文」。
- 規則：`rules/segment.md`、`narrative.md`、`narration.md` 最後各有一節「來源是部落格文章時」。

## 產出文件的固定結構（順序不可變）

1. **前情提要 & Outline** — 看這支影片前需要的背景，以及影片大綱
2. **YouTuber 的思維推導** — 作者如何一步步推出結論
3. **逐段說明** — 依影片分段，每段包含：
   - 該段內容摘要（附時間戳、對應截圖）
   - AI 補充說明
   - **該段出現的術語** 就地解釋（不集中到文末的 glossary）
4. **總結**
5. **推薦三個下一步** — 三個方向，各附建議在 YouTube 搜尋的關鍵字

## 預定架構（pipeline）

```
URL 列表
  → estimate:   yt-dlp --dump-json 拿時長/檔案大小/字幕有無 → 分階段估時間、token、磁碟（不下載）
  → fetch:      取得影片 metadata + transcript（含時間戳）
  → segment:    把 transcript 切成有意義的段落，選出每段的關鍵時間點
  → screenshot: 依關鍵時間點擷取影格（需要 ffmpeg / yt-dlp 類工具）
  → analyze:    LLM 對每段做說明、抽術語、推導作者思路
  → render:     組合成上述固定結構的文件（HTML，內嵌 Mermaid，截圖以相對路徑引用）
```

## 輸出格式

- `plan.html`：單一 HTML 檔，Mermaid 走 CDN。固定產三張圖：
  - `flowchart LR` 推理鏈：每段一節點，邊上寫該段留給下一段的線索
  - `mindmap`：主題 → 各段 → 術語
  - `graph` 術語關聯圖：術語間的依賴/對比
- 每支影片開頭註明使用的 vision 模式（見下）

## 線性推進（核心規則）

AI 的逐段說明必須「線性推進」（thematic progression / linear progression）：上一段留下的線索是下一段的出發點，不可跳段、不可引用尚未出現的段落。
實作方式：
- analyze 階段逐段生成，prompt 只帶上一段的完整 analysis，不一次餵整份 transcript
- `analysis.json` 每段必填 `builds_on` / `reasoning` / `leads_to`；第 N 段的 `builds_on` 必須回應第 N-1 段的 `leads_to`
- validator 檢查 `builds_on` 只指向更早的 segment；render 把承接句以「承上：…」顯示

## 截圖與 vision（每支影片各自設定）

`input.yaml` 每支影片有兩個獨立開關：
- `max_shots`（預設 12，`many` 24，在 `config/estimate.yaml`）——整支影片的截圖上限，`validate.py` 會擋。每張圖在 analyze 約 1,200 tokens 且會常駐整段 context，這是單一最大成本來源。
- `shots: auto | none | many`（預設 `auto`）——要不要截圖。`none` 完全不截、也不下載影片，步驟 4 跳過；`auto` 由 agent 依 `rules/segment.md` 只挑「看了才懂」的畫面，整支都沒有就自動降成 `none`。寫進 `segments.json` 的 `shots_mode`。
- `vision: true | false | auto`（預設 `true`）——AI 要不要逐張讀截圖；`shots: none` 時無意義。

## vision 模式（每支影片各自設定）

`input.yaml` 每個 URL 有 `vision: true | false | auto`（**預設 true**），決定 analyze 階段 agent 是否逐張讀截圖。`auto` 由 agent 在 segment 階段判斷並寫回 `segments.json`。

## 文字說明列表（atlas.html）

**沒有地圖了**（2026-09 拿掉：mermaid 大圖對 50 站沒幫助）。atlas.html 的定位是「所有文字說明（plan.html）的列表」：依 region 分組的縮圖卡、搜尋列、每站的相鄰站與勘誤。名詞不變：workspace 下每個影片資料夾是一個 **waypoint**；`workspace/atlas.json` 記 **route**（兩站關聯只有兩種：`next` = 看完 from 接著看 to，有方向；`related` = 相關但沒先後，不標方向；都含 via 說明為什麼）與 **region**（主題區）。`scripts/atlas.py` 產 `workspace/atlas.html`，各站 `plan.html` 頂部有回到列表與相鄰站的連結。
「各站」是 YouTube 式縮圖卡（縮圖用該站第一張截圖，沒有就退回 i.ytimg.com；標題／作者／上傳日期／時長），上方搜尋列是 `templates/_search.html.j2` 的共用 macro（條件做成 chip：作者／分類／標題／任意，作者與分類有 autocomplete，空白或 Enter 加下一個條件，條件之間是 AND；listen.html 用同一份）。作者名旁邊有**這支影片的勘誤件數**膠囊（紅八角 danger = 確定錯誤／已過時、橘三角 warning = 見仁見智，只算這一站，0 就不顯示該顆；`errata_stats()`），hover 看摘要、點下去開置中視窗看該影片的勘誤表（段落／原話／說明，每列連到 plan.html 的該段）。「詳細」開置中視窗（`showInfo()`）看摘要、takeaways、相鄰站。≥ 2 站時每新增一站由 agent 依 `rules/atlas.md` 寫 patch，跑 `atlas.py --merge <patch.json>` 併進 atlas.json（有檔案鎖、驗證沒過不寫入，多支同時跑不會互蓋）。模板共用 `templates/_base.html.j2`（viewer、mermaid（只在頁面有 `.mermaid` 時才從 CDN 載，載不到不影響其他 JS）、tooltip、勘誤樣式）與 `templates/_icons.html.j2`（勘誤圖示 `ic.danger()` / `ic.warn()` / `ic.level()`）；atlas 的三個置中視窗共用 `dialog.modal` 一套樣式。
每張卡片下方有 **pipeline 進度**：十步各一格（`atlas.py` 的 `pipeline()` 直接看檔案判定 done / partial / todo / skip），加一行白話狀態（例如「還沒處理原音：沒有挑原聲片段」——聽力版做了但 `segments.json` 沒有 clips / clips 沒 translation / 還沒有 dub 軌都算 partial）。「▸ 繼續做」開視窗列出十步狀態，選「做到哪一步」後把對應的 prompt 複製到剪貼簿，使用者自己貼進 Claude Code 跑（`next_actions()` 產生；prompt 用 `common.STEP_CMD`，缺原聲／缺翻譯會自動附上該怎麼補的說明）。

## 輸出語言

跟著使用者下指令的語言：`/learn` 判定後寫進 `input.yaml` 的 `output_lang` 與各站 `meta.json`；agent 產的所有內文用它，術語 `term` 永遠英文原文；HTML 介面文字由 `scripts/i18n.py` 依語言切換（新語言只需加一組字串）。

## 參數確認

每支 skill 開始前先跑 `scripts/options.py <skill> [--set k=v]`：印出該階段用得到的參數、目前值、意義與可選值；使用者已指定的標成「你已指定」。agent 把表原樣顯示，再用 AskUserQuestion 問一次要不要調整（第一個選項固定「用預設」）。`/learn` 只在開頭問一次。參數清單集中在 `options.py` 的 `PARAMS` / `SKILL_PARAMS`，新增參數只改這裡。

## 步驟進度

流程固定 10 步（`STEPS` 在 `scripts/common.py`）：estimate → fetch → segment → shot → analyze → digest → render → atlas → narrate → listen（atlas 需 ≥2 站；digest / narrate / listen 各由 `--digest` / `--narrate` / `--listen` 控制，預設都開）。依賴其實是樹：fetch→segment→(shot)→analyze 是主幹，之後 digest / render / atlas / narrate 只依賴 analyze，listen 依賴 narrate；digest 排在 render 前是讓 plan.html 第一次就有 PACER 標籤。notes 不在十步裡了（工具 skill `/learn-notes`）。estimate 最後印消化積欠，超過 `config/estimate.yaml` 的 `balance.max_backlog` 就警告（`/learn` 停下來建議先 `/learn-digest do due`，`--force` 硬跑）。每個 script 跑完呼叫 `print_step()` 印 `[N/10] ✔ … ●●●○○○○○○○` 與下一步；agent 自己做的階段（segment / analyze / atlas 彙整）跑完呼叫 `scripts/progress.py <stage> "<結果>"`。改步驟只改 `STEPS`，SKILL.md 的標題與 description 前綴要一起改。

## 改規則不改程式

行為都外置，改對應檔案即可：
- 切段 / 截圖挑選 / vision auto 判斷 → `rules/segment.md`
- 線性推進與 AI 說明風格 → `rules/narrative.md`（硬規則由 `scripts/validate.py check_analysis` 執行，新增硬規則要同步加檢查 + 測試）
- 彙整、takeaways、三個下一步 → `rules/overview.md`
- 站與站的 route / region 判斷 → `rules/atlas.md`
- 聽力版講稿與原聲片段長度 → `rules/narration.md`
- 成長筆記挑什麼、幾條、怎麼寫 → `rules/notes.md`（硬規則由 `validate.py check_notes` 執行）
- PACER 消化工作單怎麼分類、每類要寫什麼 → `rules/digest.md`（硬規則由 `validate.py check_digest` 執行）

## 聽力版（lesson.mp3）

`narrate.py` 把 `narration.json` 的 `say`（edge-tts）與 `clip`（yt-dlp 音訊 + ffmpeg）串成 `lesson.mp3`：
- clip 的起訖自動對齊 transcript 句子邊界（`snap`），逐句字幕併成順口長度（`clip_lines`）寫進 `lesson.json`
- 片段以內容雜湊命名快取在 `lesson_parts/`，改字幕合併或章節不必重跑 TTS
- `lesson.status.json` 讓步驟 6 產出的 `plan.html` 顯示「聽力版產生中」，完成後頁面自己偵測並重新整理（`--mark-pending` 可提前標記）
- `plan.html` 有播放器、章節，以及 karaoke 講稿視窗（已唸過=一般色、目前=強調、未唸=灰、原聲=斜體，點任一句從那裡播）
- clip 有 `translation` 就多產一軌 `lesson.dub.mp3`：原聲換成另一個聲音（`--dub-voice`，預設同語言不同性別）唸翻譯，講解部分兩軌共用同一批 TTS 檔。翻譯逐句合成，長度即 KTV 高亮節奏。網頁上「🎙 原聲 / 🗣 翻譯」切換（快捷鍵 D），兩軌 block 一一對應所以切換後停在同一個位置，章節與講稿一起換；`--no-dub` 關掉
- 文件版面 → `rules/output.md` + `templates/plan.html.j2`
- 估算係數 → `config/estimate.yaml`
- agent 輸出格式 → `schemas/*.json`

## Podcast 頁（listen.html）

`scripts/listen.py`（第 10 步，`/learn --listen false` 可跳過）把所有有 `lesson.mp3` 的站列成一集一集，**依產出時間新到舊**（`lesson.json` 的 `created`，舊檔沒有就看 mp3 mtime），產 `workspace/listen.html`；`narrate.py` 跑完會自動重產一次（`.listen.lock` 檔案鎖）。
- 置底播放器：⏮ −15 ▶ +15 ⏭、語速、`CC` 字幕（快捷鍵 C）、原聲／翻譯切換（快捷鍵 D，該集有 dub 軌才出現）、Media Session（鎖定畫面／耳機按鍵）。每集記住上次聽到哪裡（localStorage，一律存原聲軌秒數）、播完標「聽完」並自動接下一集；`listen.html#<vid>` 直接打開那一集。
- 字幕 = 講稿 karaoke，資料不內嵌在頁面（42 站會到 3.5 MB），而是每站一個 `captions.js`（`listen.captions()` 的精簡格式：`o`/`d` 逐句、`ob`/`db` 每個 block 的 [at,dur] 供切軌對位、`ch`/`segs` 章節），播到才用 `<script>` 動態載入——所以 `file://` 直接開也有字幕，不靠 fetch。
- 模板 `templates/listen.html.j2` 繼承 `templates/_lite.html.j2`（跟 `_base` 同配色但**不載 mermaid CDN**，離線／手機能開）；`notes.html.j2` 也用它。
- 每集顯示分類（= `atlas.json` 的 region 名，沒進 atlas 的顯示「未分區」，點分類就加一個篩選條件）與原始網址；搜尋列跟 atlas.html 同一份（`templates/_search.html.j2` 的 `css()` / `bar()` / `json()` / `js(card_sel, group_sel)` macro，卡片要有 `data-title` / `data-channel` / `data-category`），改搜尋行為只改那一個檔。
- 每集連到 `plan.html`、有 notes 就連到 `notes.html#<vid>`；`plan.html` 頂部有 `.hub` 連回 `listen.html#<vid>` / `notes.html#<vid>`；`atlas.html` 頂部有 topnav。發佈時 `index.html` = `listen.html`（沒有才退回 `atlas.html`）。

## 消化工作單（digest.json → digest.html，第 6 步）

依「How to Remember Everything You Read」的 PACER 法：讀完之後把每**一筆資訊**（不是一段、不是一支）標 `kind ∈ P/A/C/E/R`，並寫下該類專屬的消化動作，讓使用者去做而不是再讀一次。
- **資料**：`<站>/digest.json`（`schemas/digest.schema.json` 用 if/then 擋每類必填：P `procedure`+`practice_task`、A `new`+`known`（`critique_key` 選填答案卷）、C `concept`+`relations`（答案卷，頁面預設不顯示）、E `detail`+`supports`+`rehearse_q`、R `q`+`a`）。`validate.py digest` 另外查 `seg_id` 存在、C 一站 ≤ `MAX_C`=10 筆（地圖畫得動的上限，其餘降 R）、C concept 同站唯一、`relations[].to` 指向同站 C 或 analysis term、`supports` 只能指 C。規則在 `rules/digest.md`。
- **頁面**：`scripts/digest.py` → `workspace/digest.html`（`templates/digest.html.j2`，繼承 `_lite`）。頂部「今天」= 到期 R 卡數／待演練 E 數／P·A·C 未做數 + 「開始回想」；每站依五類分區，每筆是該類的動作 UI：P 步驟＋今天就做＋做完了、A 三格（像／不像／失效）＋對照 AI 版、C 已畫進地圖＋對答案、E 演練（第一下展開作答、第二下記錄）、R flashcard（SM-2：忘了／難／會，快捷鍵 1/2/3、空白翻面）。預設篩「只看未做」。
- **狀態**：瀏覽器 localStorage（key `digest-state`），「匯出進度」下載 `digest.state.json`（`{"<vid>:<id>": {...}}`：P/A/C `done`、E `rehearsed`、R `ef/reps/interval/due`；另有整站的 `"<vid>:read": {"read": ISO}`），放到 `workspace/` 後 `digest.py` 內嵌成預設；`digest.backlog(ws)` / `--backlog` 讀同一份算積欠，給 `/learn` 平衡閥用。「匯出 Anki」下載 R 卡 tsv。
- **消費 vs 消化**：產出工作單不算讀過。每站有「📖 讀完了」（`digest.py --mark <vid> read|unread`，`read_key()`）；**沒標讀完的站不算積欠、不進 `--pending`、頁面上收起不計入「今天」**，積欠行末印「未讀 N 站不計」。E 的「隔一天」從讀完那天起算（`rehearse_from`）。
- **plan.html**：每段「推理」下方列這段的 PACER 標籤（`.pacer`，字母＋一句＋該做的動作，hover 看為什麼），點了跳 `digest.html#<vid>-d<id>`；頂部 hub 多「🍽 消化」。listen / notes / atlas 的 topnav 有 digest.html 就連。發佈時 `index.html` 順位：listen > digest > notes > atlas。
- **skill `/learn-digest`**（`skills/learn-digest/SKILL.md`）：`<id|all>` 產工作單（agent 依 rules 寫 digest.json → validate → digest.py → render.py）；`do [<id>|due] [P|A|C|E|R]` 對話式消化——`digest.py --pending` 取未做的筆（含答案卷，agent 不先貼），使用者答完 agent 對照回饋，`digest.py --mark <vid>:<id> done|undo|rehearsed|grade|<欄位>=<值> [值]` 寫 `digest.state.json`（`.digest.lock` 檔案鎖）並重產頁；`today` = `--backlog`。SM-2 在 Python（`sm2()`）與 JS 各一份，要一起改。
- **second brain**：`scripts/brain.py`（`digest.py` 跑完自動呼叫）把所有站的 digest.json + digest.state.json 匯成 `workspace/brain/`（Obsidian vault）：`stations/<站>.md`（五類分區、做完打勾、心得／回答／下次到期）、`concepts/<概念>.md`（同名概念跨站合併：analysis term 定義、各站說法、—rel→ `[[to]]`、E 證據、來源）、`README.md` 索引。檔名過 `safe()`（`/:*?"<>|#^[]` → `-`），`wl()` 產 `[[檔名|原名]]`。
- **tldraw 先畫再對答案**：`/learn-canvas map <id>` 只把 C 概念當節點散在畫布上、不畫線；使用者連完說「對答案」→ `/learn-digest do <id> C` 讀 arrow 綁定對照 `relations`（多畫／漏畫／方向不同），再用另一色補答案線。

## 成長筆記（notes.html）

`/learn-notes <id|all>`（第 9 步，`/learn --notes false` 可跳過）：agent 依 `rules/notes.md` 從 `analysis.json` + `_overview.json` 擷取每站 3–8 條「看完才知道的」觀念（`concept`）／技巧（`skill`）／體悟（`insight`），寫 `<站>/notes.json`（`schemas/notes.schema.json`；`text` ≤ 80 字、每條必有 `seg_id`），`validate.py notes` 檢查 schema 與 `seg_id` 存在於 `analysis.json`。`scripts/notes.py` 彙整成 `workspace/notes.html`：站依產出時間新到舊，每條連回 `plan.html#<vid>-s<seg_id>`；頂部搜尋列跟 atlas / listen 同一份（`_search.html.j2`，卡片 = `.st` 站，`data-category` 來自 atlas region，「任意」條件另會搜 `data-text` = 該站所有筆記內文），留／刪篩選透過 `extra_ok(el)` 併進搜尋（全站筆記被篩掉就整站隱藏）。
混合式取捨：agent 擷取候選，使用者在頁面上按「留／刪」（localStorage，key = `<vid>:<note id>`）、篩選「只看留下的」；「匯出」下載 `notes.keep.json`，放到 `workspace/` 後 `notes.py` 把它當預設狀態（`data-st`），瀏覽器裡的操作再蓋上去。使用者要改內容就改 `notes.json` 重跑 `notes.py`。

## Skill 拆分

`skills/` 下（`.claude/skills` 是它的 symlink）：`/learn` 總指揮 + 十個階段 skill + 工具 skill `/learn-publish`（發佈到 Cloudflare Pages）、`/learn-digest`（PACER 消化工作單與對話式消化）、`/learn-canvas`（把 analysis.json 逐段畫成 tldraw 白板，需另裝 `tldraw-offline` skill）
十個階段：`/learn-estimate`、`/learn-fetch`、`/learn-segment`、`/learn-shot`、`/learn-analyze`、`/learn-render`、`/learn-atlas`、`/learn-narrate`、`/learn-notes`、`/learn-listen`。
**analyze 一定在 subagent 裡跑**（`/learn` 用 Agent tool 派出去）：逐段分析會累積 150–200k context，留在主對話會讓 render / atlas / narrate 每輪重送。subagent 只回進度兩行與一句摘要，不回 analysis 內容。
`/learn` 第 0 步一定先跑 estimate 並把分階段 + 總和給使用者看。
共用慣例：`/learn-<stage> <video_id> [--force] [--vision ...]`；預設不覆蓋既有輸出。`/learn` 另有 `--from <stage>`、`--dry-run`。

誰做什麼：estimate / fetch / shot / render 是 `scripts/*.py`（確定性）；segment / analyze / overview 由 agent 依 `rules/*.md` 產 JSON，再過 `scripts/validate.py`。

設計原則：
- 多支影片可以同時跑：所有中間檔都在各自的影片資料夾裡（`fetch` 用 `.tmp-<id>` 暫存、標題撞名自動加 `(2)`）；workspace 層級的共用檔 `atlas.json`、`dist/` 靠 `common.locked()` 的檔案鎖，`atlas.json` 一律用 `--merge` patch 而不是整份覆寫；`input.yaml` 由 agent 合併寫入。
- 每個階段的輸入/輸出落地成檔案（transcript JSON、segments JSON、截圖目錄），讓中間結果可重用、失敗可從中斷點重跑，不必重抓影片。
- 每支影片獨立資料夾、獨立 `plan.html` 與 `_overview.json`（預設不合併）；使用者明確要求時才用 `render.py --combined` 合併多支。
- skill 定義（給 agent 的指令）與程式碼分開放：skill 負責「何時、如何呼叫」，程式負責確定性的抓取/切段/截圖；LLM 判斷（分段語意、術語、說明）留在 analyze 階段。

## 兩種使用模式

同一份 repo 既可 clone 進來直接用（`.claude/skills` 是 `skills/` 的 symlink），也可當 Claude Code plugin 安裝（plugin 名 `pacer`，marketplace 名 `thewaytolearn`；指令前綴 `/pacer:`）。SKILL.md 裡所有指令都寫成 `uv run --project "${CLAUDE_PLUGIN_ROOT:-.}" "${CLAUDE_PLUGIN_ROOT:-.}/scripts/<x>.py"`，兩種模式都能跑。
- workspace：`$LEARN_WORKSPACE` > 目前目錄 `./workspace/`
- 規則覆寫：`$LEARN_RULES` > 目前目錄 `./learn.rules/`（同名檔案覆蓋 `rules/`、`config/`、`templates/`），`scripts/paths.py` 印出實際生效路徑
- 改 skill 就改 `skills/<name>/SKILL.md`

## 常用指令

（尚無。加入 build / test / lint 指令後在此補上，含「跑單一測試」的方式。）
