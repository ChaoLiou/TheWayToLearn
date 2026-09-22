import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import playlist
from common import is_playlist_url, load_input, playlist_id, playlist_index, video_id

PL = "https://www.youtube.com/playlist?list=PLabc123"
WATCH_IN_PL = "https://www.youtube.com/watch?v=aaaaaaaaaaa&list=PLabc123"
WATCH_2ND = "https://www.youtube.com/watch?v=bbbbbbbbbbb&list=PLabc123&index=2"

ENTRIES = [
    {"id": "aaaaaaaaaaa", "title": "第一集", "duration": 600, "channel": "Ch", "playlist_title": "課程"},
    {"id": "bbbbbbbbbbb", "title": "第二集", "duration": 900, "channel": "Ch", "playlist_title": "課程"},
    {"id": "ccccccccccc", "title": "[Private video]", "duration": None, "playlist_title": "課程"},
    {"id": "aaaaaaaaaaa", "title": "第一集", "duration": 600, "playlist_title": "課程"},
    {"id": "eeeeeeeeeee", "title": "會員課", "duration": 800, "availability": "subscriber_only"},
    {"id": "ddddddddddd", "title": "第三集", "duration": 300, "playlist_title": "課程"},
]


@pytest.fixture
def fake_ytdlp(monkeypatch):
    """讓 entries() 讀假的 --flat-playlist 輸出，測試不碰網路。"""
    calls = []

    def run(cmd, capture_output=True, text=True, **kw):
        calls.append(cmd)
        out = "\n".join(json.dumps(e, ensure_ascii=False) for e in ENTRIES)
        return subprocess.CompletedProcess(cmd, 0, out, "")

    monkeypatch.setattr(playlist.subprocess, "run", run)
    return calls


def test_detects_playlist_urls():
    assert playlist_id(PL) == "PLabc123"
    assert is_playlist_url(PL)
    # 指定了某一支又帶清單：預設只做那一支
    assert not is_playlist_url(WATCH_IN_PL)
    assert is_playlist_url(WATCH_IN_PL, only=False)
    assert video_id(WATCH_IN_PL) == "aaaaaaaaaaa"
    assert not is_playlist_url("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert not is_playlist_url("https://example.com/blog/post?list=x")
    assert playlist_index(WATCH_2ND) == 2
    assert playlist_index(WATCH_IN_PL) is None


def test_playlist_url_is_not_a_video_id():
    with pytest.raises(ValueError, match="播放清單"):
        video_id(PL)


def test_entries_keeps_order_and_drops_dead_ones(fake_ytdlp):
    pl = playlist.entries(PL)
    assert [v["id"] for v in pl["videos"]] == ["aaaaaaaaaaa", "bbbbbbbbbbb", "ddddddddddd"]
    assert [v["index"] for v in pl["videos"]] == [1, 2, 3]
    assert pl["title"] == "課程" and pl["playlist_id"] == "PLabc123"
    assert {s["why"] for s in pl["skipped"]} == {"已刪除或私人影片", "清單內重複", "頻道會員限定"}
    # 展開後是乾淨的單支網址，下游的 --no-playlist 不會歧義
    assert pl["videos"][0]["url"] == "https://www.youtube.com/watch?v=aaaaaaaaaaa"


def test_entries_passes_range_to_ytdlp(fake_ytdlp):
    playlist.entries(PL, items="1-2")
    playlist.entries(PL, limit=3)
    assert "--playlist-items" in fake_ytdlp[0] and "1-2" in fake_ytdlp[0]
    assert "-I" in fake_ytdlp[1] and ":3" in fake_ytdlp[1]


def test_entries_raises_when_nothing_comes_back(monkeypatch):
    monkeypatch.setattr(playlist.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", "ERROR: 私人清單"))
    with pytest.raises(RuntimeError, match="展不開"):
        playlist.entries(PL)


def test_expand_videos_inherits_options_and_keeps_others(fake_ytdlp):
    given = [
        {"url": "https://youtu.be/zzzzzzzzzzz", "shots": "none"},
        {"url": PL, "shots": "many", "vision": "false", "max_shots": 4},
    ]
    out = playlist.expand_videos(given)
    assert [v["url"] for v in out] == [
        "https://youtu.be/zzzzzzzzzzz",
        "https://www.youtube.com/watch?v=aaaaaaaaaaa",
        "https://www.youtube.com/watch?v=bbbbbbbbbbb",
        "https://www.youtube.com/watch?v=ddddddddddd",
    ]
    for v in out[1:]:
        assert (v["shots"], v["vision"], v["max_shots"]) == ("many", "false", 4)
        assert v["playlist_title"] == "課程"
    assert [v["playlist_index"] for v in out[1:]] == [1, 2, 3]


def test_expand_videos_modes_for_watch_plus_list(fake_ytdlp):
    # 預設只做點進來的那一支
    assert playlist.expand_videos([{"url": WATCH_IN_PL}]) == [{"url": WATCH_IN_PL}]
    # all = 整份清單；from-here = 從那一支到最後
    assert len(playlist.expand_videos([{"url": WATCH_IN_PL}], mode="all")) == 3
    rest = playlist.expand_videos([{"url": WATCH_2ND}], mode="from-here")
    assert [v["url"].split("v=")[1] for v in rest] == ["bbbbbbbbbbb", "ddddddddddd"]
    assert [v["playlist_index"] for v in rest] == [1, 2]
    # input.yaml 那一筆自己寫 playlist: all 也算
    assert len(playlist.expand_videos([{"url": WATCH_IN_PL, "playlist": "all"}])) == 3
    with pytest.raises(ValueError, match="playlist 只能是"):
        playlist.expand_videos([{"url": WATCH_IN_PL, "playlist": "everything"}])


def test_from_here_on_entries(fake_ytdlp):
    pl = playlist.entries(WATCH_2ND, from_here=True)
    assert [v["id"] for v in pl["videos"]] == ["bbbbbbbbbbb", "ddddddddddd"]
    assert playlist.entries(WATCH_2ND)["videos"][0]["id"] == "aaaaaaaaaaa"


def test_load_input_expands_watch_plus_list_only_when_asked(tmp_path, fake_ytdlp):
    p = tmp_path / "input.yaml"
    p.write_text(f"videos:\n  - url: {WATCH_IN_PL}\n", encoding="utf-8")
    assert [v["id"] for v in load_input(p)["videos"]] == ["aaaaaaaaaaa"]
    p.write_text(f"videos:\n  - url: {WATCH_IN_PL}\n    playlist: all\n", encoding="utf-8")
    assert [v["id"] for v in load_input(p)["videos"]] == ["aaaaaaaaaaa", "bbbbbbbbbbb", "ddddddddddd"]


def test_load_input_expands_playlist(tmp_path, fake_ytdlp):
    p = tmp_path / "input.yaml"
    p.write_text(f"videos:\n  - url: {PL}\n    shots: none\n", encoding="utf-8")
    data = load_input(p)
    assert [v["id"] for v in data["videos"]] == ["aaaaaaaaaaa", "bbbbbbbbbbb", "ddddddddddd"]
    assert all(v["shots"] == "none" and v["vision"] is True for v in data["videos"])


def test_print_list_shows_order(fake_ytdlp, capsys):
    playlist.main([PL])
    out = capsys.readouterr().out
    assert "播放清單：課程" in out and "3 支" in out
    assert out.index("1. 第一集") < out.index("2. 第二集") < out.index("3. 第三集")
    assert "跳過：[Private video]" in out
