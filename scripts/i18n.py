"""HTML 固定文字的語言表。內文語言由各站 meta.json 的 output_lang 決定（/learn 依對話語言設定）。

新增語言：在 STRINGS 加一個 key，缺的字串會 fallback 到 zh-TW。
"""
from __future__ import annotations

DEFAULT_LANG = "zh-TW"

STRINGS: dict[str, dict[str, str]] = {
    "zh-TW": {
        # 共用
        "click_to_enlarge": "⤢ 點擊放大", "zoom_out": "縮小 (-)", "zoom_in": "放大 (+)", "fit": "最佳視角 (F)",
        "reset": "原始大小 (1)", "close": "關閉 (Esc)", "prev": "上一張 (←)", "next": "下一張 (→)",
        "mindmap_edge_tip": "上層 → 下層：段落包含在此段首次定義的術語",
        # plan
        "plan_title_suffix": "學習規劃", "plan_meta": "學習規劃 · {n} 支影片 · 產生於 {t}",
        "atlas": "文字說明列表", "region": "主題區", "no_links": "這一站還沒有連到其他站。",
        "h_prereq": "1. 前情提要 & Outline", "prereq_box": "看之前需要先懂", "outline": "Outline",
        "h_reasoning": "2. YouTuber 的思維推導", "subs": "字幕", "stage": "階段", "est": "預估", "actual": "實際",
        "h_reasoning_blog": "2. 作者的思維推導", "blog_link": "原文", "article_lang": "文章語言", "reading": "閱讀約",
        "source_blog": "文章",
        "chain_cap": "推理鏈", "chain_desc_summary": "推理鏈的文字說明",
        "chain_desc": "每個節點是一段，箭頭上的字是該段留給下一段的線索。hover 節點看該段摘要、hover 箭頭文字看完整線索。",
        "h_segments": "3. 逐段說明", "author_says": "作者說：", "builds_on": "承上", "reasoning": "推理", "ai_note": "AI 補充",
        "more": "更多說明", "related": "相關", "related_terms": "相關術語", "source_seg": "出處：第 {id} 段「{title}」",
        "lvl_wrong": "確定錯誤／已過時", "lvl_debatable": "見仁見智", "evidence": "依據", "leads_to": "留給下一段",
        "h_summary": "4. 總結", "issues_sum": "勘誤總整理", "lvl_debatable_long": "見仁見智（取決於版本或情境）",
        "col_seg": "段落", "col_quote": "原話（transcript 逐字）", "col_note": "說明",
        "mindmap_desc_summary": "Mindmap 的文字說明", "mindmap_desc": "根 = 主題；第二層 = 影片；第三層 = 段落；第四層 = 該段首次定義的術語。",
        "term_graph": "術語關聯圖", "term_graph_desc_summary": "術語關聯圖的文字說明",
        "term_graph_desc": "節點顏色 = 首次定義的段落（見上方圖例）；箭頭 A → B 表示 A 的定義牽涉 B，線上文字是關係；雙箭頭且標籤前有 ⇄ = 兩者定義互相引用。hover 節點看定義、hover 線上文字看完整關係。",
        "h_next": "5. 推薦三個下一步", "yt_search": "YouTube 搜尋：",
        "listen": "🎧 聽力版", "listen_hint": "TTS 講解與作者原聲交錯；點章節可跳。",
        "chapters": "章節", "clip_mark": "原聲",
        "listen_building": "🎧 聽力版產生中…", "listen_building_hint": "第 8 步正在合成語音與原聲，完成後這裡會自動出現播放器與講稿；你可以先往下讀。",
        "check_now": "檢查是否完成", "listen_failed": "聽力版產生失敗，看終端機的錯誤訊息。",
        "open_script": "🎤 開啟講稿", "kara_hint": "邊聽邊看逐句講稿，點任一句從那裡開始",
        "mode_orig": "🎙 原聲", "mode_dub": "🗣 翻譯",
        "dub_hint": "切換原聲片段：作者原音／另一個聲音唸翻譯（快捷鍵 D）", "orig_text": "原文",
        "script": "講稿", "speed": "速度", "restart": "⏮ 重頭", "play": "▶ 播放", "pause": "⏸ 暫停", "back_to_now": "回到目前",
        "leads_to_tip": "留給下一段：", "term_undefined": "（本片未單獨定義）", "sep": "、",
        # listen（podcast 頁）與 notes（成長筆記）
        "nav_listen": "🎧 聽", "nav_notes": "📝 成長筆記", "nav_atlas": "📄 文字說明",
        "listen_title": "聽 · Podcast", "listen_h1": "🎧 聽",
        "listen_sub": "新的在上面。點一集就開始播；字幕與講稿在底部播放器。",
        "n_episode": "{n} 集", "total_len": "共 {t}",
        "ep_produced": "產生於 {t}", "ep_resume": "上次聽到 {t}", "ep_done": "✓ 聽完了", "ep_new": "NEW",
        "ep_plan": "📄 文字說明", "ep_notes": "📝 筆記", "ep_dub": "🗣 有翻譯版",
        "no_episodes": "還沒有聽力版。跑 <code>/learn-narrate &lt;id&gt;</code> 產生 lesson.mp3。",
        "p_prev": "上一集", "p_next": "下一集", "p_back": "退 15 秒", "p_fwd": "進 15 秒",
        "p_cc": "字幕", "p_cc_off": "字幕（未載入）", "p_now_playing": "正在播", "p_pick": "從上面挑一集開始聽",
        "cc_loading": "載入講稿中…", "cc_missing": "這一集沒有講稿檔（captions.js），重跑 listen.py。",
        "notes_title": "成長筆記", "notes_h1": "📝 成長筆記",
        "notes_sub": "每一篇學習素材留下的觀念與技巧。新的在上面；每條都連回原本的段落。",
        "n_notes": "{n} 條", "n_kept": "留下 {n}", "n_dropped": "刪掉 {n}",
        "notes_all": "全部", "notes_kept": "只看留下的", "notes_undecided": "還沒決定", "notes_dropped": "已刪",
        "kind_concept": "觀念", "kind_skill": "技巧", "kind_insight": "體悟",
        "note_keep": "留", "note_drop": "刪", "note_undo": "還原", "note_seg": "第 {id} 段 →",
        "notes_export": "⬇ 匯出留／刪狀態", "notes_export_hint": "下載 notes.keep.json，放到 workspace/ 後重跑 notes.py 就會記住",
        "notes_reset": "清掉本機狀態",
        "no_notes": "還沒有筆記。對某一站說「幫我做成長筆記」或跑 <code>/learn-notes &lt;id&gt;</code>。",
        "notes_open_plan": "開啟文字說明", "notes_listen": "🎧 聽這集",
        # digest（PACER 消化工作單）
        "nav_digest": "🍽 消化", "digest_title": "消化工作單", "digest_h1": "🍽 消化工作單",
        "digest_sub": "讀完只是消費；留下來的靠消化。每筆資訊已標好類別與該做的事，做完就灰掉。",
        "d_today": "今天", "d_due_cards": "到期回想 {n} 張", "d_due_rehearse": "待演練 {n} 筆", "d_backlog": "未做：P {p} · A {a} · C {c}",
        "d_start_recall": "開始回想", "d_nothing_today": "今天沒有到期的。去做上面的練習或畫地圖。",
        "d_unread_skip": "未讀 {n} 站不計", "d_unread": "未讀", "d_read_on": "已讀 {t}",
        "d_read_btn": "📖 讀完了，開始消化", "d_unread_btn": "標回未讀",
        "d_unread_hint": "工作單只是準備。先開文字說明讀完，按這裡才進消化期；沒讀的站不算積欠。",
        "d_all": "全部", "d_todo": "只看未做", "d_done": "已做",
        "d_export": "⬇ 匯出進度", "d_export_hint": "下載 digest.state.json，放到 workspace/ 後重跑 digest.py 就會記住；/learn 也靠它算積欠",
        "d_export_anki": "⬇ 匯出 Anki (tsv)", "d_reset": "清掉本機狀態",
        # 轉移到 Claude Code 做（對話式消化）
        "d_cc_title": "🤖 想要有人帶著做？到 Claude Code 裡消化",
        "d_cc_body": "網頁適合自己翻卡與打勾；P／A／C／E 需要一問一答。複製下面的 prompt 貼進 Claude Code，它會一次一題、用填空題帶你做，做完自動寫回進度。",
        "d_cc_steps": "① 先按「⬇ 匯出進度」，把 digest.state.json 放到 workspace/（不然 Claude Code 看不到你在網頁上做過的）　② 複製 prompt　③ 貼進 Claude Code",
        "d_cc_today": "今天該做什麼", "d_cc_due": "帶我做所有到期的", "d_cc_station": "🤖 帶我做這站",
        "d_cc_kind": "🤖 帶我做這類", "d_cc_item": "🤖 帶我做這筆",
        "d_cc_hint": "複製 prompt，貼進 Claude Code",
        "d_kind_P": "P 程序", "d_kind_A": "A 類比", "d_kind_C": "C 概念", "d_kind_E": "E 證據", "d_kind_R": "R 參考",
        "d_act_P": "練習", "d_act_A": "批判類比", "d_act_C": "畫地圖", "d_act_E": "存＋演練", "d_act_R": "存＋回想",
        "d_why_P": "怎麼做的資訊：盡早在真實情境用，硬背會白費。", "d_why_A": "跟已知很像的資訊：找出哪裡像、哪裡不像、何時失效，新知識才接得上舊網路。",
        "d_why_C": "是什麼／為什麼的資訊：知識是網路不是清單，自己畫出概念間的連結。",
        "d_why_E": "支持概念的細節：當下存起來，之後想它證明了什麼、你會怎麼用。", "d_why_R": "瑣碎但之後要查的：存進 flashcard，間隔重複回想。",
        "d_steps": "步驟", "d_task": "今天就做", "d_done_btn": "做完了", "d_undo": "還原", "d_note_ph": "做了什麼、結果如何（選填）",
        "d_new": "新", "d_known": "像", "d_alike": "哪裡像", "d_unlike": "哪裡不像", "d_breaks": "什麼情況下失效", "d_show_key": "對照 AI 版",
        "d_mapped": "已畫進地圖", "d_show_relations": "對答案", "d_relations_hint": "先自己畫完再看：這個概念連到——",
        "d_stored": "已存", "d_supports": "證明", "d_rehearse": "演練", "d_rehearsed": "演練過", "d_answer_ph": "你的回答",
        "d_flip": "顯示答案", "d_forgot": "忘了", "d_hard": "難", "d_easy": "會", "d_next_due": "下次 {t}", "d_new_card": "新卡", "d_recall_now": "現在回想",
        "d_session_done": "這輪回想完了。", "d_card_n": "{i} / {n}",
        "d_no_stations": "還沒有工作單。對某一站說「幫我做消化工作單」或跑 <code>/learn-digest &lt;id&gt;</code>。",
        "d_open_plan": "開啟文字說明", "d_seg": "第 {id} 段 →",
        "d_tag_hint": "點開看消化工作單",
        # atlas
        "atlas_title": "文字說明", "atlas_h1": "📄 文字說明", "n_wp": "{n} 站", "n_region": "{n} 個主題區",
        "updated": "更新於 {t}",
        "h_stations": "各站", "n_seg": "{n} 段", "terms": "術語：", "terms_total": "…共 {n} 個",
        "search_ph": "搜尋作者、標題、分類…", "search_hint": "按空白鍵或 Enter 加下一個條件；條件之間是 AND",
        "f_author": "作者", "f_category": "分類", "f_title": "標題", "f_any": "任意",
        "showing": "顯示 {n} / {total} 站", "no_match": "沒有符合條件的站。", "clear_all": "清除全部",
        "more_info": "詳細", "watch_yt": "在 YouTube 看",
        "err_ok": "✓ 0",
        "err_tip": "這支影片共 {seg} 段，其中 {w} 處確定錯誤／已過時、{d} 處見仁見智，點看詳細",
        "err_tip_ok": "這支影片共 {seg} 段，目前沒有勘誤",
        "err_legend": "勘誤件數（這支影片）：",
        "err_title": "勘誤",
        "open_plan": "開啟學習規劃 →", "unplaced": "未分區", "unplaced_desc": "還沒歸入主題區的站。",
        "unplaced_hint": "跑 <code>/learn-atlas</code> 決定它們的 route 與 region。",
        # atlas：各站的 pipeline 進度與「繼續做」的 prompt
        "progress": "進度", "stage_of": "{n}/{total}",
        "stg_estimate": "估成本", "stg_fetch": "抓字幕", "stg_segment": "切段", "stg_shot": "截圖",
        "stg_analyze": "逐段分析", "stg_render": "學習規劃", "stg_atlas": "連結各站", "stg_narrate": "聽力版",
        "stg_digest": "消化工作單", "stg_listen": "podcast 頁",
        "st_done": "完成", "st_todo": "還沒做", "st_partial": "沒做完", "st_skip": "不需要", "st_running": "進行中",
        "n_no_shots": "這支不需要截圖", "n_no_lesson": "沒有聽力版，podcast 頁不會列這站", "n_no_clips": "還沒處理原音：沒有挑原聲片段",
        "n_no_trans": "原聲片段還沒寫翻譯", "n_no_dub": "還沒做翻譯配音（🗣 那一軌）",
        "n_building": "聽力版正在合成", "n_all_done": "十個階段都做完了",
        "next_step": "▸ 繼續做", "next_q": "要往下做到哪裡？",
        "next_hint": "選一個 → 複製 prompt → 貼到 Claude Code 執行",
        "copy_prompt": "複製 prompt", "copied": "✓ 已複製",
        "np_to": "做到「{stage}」", "np_only": "只做「{stage}」",
        "np_steps": "包含 {n} 步：{list}",
        "np_lead": "請幫「{title}」這支影片繼續做完學習 pipeline（video_id: {id}）。依序執行，每一步跑完再跑下一步，中途不用問我：",
        "np_tail": "規則都在 rules/ 底下，照著做；每一步的產出要過 scripts/validate.py。",
        "np_note_clips": "narrate 這一步要先補原聲：依 rules/narration.md 幫每段在 segments.json 加 clips（≤150 秒的段落直接整段）與 translation（繁體中文、術語保留英文原文、寫給耳朵的短句），再把 narration.json 補上導聽與 clip block，最後跑 narrate.py --force。",
        "np_note_trans": "narrate 這一步要先幫 segments.json 既有的 clips 補上 translation（繁體中文、術語保留英文原文），再跑 narrate.py --force 產出翻譯配音那一軌。",
        "np_note_dub": "這一步只要重跑 narrate.py 就會補上翻譯配音那一軌（lesson.dub.mp3）。",
        "np_redo": "重做「{stage}」", "np_redo_desc": "已經做完了，重跑會覆蓋舊的產出",
        "ago_now": "剛剛", "ago_today": "今天", "ago_h": "{n} 小時前",
        "ago_d": "{n} 天前", "ago_mo": "{n} 個月前", "ago_y": "{n} 年前",
        "route_next": "接著看", "route_related": "相關",
    },
    "en": {
        "click_to_enlarge": "⤢ Click to enlarge", "zoom_out": "Zoom out (-)", "zoom_in": "Zoom in (+)", "fit": "Fit (F)",
        "reset": "Actual size (1)", "close": "Close (Esc)", "prev": "Previous (←)", "next": "Next (→)",
        "mindmap_edge_tip": "Parent → child: the segment contains the terms first defined in it",
        "plan_title_suffix": "Learning plan", "plan_meta": "Learning plan · {n} video(s) · generated {t}",
        "atlas": "All write-ups", "region": "Region", "no_links": "This station is not linked to any other yet.",
        "h_prereq": "1. Prerequisites & Outline", "prereq_box": "What you need before watching", "outline": "Outline",
        "h_reasoning": "2. The YouTuber's line of reasoning", "subs": "subtitles", "stage": "Stage", "est": "Estimated", "actual": "Actual",
        "h_reasoning_blog": "2. The author's line of reasoning", "blog_link": "Article", "article_lang": "language", "reading": "~read",
        "source_blog": "article",
        "chain_cap": "Reasoning chain", "chain_desc_summary": "Reasoning chain as text",
        "chain_desc": "Each node is a segment; the text on an arrow is the thread that segment leaves for the next. Hover a node for the segment summary, hover an arrow label for the full thread.",
        "h_segments": "3. Segment by segment", "author_says": "The author says: ", "builds_on": "Builds on", "reasoning": "Reasoning", "ai_note": "AI note",
        "more": "More", "related": "Related", "related_terms": "Related terms", "source_seg": "From segment {id} “{title}”",
        "lvl_wrong": "Wrong / outdated", "lvl_debatable": "Debatable", "evidence": "Evidence", "leads_to": "Leads to",
        "h_summary": "4. Summary", "issues_sum": "Corrections at a glance", "lvl_debatable_long": "Debatable (depends on version or context)",
        "col_seg": "Segment", "col_quote": "Verbatim quote (from transcript)", "col_note": "Note",
        "mindmap_desc_summary": "Mindmap as text", "mindmap_desc": "Root = topic; level 2 = video; level 3 = segment; level 4 = terms first defined in that segment.",
        "term_graph": "Term graph", "term_graph_desc_summary": "Term graph as text",
        "term_graph_desc": "Node colour = segment where the term is first defined (see legend). An arrow A → B means A's definition involves B; the label is the relation. A double arrow with ⇄ means both definitions reference each other. Hover a node for its definition, hover a label for the full relation.",
        "h_next": "5. Three recommended next steps", "yt_search": "Search YouTube: ",
        "listen": "🎧 Audio lesson", "listen_hint": "Narration interleaved with the author's own words; click a chapter to jump.",
        "chapters": "Chapters", "clip_mark": "original audio",
        "listen_building": "🎧 Audio lesson is being built…", "listen_building_hint": "Step 8 is synthesising narration and clips; the player and script will appear here when it is done. Read on meanwhile.",
        "check_now": "Check now", "listen_failed": "The audio lesson failed to build; see the terminal output.",
        "open_script": "🎤 Open script", "kara_hint": "Follow line by line; click any line to start there",
        "mode_orig": "🎙 Original", "mode_dub": "🗣 Translated",
        "dub_hint": "Switch the clips between the author's own voice and a second voice reading the translation (shortcut: D)",
        "orig_text": "Original",
        "script": "Script", "speed": "Speed", "restart": "⏮ Restart", "play": "▶ Play", "pause": "⏸ Pause", "back_to_now": "Back to current",
        "leads_to_tip": "Leads to: ", "term_undefined": "(not defined separately in this video)", "sep": ", ",
        "nav_listen": "🎧 Listen", "nav_notes": "📝 Growth notes", "nav_atlas": "📄 Write-ups",
        "listen_title": "Listen · Podcast", "listen_h1": "🎧 Listen",
        "listen_sub": "Newest first. Tap an episode to play; captions and the script live in the bottom player.",
        "n_episode": "{n} episode(s)", "total_len": "{t} total",
        "ep_produced": "produced {t}", "ep_resume": "resume at {t}", "ep_done": "✓ finished", "ep_new": "NEW",
        "ep_plan": "📄 Read", "ep_notes": "📝 Notes", "ep_dub": "🗣 dubbed version",
        "no_episodes": "No audio lessons yet. Run <code>/learn-narrate &lt;id&gt;</code> to build lesson.mp3.",
        "p_prev": "Previous", "p_next": "Next", "p_back": "Back 15s", "p_fwd": "Forward 15s",
        "p_cc": "Captions", "p_cc_off": "Captions (not loaded)", "p_now_playing": "Now playing", "p_pick": "Pick an episode above",
        "cc_loading": "Loading script…", "cc_missing": "No script file (captions.js) for this episode; rerun listen.py.",
        "notes_title": "Growth notes", "notes_h1": "📝 Growth notes",
        "notes_sub": "The concepts and skills each lesson left behind. Newest first; every note links back to its segment.",
        "n_notes": "{n} note(s)", "n_kept": "kept {n}", "n_dropped": "dropped {n}",
        "notes_all": "All", "notes_kept": "Kept only", "notes_undecided": "Undecided", "notes_dropped": "Dropped",
        "kind_concept": "concept", "kind_skill": "skill", "kind_insight": "insight",
        "note_keep": "Keep", "note_drop": "Drop", "note_undo": "Undo", "note_seg": "Segment {id} →",
        "notes_export": "⬇ Export keep/drop", "notes_export_hint": "Downloads notes.keep.json; put it in workspace/ and rerun notes.py to persist",
        "notes_reset": "Clear local state",
        "no_notes": "No notes yet. Ask for growth notes on a station or run <code>/learn-notes &lt;id&gt;</code>.",
        "notes_open_plan": "Open the write-up", "notes_listen": "🎧 Listen",
        # digest (PACER worklist)
        "nav_digest": "🍽 Digest", "digest_title": "Digest worklist", "digest_h1": "🍽 Digest worklist",
        "digest_sub": "Reading is only consumption; what stays depends on digestion. Every item is tagged with its type and the action to take — done items fade.",
        "d_today": "Today", "d_due_cards": "{n} card(s) due", "d_due_rehearse": "{n} to rehearse", "d_backlog": "Undone: P {p} · A {a} · C {c}",
        "d_start_recall": "Start recall", "d_nothing_today": "Nothing due today. Do a practice task or draw a map above.",
        "d_unread_skip": "{n} unread station(s) not counted", "d_unread": "Unread", "d_read_on": "Read {t}",
        "d_read_btn": "📖 Done reading, start digesting", "d_unread_btn": "Mark unread",
        "d_unread_hint": "The worksheet is only preparation. Read the write-up first, then press this to enter digestion; unread stations don't count as backlog.",
        "d_all": "All", "d_todo": "Undone only", "d_done": "Done",
        "d_export": "⬇ Export progress", "d_export_hint": "Downloads digest.state.json; put it in workspace/ and rerun digest.py to persist. /learn reads it for the backlog gate",
        "d_export_anki": "⬇ Export Anki (tsv)", "d_reset": "Clear local state",
        # hand off to Claude Code (conversational digestion)
        "d_cc_title": "🤖 Want to be walked through it? Digest inside Claude Code",
        "d_cc_body": "The page is good for flipping cards and ticking things off; P/A/C/E need back-and-forth. Copy a prompt below into Claude Code and it will walk you through one blank at a time, then write your progress back.",
        "d_cc_steps": "① Hit \u201c⬇ Export progress\u201d first and drop digest.state.json into workspace/ (otherwise Claude Code can't see what you did here)　② copy a prompt　③ paste it into Claude Code",
        "d_cc_today": "What should I do today", "d_cc_due": "Walk me through everything due", "d_cc_station": "🤖 Walk me through this station",
        "d_cc_kind": "🤖 Walk me through this type", "d_cc_item": "🤖 Walk me through this one",
        "d_cc_hint": "Copy the prompt, paste it into Claude Code",
        "d_kind_P": "P procedural", "d_kind_A": "A analogous", "d_kind_C": "C conceptual", "d_kind_E": "E evidence", "d_kind_R": "R reference",
        "d_act_P": "Practice", "d_act_A": "Critique", "d_act_C": "Map", "d_act_E": "Store + rehearse", "d_act_R": "Store + recall",
        "d_why_P": "How-to information: use it in a real context as early as possible; cramming is wasted.", "d_why_A": "Information that resembles what you know: find where it matches, where it doesn't, and when it breaks, so new knowledge attaches to the old network.",
        "d_why_C": "What/why information: knowledge is a network, not a list — draw the links between concepts yourself.",
        "d_why_E": "Details that support a concept: store now, later ask what it proves and how you would use it.", "d_why_R": "Trivial but look-up-later facts: put them in flashcards and recall with spaced repetition.",
        "d_steps": "Steps", "d_task": "Do today", "d_done_btn": "Done", "d_undo": "Undo", "d_note_ph": "What you did and the result (optional)",
        "d_new": "new", "d_known": "like", "d_alike": "Where alike", "d_unlike": "Where different", "d_breaks": "When it breaks", "d_show_key": "Compare with AI",
        "d_mapped": "Mapped", "d_show_relations": "Check answer", "d_relations_hint": "Draw yours first — this concept links to:",
        "d_stored": "Stored", "d_supports": "supports", "d_rehearse": "Rehearse", "d_rehearsed": "Rehearsed", "d_answer_ph": "Your answer",
        "d_flip": "Show answer", "d_forgot": "Forgot", "d_hard": "Hard", "d_easy": "Easy", "d_next_due": "Next {t}", "d_new_card": "New", "d_recall_now": "Recall now",
        "d_session_done": "Recall session finished.", "d_card_n": "{i} / {n}",
        "d_no_stations": "No worklist yet. Ask for a digest worklist on a station or run <code>/learn-digest &lt;id&gt;</code>.",
        "d_open_plan": "Open the write-up", "d_seg": "Segment {id} →",
        "d_tag_hint": "Open the digest worklist",
        "atlas_title": "Write-ups", "atlas_h1": "📄 Write-ups", "n_wp": "{n} station(s)", "n_region": "{n} region(s)", "updated": "updated {t}", "h_stations": "Stations", "n_seg": "{n} segments", "terms": "Terms: ", "terms_total": "… {n} in total",
        "search_ph": "Search author, title, category…", "search_hint": "Press space or Enter to add another condition; conditions are ANDed",
        "f_author": "Author", "f_category": "Category", "f_title": "Title", "f_any": "Any",
        "showing": "Showing {n} of {total}", "no_match": "No station matches these conditions.", "clear_all": "Clear all",
        "more_info": "Details", "watch_yt": "Watch on YouTube",
        "err_ok": "✓ 0",
        "err_tip": "{w} wrong/outdated and {d} debatable across {seg} segments in this video — click for details",
        "err_tip_ok": "No corrections across {seg} segments in this video",
        "err_legend": "Corrections in this video: ",
        "err_title": "Corrections",
        "open_plan": "Open learning plan →", "unplaced": "Unassigned", "unplaced_desc": "Stations not yet placed in a region.",
        "unplaced_hint": "Run <code>/learn-atlas</code> to decide their routes and region.",
        "progress": "Progress", "stage_of": "{n}/{total}",
        "stg_estimate": "Estimate", "stg_fetch": "Transcript", "stg_segment": "Segments", "stg_shot": "Frames",
        "stg_analyze": "Analysis", "stg_render": "Plan", "stg_atlas": "Link stations", "stg_narrate": "Audio lesson",
        "stg_digest": "Digest worklist", "stg_listen": "Podcast page",
        "st_done": "done", "st_todo": "not started", "st_partial": "incomplete", "st_skip": "not needed", "st_running": "running",
        "n_no_shots": "no frames needed for this one", "n_no_lesson": "no audio lesson, so the podcast page skips this one", "n_no_clips": "no original-audio clips picked yet",
        "n_no_trans": "the clips have no translation yet", "n_no_dub": "no dubbed track yet (the 🗣 one)",
        "n_building": "the audio lesson is being built", "n_all_done": "all ten stages are done",
        "next_step": "▸ Continue", "next_q": "How far do you want to take this one?",
        "next_hint": "pick one → copy the prompt → paste it into Claude Code",
        "copy_prompt": "Copy prompt", "copied": "✓ Copied",
        "np_to": "Up to \u201c{stage}\u201d", "np_only": "Just \u201c{stage}\u201d",
        "np_steps": "{n} step(s): {list}",
        "np_lead": "Please continue the learning pipeline for \u201c{title}\u201d (video_id: {id}). Run these in order, one after the other, without asking me in between:",
        "np_tail": "The rules live under rules/; each stage's output must pass scripts/validate.py.",
        "np_note_clips": "For narrate, first add the original-audio clips: following rules/narration.md, add clips to segments.json for every segment (segments \u2264150s go in whole) plus a translation (short spoken sentences, technical terms kept in English), add the cue-in and clip blocks to narration.json, then run narrate.py --force.",
        "np_note_trans": "For narrate, first add a translation to the existing clips in segments.json, then run narrate.py --force to build the dubbed track.",
        "np_note_dub": "This one only needs narrate.py rerun to add the dubbed track (lesson.dub.mp3).",
        "np_redo": "Redo \u201c{stage}\u201d", "np_redo_desc": "already done; rerunning overwrites the old output",
        "ago_now": "just now", "ago_today": "today", "ago_h": "{n}h ago",
        "ago_d": "{n}d ago", "ago_mo": "{n}mo ago", "ago_y": "{n}y ago",
        "route_next": "next", "route_related": "related",
    },
}


