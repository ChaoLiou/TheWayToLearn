"""所有 script 共用：路徑、video id、JSON 讀寫、階段記錄。"""
from __future__ import annotations

import json
import os
import re
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent  # repo 或 plugin 的根目錄（${CLAUDE_PLUGIN_ROOT}）
CONFIG = ROOT / "config"
SCHEMAS = ROOT / "schemas"
RULES = ROOT / "rules"
TEMPLATES = ROOT / "templates"


def _workspace() -> Path:
    """workspace 位置：$LEARN_WORKSPACE > 目前目錄的 ./workspace（clone 模式下目前目錄就是 repo）。"""
    env = os.environ.get("LEARN_WORKSPACE")
    return Path(env).expanduser().resolve() if env else Path.cwd() / "workspace"


DEFAULT_WORKSPACE = _workspace()


def override_dir() -> Path:
    """使用者自己的規則覆寫目錄：$LEARN_RULES > 目前目錄的 ./learn.rules。
    plugin 模式下 rules/ config/ templates/ 會被更新覆蓋，要客製就複製到這裡改。"""
    env = os.environ.get("LEARN_RULES")
    return Path(env).expanduser().resolve() if env else Path.cwd() / "learn.rules"


def rule_file(name: str) -> Path:
    o = override_dir() / name
    return o if o.exists() else RULES / name


def config_file(name: str) -> Path:
    o = override_dir() / name
    return o if o.exists() else CONFIG / name


def template_dirs() -> list[str]:
    """Jinja 搜尋路徑：覆寫目錄的 templates/ 優先。"""
    o = override_dir() / "templates"
    return [str(o), str(TEMPLATES)] if o.is_dir() else [str(TEMPLATES)]

_ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})")
_YT_HOST = re.compile(r"^https?://(?:[\w-]+\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)/", re.IGNORECASE)
BLOG_PREFIX = "b_"  # 部落格站的 id 開頭：後面 9 碼是網址的 sha1，湊成跟 YouTube 一樣的 11 碼


def blog_id(url: str) -> str:
    """部落格文章的 id：去掉 fragment 與結尾斜線後取 sha1，同一篇文章不管怎麼貼都是同一站。"""
    import hashlib
    norm = re.sub(r"#.*$", "", url.strip()).rstrip("/")
    norm = re.sub(r"^https?://(www\.)?", "", norm, flags=re.IGNORECASE)
    return BLOG_PREFIX + hashlib.sha1(norm.encode("utf-8")).hexdigest()[:9]


def is_blog(vid_or_meta) -> bool:
    """給 id 或 meta.json 的 dict 都可以：這一站是不是部落格文章。"""
    if isinstance(vid_or_meta, dict):
        return vid_or_meta.get("source") == "blog" or str(vid_or_meta.get("video_id", "")).startswith(BLOG_PREFIX)
    return str(vid_or_meta).startswith(BLOG_PREFIX)


def is_youtube_url(s: str) -> bool:
    return bool(_YT_HOST.match(s))


_LIST_RE = re.compile(r"[?&]list=([A-Za-z0-9_-]+)")


def playlist_id(url: str) -> str | None:
    """YouTube 網址裡的播放清單 id（`list=`），沒有就回 None。"""
    if not is_youtube_url(url):
        return None
    m = _LIST_RE.search(url)
    return m.group(1) if m else None


def playlist_index(url: str) -> int | None:
    """`watch?v=…&list=…&index=N` 的 N：使用者是從清單第幾支點進來的。"""
    m = re.search(r"[?&]index=(\d+)", url)
    return int(m.group(1)) if m and playlist_id(url) else None


def is_playlist_url(url: str, only: bool = True) -> bool:
    """這個網址要不要當播放清單展開。
    only=True（預設）：只有同時沒指定某一支影片時才算（`/playlist?list=…`）；
    `watch?v=X&list=Y` 是「清單裡的第 X 支」，預設只做那一支，only=False 才連整份清單一起算。"""
    if not playlist_id(url):
        return False
    return not (only and _ID_RE.search(url))


def video_id(url_or_id: str) -> str:
    """接受 URL 或裸 id，回傳 11 碼 id。YouTube 以外的網址當成部落格文章，id 由網址算出。"""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id
    m = _ID_RE.search(url_or_id)
    if m:
        return m.group(1)
    if re.match(r"^https?://", url_or_id, re.IGNORECASE) and not is_youtube_url(url_or_id):
        return blog_id(url_or_id)
    if playlist_id(url_or_id):
        raise ValueError(f"這是播放清單不是單支影片: {url_or_id}\n"
                         f"先展開：scripts/playlist.py <網址>（estimate.py 與 /learn 會自動展開）")
    raise ValueError(f"看不出 video id: {url_or_id}")


