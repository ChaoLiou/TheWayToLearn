import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import common
import pytest
from common import fmt_dur, fmt_ts, locked, save_json, video_dir, video_id


@pytest.mark.parametrize("u", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ?t=10",
    "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    "dQw4w9WgXcQ",
])
def test_video_id(u):
    assert video_id(u) == "dQw4w9WgXcQ"


def test_video_id_bad():
    with pytest.raises(ValueError):
        video_id("not a url or id")


def test_blog_url_gets_stable_id():
    a = video_id("https://example.com/posts/attention/")
    b = video_id("http://www.example.com/posts/attention#comments")
    assert a == b and a.startswith("b_") and len(a) == 11
    assert video_id(a) == a                      # 裸 id 原樣回傳
    assert common.is_blog(a) and not common.is_blog("dQw4w9WgXcQ")
    assert common.is_blog({"video_id": "xxxxxxxxxxx", "source": "blog"})
    assert video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_fmt():
    assert fmt_ts(65) == "1:05"
    assert fmt_ts(3661) == "1:01:01"
    assert fmt_dur(45) == "45s"
    assert fmt_dur(3700) == "1h01m"


def test_title_dirname():
    from common import title_dirname
    assert title_dirname('What Is X? "A/B" | C: D...') == "What Is X A B C D"
    assert len(title_dirname("x" * 200)) == 80


def test_title_dirname_cuts_at_word_boundary():
    from common import title_dirname
    t = "Content Security Policy explained how to protect against Cross Site Scripting (XSS) and more"
    d = title_dirname(t)
    assert len(d) <= 80 and not d.endswith("(") and d.endswith(("Scripting", "(XSS)"))


def test_step_line_format():
    from common import STEPS, step_line, step_no
    n = len(STEPS)
    assert step_no("segment") == 3
    first = step_line("segment", "9 段")
    assert first.startswith(f"[3/{n}] ✔ segment 切段 完成  ●●●" + "○" * (n - 3)) and "9 段" in first
    assert f"下一步 [4/{n}] shot" in first
    last = step_line("listen")
    assert last.startswith(f"[{n}/{n}]") and "全部完成" in last and "下一步" not in last
    assert "≥ 2 站" in step_line("render") and "選配" in step_line("atlas")
    assert step_no("digest") == 6 and "--digest false" in step_line("analyze")


def test_options_lists_params_per_skill(capsys, tmp_path):
    import options
    options.main(["learn", "--set", "shots=none", "--workspace", str(tmp_path)])
    out = capsys.readouterr().out
    assert "--shots  = none （你已指定）" in out
    assert "--vision" in out and "要調整哪一個" in out
    assert "--shots" not in out.split("可調：")[1]
    options.main(["learn-atlas", "--workspace", str(tmp_path)])
    assert "沒有可調參數" in capsys.readouterr().out


def test_narrate_helpers(tmp_path):
    import narrate
    a, b = tmp_path / "a.mp3", tmp_path / "it's.mp3"
    assert narrate.concat_file([a, b]).splitlines()[1].endswith("it'\\''s.mp3'")
    tl = [{"seg_id": 1, "seg_title": "A", "at": 0.0}, {"seg_id": 1, "seg_title": "A", "at": 3.0},
          {"seg_id": 2, "seg_title": "B", "at": 9.0}]
    assert narrate.chapters_of(tl) == [{"seg_id": 1, "title": "A", "at": 0.0}, {"seg_id": 2, "title": "B", "at": 9.0}]
    assert narrate.voice_for("zh-TW").startswith("zh-TW") and narrate.voice_for("en").startswith("en-")


def test_clip_lines_merge_and_snap():
    import narrate
    ev = [{"start": 10.0, "duration": 2.0, "text": "hello"},
          {"start": 12.0, "duration": 1.5, "text": "there"},
          {"start": 13.5, "duration": 3.0, "text": "this is a much longer caption line here"},
          {"start": 30.0, "duration": 2.0, "text": "outside"}]
    lines = narrate.clip_lines(ev, 10.0, 17.0, 100.0)
    assert len(lines) == 1 and lines[0]["at"] == 100.0          # 短句併成一行，範圍外的不收
    assert lines[0]["text"].startswith("hello there this is")
    long_ev = [{"start": i, "duration": 1.0, "text": "x" * 40} for i in range(6)]
    assert len(narrate.clip_lines(long_ev, 0.0, 6.0, 0.0)) == 6  # 太長就不併
    assert narrate.snap(ev, 10.4, 16.0) == (10.0, 16.5)


