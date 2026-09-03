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