_BAD_FS = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def title_dirname(title: str, limit: int = 80) -> str:
    """YouTube title → 可當資料夾名的字串。"""
    name = _BAD_FS.sub(" ", title)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if len(name) > limit:  # 在字邊界截斷，避免留下半個字或孤立的「(」
        cut = name[:limit]
        name = cut[: cut.rfind(" ")] if " " in cut[limit // 2 :] else cut
    return name.rstrip(" .-(（[") or "untitled"


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
    """回傳（必要時建立）影片的工作目錄。已存在就沿用；不存在需要 title 才能建。
    標題撞名（不同影片同名、或標題被截成同一個字串）就加 (2)、(3)，不會蓋到別支。"""
    found = find_video_dir(vid, workspace)
    if found:
        return found
    if title is None:
        raise FileNotFoundError(f"workspace 裡沒有 {vid} 的資料夾，先跑 estimate 或 fetch")
    base = title_dirname(title)
    d, n = workspace / base, 2
    while d.exists() and any(d.iterdir()):  # 已經有人用了（find_video_dir 找不到 = 不是這支）
        d = workspace / f"{base} ({n})"
        n += 1
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_text(p: Path, text: str) -> None:
    """先寫暫存檔再 os.replace：多支影片同時跑時，讀的人不會讀到寫到一半的檔案。"""
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def save_json(p: Path, data) -> None:
    write_text(p, json.dumps(data, ensure_ascii=False, indent=2))


@contextmanager
def locked(path: Path, what: str = ""):
    """workspace 層級的共用檔（atlas.json、dist/）一次只給一個 process 寫。
    advisory lock，只擋同樣走這個函式的人；沒有 fcntl 的平台就不鎖。"""
    try:
        import fcntl
    except ImportError:
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print(f"等另一個流程放開 {what or path.name} …")
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_input(p: Path) -> dict:
    """input.yaml → 正規化：每支影片有 url/id/vision；播放清單網址就地展開成清單順序的每一支。"""
    data = load_yaml(p)
    data.setdefault("lang", ["zh-TW", "zh", "en"])
    data.setdefault("out", str(DEFAULT_WORKSPACE))
    data.setdefault("output_lang", "zh-TW")  # /learn 依對話語言填
    if any(playlist_id(str(v.get("url", ""))) for v in data["videos"]):
        # 只有真的有清單時才載（展不展開由 expand_videos 依該筆的 playlist 決定）
        from playlist import expand_videos
        data["videos"] = expand_videos(data["videos"])
    for v in data["videos"]:
        v["id"] = video_id(v["url"])
        v.setdefault("vision", True)
        v.setdefault("shots", "auto")
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


# ---- 流程步驟：每個階段跑完都印同一種進度行，讓使用者知道走到哪 ----
STEPS: list[tuple[str, str]] = [
    ("estimate", "估成本"),
    ("fetch", "抓字幕"),
    ("segment", "切段"),
    ("shot", "截圖"),
    ("analyze", "逐段分析"),
    ("digest", "消化工作單"),
    ("render", "產出 plan.html"),
    ("atlas", "連結各站"),
    ("narrate", "產出聽力版"),
    ("listen", "podcast 頁"),
]
STEP_CMD = {k: f"/atlas:learn-{k}" for k, _ in STEPS}


def step_no(key: str) -> int:
    return next(i for i, (k, _) in enumerate(STEPS, 1) if k == key)


def step_line(key: str, note: str = "") -> str:
    """`[3/7] ✔ segment 切段 完成  ●●●○○○○` + 下一步。"""
    n, total = step_no(key), len(STEPS)
    _, zh = STEPS[n - 1]
    bar = "●" * n + "○" * (total - n)
    head = f"[{n}/{total}] ✔ {key} {zh} 完成  {bar}"
    if note:
        head += f"  · {note}"
    if n == total:
        return f"{head}\n        全部完成 → 開 workspace/listen.html"
    nk, nzh = STEPS[n]
    tail = f"        下一步 [{n + 1}/{total}] {nk} {nzh} → {STEP_CMD[nk]}"
    if nk == "atlas":
        tail += "（workspace 有 ≥ 2 站時才需要）"
    if nk == "narrate":
        tail += "（選配：想用聽的再跑）"
    if nk == "digest":
        tail += "（選配：--digest false 可跳過）"
    return f"{head}\n{tail}"


def print_step(key: str, note: str = "") -> None:
    print(step_line(key, note))


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
