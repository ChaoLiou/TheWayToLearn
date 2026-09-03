import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import pytest
from common import find_video_dir, video_dir


def test_video_dir_by_title_then_lookup_by_id(tmp_path):
    d = video_dir("abcdefghijk", tmp_path, title="My Video: Part 1")
    assert d.name == "My Video Part 1"
    (d / "meta.json").write_text(json.dumps({"video_id": "abcdefghijk"}))
    assert find_video_dir("abcdefghijk", tmp_path) == d
    assert video_dir("abcdefghijk", tmp_path) == d


def test_video_dir_unknown_without_title(tmp_path):
    with pytest.raises(FileNotFoundError):
        video_dir("zzzzzzzzzzz", tmp_path)