def test_video_dir_avoids_title_collision(tmp_path):
    """不同影片、同一個標題 → 各自一個資料夾，不會互相覆寫。"""
    a = video_dir("aaaaaaaaaaa", tmp_path, title="Same Title")
    (a / "meta.json").write_text(json.dumps({"video_id": "aaaaaaaaaaa"}), encoding="utf-8")
    b = video_dir("bbbbbbbbbbb", tmp_path, title="Same Title")
    assert a.name == "Same Title" and b.name == "Same Title (2)"
    # 再叫一次要回到原本那支的資料夾
    assert video_dir("aaaaaaaaaaa", tmp_path, title="Same Title") == a


def test_write_text_is_atomic(tmp_path):
    p = tmp_path / "x.json"
    save_json(p, {"a": 1})
    assert json.loads(p.read_text()) == {"a": 1}
    assert not list(tmp_path.glob(".*tmp"))  # 暫存檔要收乾淨


def test_locked_is_reentrant_across_calls(tmp_path):
    lock = tmp_path / ".x.lock"
    with locked(lock, "x"):
        pass
    with locked(lock, "x"):  # 前一次要有放開
        pass


def test_dub_lines_and_voice():
    import narrate

    assert narrate.dub_voice_for("zh-TW", "zh-TW-HsiaoChenNeural") == "zh-TW-YunJheNeural"
    # 講解已經用了配音的預設聲音，就換成講解的預設聲，兩個聲音不會撞在一起
    assert narrate.dub_voice_for("zh-TW", "zh-TW-YunJheNeural") == "zh-TW-HsiaoChenNeural"
    lines = narrate.dub_lines("他說 partition 是關鍵。" + "很長的一句話，" * 12 + "結束。")
    assert lines[0] == "他說 partition 是關鍵。"
    assert all(len(x) <= narrate.DUB_MAX for x in lines)      # 太長的句子會再斷
    assert "".join(lines).replace("", "") .startswith("他說 partition")
    assert narrate.dub_lines("好。這句話夠長了可以自己成一句話。") == ["好。這句話夠長了可以自己成一句話。"]  # 太短就併回前一句
    # 句號在引號裡：收尾的「」」要跟著前一句，不能單獨成一句（edge-tts 對純標點回 NoAudioReceived）
    quoted = narrate.dub_lines("我就說：「你能建立一個新的範例專案嗎？」就是建一個可以展示的 demo 專案。")
    assert quoted == ["我就說：「你能建立一個新的範例專案嗎？」", "就是建一個可以展示的 demo 專案。"]
    assert all(__import__("re").search(r"\w", x) for x in narrate.dub_lines("他問：「好嗎？」"))


# ---------- --ui-lang：同一份 workspace 產多語系頁面 ----------

def test_ui_lang_override_beats_station_meta():
    """--ui-lang 要蓋過各站 meta.json 的 output_lang，否則同一份 workspace 產不出第二種語言。"""
    import common
    meta = {"output_lang": "zh-TW"}
    try:
        assert common.station_lang(meta) == "zh-TW"
        assert common.ui_lang_override() is None
        common.set_ui_lang("en")
        assert common.ui_lang_override() == "en"
        assert common.station_lang(meta) == "en"          # 蓋過 meta
        assert common.default_output_lang() == "en"       # 也蓋過 settings / $LEARN_LANG
        common.set_ui_lang("")                            # 空字串 = 取消
        assert common.ui_lang_override() is None
        assert common.station_lang(meta) == "zh-TW"
    finally:
        common.set_ui_lang(None)


def test_ui_lang_switches_every_page(tmp_path):
    """五個產頁的 script 都要吃 --ui-lang，而且只換介面字串、不動內文。"""
    import shutil

    import common
    import render
    ws = tmp_path / "ws"
    shutil.copytree(Path(__file__).parent / "fixtures/ws", ws)
    try:
        common.set_ui_lang("en")
        render.main(["--workspace", str(ws), "--ui-lang", "en"])
        h = (ws / "測試影片 A: B" / "plan.html").read_text(encoding="utf-8")
        assert 'lang="en"' in h and "1. Outline" in h and "Builds on" in h
        assert "承上" not in h
        assert "測試影片" in h           # 內文（標題）沒有被翻譯
    finally:
        common.set_ui_lang(None)
