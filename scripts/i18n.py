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
        "atlas": "學習地圖", "region": "主題區", "no_links": "這一站還沒有連到其他站。",
        "h_prereq": "1. 前情提要 & Outline", "prereq_box": "看之前需要先懂", "outline": "Outline",
        "h_reasoning": "2. YouTuber 的思維推導", "subs": "字幕", "stage": "階段", "est": "預估", "actual": "實際",
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
        # atlas
        "atlas_title": "學習地圖 · Atlas", "atlas_h1": "🗺 學習地圖", "n_wp": "{n} 站", "n_region": "{n} 個主題區",
        "n_route": "{n} 條 route", "updated": "更新於 {t}", "h_map": "地圖",
        "route_legend": "箭頭：<span><b>先看</b> A → B：先看 A 再看 B</span><span><b>深入</b> B 深入 A 的主題</span><span><b>對照</b> 兩者對照</span><span><b>應用</b> B 把 A 用到場景</span><span><b>相關</b> 無方向</span>· 點縮圖節點看這一站的重點，視窗裡可再開學習規劃",
        "map_cap": "學習地圖", "h_stations": "各站", "n_seg": "{n} 段", "terms": "術語：", "terms_total": "…共 {n} 個",
        "search_ph": "搜尋作者、標題、分類…", "search_hint": "按空白鍵或 Enter 加下一個條件；條件之間是 AND",
        "f_author": "作者", "f_category": "分類", "f_title": "標題", "f_any": "任意",
        "showing": "顯示 {n} / {total} 站", "no_match": "沒有符合條件的站。", "clear_all": "清除全部",
        "more_info": "詳細", "watch_yt": "在 YouTube 看",
        "err_ok": "✓ 0",
        "err_tip": "作者「{ch}」的勘誤：{v} 支影片共 {seg} 段，其中 {w} 處確定錯誤／已過時、{d} 處見仁見智",
        "err_tip_ok": "作者「{ch}」：{v} 支影片共 {seg} 段，目前沒有勘誤",
        "err_legend": "作者勘誤數（該作者所有站加總）：",
        "open_plan": "開啟學習規劃 →", "unplaced": "未分區", "unplaced_desc": "還沒歸入主題區的站。",
        "unplaced_hint": "跑 <code>/learn-atlas</code> 決定它們的 route 與 region。",
        # atlas：各站的 pipeline 進度與「繼續做」的 prompt
        "progress": "進度", "stage_of": "{n}/{total}",
        "stg_estimate": "估成本", "stg_fetch": "抓字幕", "stg_segment": "切段", "stg_shot": "截圖",
        "stg_analyze": "逐段分析", "stg_render": "學習規劃", "stg_atlas": "上地圖", "stg_narrate": "聽力版",
        "st_done": "完成", "st_todo": "還沒做", "st_partial": "沒做完", "st_skip": "不需要", "st_running": "進行中",
        "n_no_shots": "這支不需要截圖", "n_no_clips": "還沒處理原音：沒有挑原聲片段",
        "n_no_trans": "原聲片段還沒寫翻譯", "n_no_dub": "還沒做翻譯配音（🗣 那一軌）",
        "n_building": "聽力版正在合成", "n_all_done": "八個階段都做完了",
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
        "route_prerequisite": "先看", "route_deepens": "深入", "route_contrasts": "對照", "route_applies": "應用", "route_related": "相關",
    },
    "en": {
        "click_to_enlarge": "⤢ Click to enlarge", "zoom_out": "Zoom out (-)", "zoom_in": "Zoom in (+)", "fit": "Fit (F)",
        "reset": "Actual size (1)", "close": "Close (Esc)", "prev": "Previous (←)", "next": "Next (→)",
        "mindmap_edge_tip": "Parent → child: the segment contains the terms first defined in it",
        "plan_title_suffix": "Learning plan", "plan_meta": "Learning plan · {n} video(s) · generated {t}",
        "atlas": "Learning atlas", "region": "Region", "no_links": "This station is not linked to any other yet.",
        "h_prereq": "1. Prerequisites & Outline", "prereq_box": "What you need before watching", "outline": "Outline",
        "h_reasoning": "2. The YouTuber's line of reasoning", "subs": "subtitles", "stage": "Stage", "est": "Estimated", "actual": "Actual",
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
        "atlas_title": "Learning Atlas", "atlas_h1": "🗺 Learning Atlas", "n_wp": "{n} station(s)", "n_region": "{n} region(s)",
        "n_route": "{n} route(s)", "updated": "updated {t}", "h_map": "Map",
        "route_legend": "Arrows: <span><b>first</b> A → B: watch A before B</span><span><b>deepens</b> B goes deeper into A</span><span><b>contrasts</b> the two compared</span><span><b>applies</b> B applies A to a scenario</span><span><b>related</b> undirected</span>· click a thumbnail node for that station's highlights; the dialog links to its plan",
        "map_cap": "Learning atlas", "h_stations": "Stations", "n_seg": "{n} segments", "terms": "Terms: ", "terms_total": "… {n} in total",
        "search_ph": "Search author, title, category…", "search_hint": "Press space or Enter to add another condition; conditions are ANDed",
        "f_author": "Author", "f_category": "Category", "f_title": "Title", "f_any": "Any",
        "showing": "Showing {n} of {total}", "no_match": "No station matches these conditions.", "clear_all": "Clear all",
        "more_info": "Details", "watch_yt": "Watch on YouTube",
        "err_ok": "✓ 0",
        "err_tip": "{ch}: {w} wrong/outdated and {d} debatable across {seg} segments in {v} video(s)",
        "err_tip_ok": "{ch}: no corrections across {seg} segments in {v} video(s)",
        "err_legend": "Author corrections (totalled over that author's stations): ",
        "open_plan": "Open learning plan →", "unplaced": "Unassigned", "unplaced_desc": "Stations not yet placed in a region.",
        "unplaced_hint": "Run <code>/learn-atlas</code> to decide their routes and region.",
        "progress": "Progress", "stage_of": "{n}/{total}",
        "stg_estimate": "Estimate", "stg_fetch": "Transcript", "stg_segment": "Segments", "stg_shot": "Frames",
        "stg_analyze": "Analysis", "stg_render": "Plan", "stg_atlas": "On the map", "stg_narrate": "Audio lesson",
        "st_done": "done", "st_todo": "not started", "st_partial": "incomplete", "st_skip": "not needed", "st_running": "running",
        "n_no_shots": "no frames needed for this one", "n_no_clips": "no original-audio clips picked yet",
        "n_no_trans": "the clips have no translation yet", "n_no_dub": "no dubbed track yet (the 🗣 one)",
        "n_building": "the audio lesson is being built", "n_all_done": "all eight stages are done",
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
        "route_prerequisite": "first", "route_deepens": "deepens", "route_contrasts": "contrasts", "route_applies": "applies", "route_related": "related",
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
