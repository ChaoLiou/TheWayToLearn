import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import pytest
from common import fmt_dur, fmt_ts, video_id


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
        video_id("https://example.com")


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
    assert step_no("segment") == 3 and len(STEPS) == 8
    first = step_line("segment", "9 段")
    assert first.startswith("[3/8] ✔ segment 切段 完成  ●●●○○○○○") and "9 段" in first
    assert "下一步 [4/8] shot" in first
    last = step_line("narrate")
    assert last.startswith("[8/8]") and "全部完成" in last and "下一步" not in last
    assert "≥ 2 站" in step_line("render") and "選配" in step_line("atlas")


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