class Strings(dict):
    """S.key 取字串；S.f('key', n=3) 帶參數。缺字 fallback 到 zh-TW。"""

    def __init__(self, lang: str):
        base = dict(STRINGS[DEFAULT_LANG])
        base.update(STRINGS.get(lang, {}))
        super().__init__(base)
        self.lang = lang

    def __getattr__(self, k: str) -> str:
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e

    def f(self, k: str, **kw) -> str:
        return self[k].format(**kw)

    def ago(self, secs: float) -> str:
        """秒數 → 剛剛／n 小時前／n 天前／n 個月前／n 年前。"""
        h = int(secs // 3600)
        if h < 1:
            return self.ago_now
        return self.f("ago_h", n=h) if h < 24 else self.ago_days(h // 24)

    def ago_days(self, d: int) -> str:
        """天數 → 今天／n 天前／n 個月前／n 年前（只有日期、沒有時刻時用）。"""
        if d <= 0:
            return self.ago_today
        if d < 30:
            return self.f("ago_d", n=d)
        if d < 365:
            return self.f("ago_mo", n=max(1, d // 30))
        return self.f("ago_y", n=d // 365)

    def route(self, t: str) -> str:
        return self.get(f"route_{t}", t)


def norm_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANG
    lang = lang.strip()
    if lang.lower().startswith("zh"):
        return "zh-TW"
    base = lang.split("-")[0].lower()
    return base if base in STRINGS else lang
