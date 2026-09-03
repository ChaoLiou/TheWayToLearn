"""所有 script 共用：路徑、video id、JSON 讀寫、階段記錄。"""
from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
SCHEMAS = ROOT / "schemas"
RULES = ROOT / "rules"
TEMPLATES = ROOT / "templates"
DEFAULT_WORKSPACE = ROOT / "workspace"

_ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})")


def video_id(url_or_id: str) -> str:
    """接受 URL 或裸 id，回傳 11 碼 id。"""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id
    m = _ID_RE.search(url_or_id)
    if not m:
        raise ValueError(f"看不出 video id: {url_or_id}")
    return m.group(1)


_BAD_FS = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def title_dirname(title: str, limit: int = 80) -> str:
    """YouTube title → 可當資料夾名的字串。"""
    name = _BAD_FS.sub(" ", title)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:limit].rstrip(" .") or "untitled"


def find_video_dir(vid: str, workspace: Path = DEFAULT_WORKSPACE) -> Path | None:
    """資料夾用影片標題命名，靠裡面的 meta.json / estimate.json 反查 id。"""
    if not workspace.exists():
        return None
    for d in sorted(workspace.iterdir()):
        if not d.is_dir() or d.name.startswith((".", "_")):
            continue
        for f in ("meta.json", "estimate.json"):
            if (d / f).exists():
                try:
                    if load_json(d / f).get("video_id") == vid:
                        return d
                except (ValueError, OSError):
                    pass
    return None


def video_dir(vid: str, workspace: Path = DEFAULT_WORKSPACE, title: str | None = None) -> Path:
    """回傳（必要時建立）影片的工作目錄。已存在就沿用；不存在需要 title 才能建。"""
    found = find_video_dir(vid, workspace)
    if found:
        return found
    if title is None:
        raise FileNotFoundError(f"workspace 裡沒有 {vid} 的資料夾，先跑 estimate 或 fetch")
    d = workspace / title_dirname(title)
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(p: Path, data) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_input(p: Path) -> dict:
    """input.yaml → 正規化：每支影片有 url/id/vision。"""
    data = load_yaml(p)
    data.setdefault("lang", ["zh-TW", "zh", "en"])
    data.setdefault("out", str(DEFAULT_WORKSPACE))
    for v in data["videos"]:
        v["id"] = video_id(v["url"])
        v.setdefault("vision", True)
    return data


def record_timing(vdir: Path, stage: str, seconds: float) -> None:
    """把各階段實際耗時累積到 timings.json，render 會拿來跟 estimate 對照。"""
    p = vdir / "timings.json"
    t = load_json(p) if p.exists() else {}
    t[stage] = {"sec": round(seconds, 1), "at": datetime.now(UTC).astimezone().isoformat(timespec="seconds")}
    save_json(p, t)


class Timer:
    def __init__(self, vdir: Path, stage: str):
        self.vdir, self.stage = vdir, stage

    def __enter__(self):
        self.t0 = time.monotonic()
        return self

    def __exit__(self, *exc):
        record_timing(self.vdir, self.stage, time.monotonic() - self.t0)


def fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_dur(sec: float) -> str:
    sec = round(sec)
    if sec < 60:
        return f"{sec}s"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"
