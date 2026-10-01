"""把 workspace 裡「要上線的檔案」整理成 dist/，可選擇直接部署到 Cloudflare Pages。

  uv run scripts/publish.py                          # 只整理 dist/ 並列出內容
  uv run scripts/publish.py --deploy                 # 整理後用 wrangler 部署
  uv run scripts/publish.py --project-name my-atlas --deploy

只複製：listen.html、digest.html、notes.html、atlas.html、各站 plan.html、frames/、lesson.mp3、lesson.dub.mp3、captions.js
（外加一份 index.html = listen.html，沒有 listen.html 就用 atlas.html）。
不複製：原始音訊 audio.mp3、TTS 片段快取 lesson_parts/、transcript 與各種 json（內容已內嵌在 html）。

## 混合式：HTML 一個家、mp3 另一個家

`--media-base <網址>` 把語音解析 mp3 與截圖分出去放 object storage，HTML 裡的路徑改寫成那個絕對網址：

  uv run scripts/publish.py --media-base https://media.example.com/learn

  dist/        HTML、captions.js                    → Cloudflare Pages（小、常改、每次全量重傳）
  dist-media/  lesson.mp3、lesson.dub.mp3、frames/  → R2 / B2 / S3（大、幾乎不改、增量同步）

為什麼：容量有 96% 是 mp3，但真正會反覆重新部署的是 HTML。分開之後 Pages 每次只傳幾十 MB，
而且 object storage 沒有單檔上限——超過 72 分鐘的影片不會再撞到 Pages 的 25 MiB。
瀏覽器播跨網域的 `<audio>` 不需要 CORS，但那個 bucket 一定要支援 Range 請求（R2 / B2 / S3 都有），
不然進度條拖不動。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEFAULT_WORKSPACE, locked

MAX_FILE = 25 * 1024 * 1024  # Cloudflare Pages 單檔上限
KEEP = ("plan.html", "lesson.mp3", "lesson.dub.mp3", "captions.js")
MEDIA = ("lesson.mp3", "lesson.dub.mp3")   # --media-base 時分出去的檔（frames/ 底下的圖也算，見 is_media）
TOP = ("atlas.html", "listen.html", "digest.html", "notes.html")   # 第一個存在的當 index.html
# HTML / JS 裡引用媒體的地方一律是被引號夾住的相對路徑，兩種形狀：
#   plan.html 在站資料夾裡 → 裸的 `lesson.mp3` / `frames/s01_30.jpg`
#   listen.html / atlas.html 在 workspace 根 → `<站>/lesson.mp3` / `<站>/frames/s01_30.jpg`
MEDIA_REF = re.compile(
    r"""(?<=["'])(?!\w+:)((?:[^"']*/)?)((?:lesson(?:\.dub)?\.mp3)|(?:frames/[^"'/]+))(?=["'])""")


def is_media(rel: Path) -> bool:
    return rel.name in MEDIA or "frames" in rel.parts


# Cloudflare 的管理 API 會把路徑裡的 `..` 當目錄穿越擋掉（403，連 %2E%2E 也一樣），
# 而 YouTube 標題很容易出現「You Think.. Here's Why」這種連續句點。Pages 服務端其實吃得下，
# 但上傳進 R2 就會失敗，所以媒體 key 一律把連續點收斂成一個。URL 與 dist-media/ 的路徑
# 都走同一個函式，兩邊才不會對不上。
DOT_RUN = re.compile(r"\.{2,}")


def safe_key(path: str) -> str:
    return DOT_RUN.sub(".", path)


def rewrite_media(text: str, base: str, station: str | None) -> tuple[str, int]:
    r"""把 mp3／截圖的路徑換成 media base 的絕對網址。
    station 有值 = 這份 HTML 住在該站資料夾裡（plan.html），路徑是裸的，要補回站名。
    `(?!\w+:)` 排掉 `https://…`、`data:…`：外部縮圖（i.ytimg.com）與已是絕對網址的不要動。
    （站名本身可能有冒號，例如「測試影片 A: B」，所以不能拿「有沒有冒號」當判準。）"""
    def sub(m):
        prefix = m.group(1) or (f"{quote(station)}/" if station else "")
        return f"{base}/{safe_key(prefix + m.group(2))}"
    return MEDIA_REF.subn(sub, text)


def human(n: int) -> str:
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"


def collect(ws: Path) -> list[tuple[Path, Path]]:
    """回傳 [(來源, dist 內的相對路徑)]。"""
    out: list[tuple[Path, Path]] = []
    index_done = False
    for name in TOP:
        f = ws / name
        if f.exists():
            out.append((f, Path(name)))
            if not index_done:
                out.append((f, Path("index.html")))  # 根網址直接進「全部影片」（沒有就依序退到 listen / digest / notes）
                index_done = True
    for d in sorted(p for p in ws.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        for name in KEEP:
            f = d / name
            if f.exists():
                out.append((f, Path(d.name) / name))
        frames = d / "frames"
        if frames.is_dir():
            out += [(f, Path(d.name) / "frames" / f.name) for f in sorted(frames.iterdir()) if f.is_file()]
    return out


def build(ws: Path, dist: Path, media: Path | None = None, base: str = "") -> tuple[list, list]:
    """回傳 (站台檔, 媒體檔)；base 有值時 mp3 進 media/，HTML 裡的路徑改寫成絕對網址。"""
    items = collect(ws)
    if not items:
        raise SystemExit(f"{ws} 裡沒有可發佈的檔案（先跑 /learn 產生 plan.html）")
    for d in (dist, media):
        if d and d.exists():
            shutil.rmtree(d)
    site, mp3s, rewritten = [], [], 0
    seen: dict[str, Path] = {}
    for src, rel in items:
        to_media = bool(base) and is_media(rel)
        if to_media:  # key 收斂後兩個不同的站撞在一起就停下來，不要靜靜蓋掉
            k = safe_key(rel.as_posix())
            if k in seen and seen[k] != rel:
                raise SystemExit(f"媒體 key 衝突：{rel} 與 {seen[k]} 收斂後都是 {k}，改一下資料夾名稱")
            seen[k] = rel
        dst = (media / safe_key(rel.as_posix())) if to_media else (dist / rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if base and rel.suffix in (".html", ".js") and not to_media:
            station = rel.parts[0] if len(rel.parts) > 1 else None
            text, n = rewrite_media(src.read_text(encoding="utf-8"), base, station)
            dst.write_text(text, encoding="utf-8")
            rewritten += n
        else:
            shutil.copy2(src, dst)
        (mp3s if to_media else site).append((src, rel))
    if base:
        print(f"改寫了 {rewritten} 處媒體路徑（mp3 與截圖）→ {base}/…")
    return site, mp3s


def report(ws: Path, dist: Path, site: list, mp3s: list, media: Path | None) -> int:
    """只有留在 Pages 的檔要檢查 25 MiB；分出去的 mp3 不受限。"""
    def size_of(items, root):
        # 媒體檔落地在 safe_key() 收斂後的路徑上，不是原始 rel
        return sum((root / (safe_key(rel.as_posix()) if root is media else rel.as_posix()))
                   .stat().st_size for _, rel in items)

    big = [(rel, src.stat().st_size) for src, rel in site if src.stat().st_size > MAX_FILE]
    stations = sorted({rel.parts[0] for _, rel in site + mp3s if len(rel.parts) > 1})
    print(f"dist: {dist}")
    print(f"  {len(site)} 個檔案、{human(size_of(site, dist))}"
          f"（workspace 全部是 {human(sum(f.stat().st_size for f in ws.rglob('*') if f.is_file()))}）")
    if mp3s:
        n_a = sum(1 for _, rel in mp3s if rel.name in MEDIA)
        print(f"media: {media}")
        print(f"  {len(mp3s)} 個檔（語音解析 {n_a}、截圖 {len(mp3s) - n_a}）、{human(size_of(mp3s, media))}")
    for s in stations:
        n = sum(1 for _, rel in site if rel.parts[0] == s)
        size = size_of([x for x in site if x[1].parts[0] == s], dist)
        has = any(rel.parts[0] == s and rel.name == "lesson.mp3" for _, rel in site + mp3s)
        print(f"  · {s[:52]:54} {n:3} 檔 {human(size):>9}{'  含語音解析' if has else ''}")
    for rel, size in big:
        print(f"  !! {rel} 是 {human(size)}，超過 Cloudflare Pages 單檔 25 MB 上限")
    return len(big)


# Pages 的 advanced mode：dist/_worker.js 接走所有請求，媒體路徑轉去讀 R2，其餘丟回靜態檔。
# 這樣 HTML 與 mp3 同一個 origin，Access 一設就同時保護兩者，也避開 r2.dev 的速率限制。
# Range 一定要自己處理，不然拖進度條、跳章節會失效（見 README 的 206 說明）。
WORKER_JS = r"""// 由 scripts/publish.py 產生，不要手改
const TYPES = { mp3: "audio/mpeg", m4a: "audio/mp4", jpg: "image/jpeg", jpeg: "image/jpeg",
                png: "image/png", webp: "image/webp", gif: "image/gif" };
const PREFIX = %(prefix)s;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith(PREFIX)) return env.ASSETS.fetch(request);
    const key = decodeURIComponent(url.pathname.slice(PREFIX.length));
    if (!key || key.endsWith("/")) return new Response("Not found", { status: 404 });

    // Range: bytes=a-b / bytes=a- / bytes=-b
    let want = null;
    const raw = request.headers.get("Range");
    if (raw) {
      const m = /^bytes=(\d*)-(\d*)$/.exec(raw.trim());
      if (m && (m[1] || m[2])) {
        want = m[1]
          ? { offset: +m[1], ...(m[2] ? { length: +m[2] - +m[1] + 1 } : {}) }
          : { suffix: +m[2] };
      }
    }
    const obj = await env.%(binding)s.get(key, want ? { range: want } : undefined);
    if (!obj) return new Response("Not found", { status: 404 });

    const h = new Headers();
    obj.writeHttpMetadata(h);
    h.set("etag", obj.httpEtag);
    h.set("accept-ranges", "bytes");
    h.set("cache-control", "public, max-age=31536000, immutable");
    if (!h.get("content-type")) {
      const ext = key.split(".").pop().toLowerCase();
      if (TYPES[ext]) h.set("content-type", TYPES[ext]);
    }
    const body = request.method === "HEAD" ? null : obj.body;
    if (want && obj.range) {
      const start = obj.range.offset ?? 0;
      const len = obj.range.length ?? obj.size - start;
      h.set("content-range", `bytes ${start}-${start + len - 1}/${obj.size}`);
      h.set("content-length", String(len));
      return new Response(body, { status: 206, headers: h });
    }
    h.set("content-length", String(obj.size));
    return new Response(body, { headers: h });
  },
};
"""


def write_worker(dist: Path, base: str, binding: str) -> None:
    """base 是站內路徑（例如 /media）時才有意義：把它當前綴接到 R2。

    一起寫 `_routes.json`：沒有它的話 advanced mode 的 `_worker.js` 會接走**全站每一個請求**
    （HTML、截圖、captions.js 都算一次 Pages Functions 請求，免費方案每天 10 萬次），
    但其實只有媒體路徑需要進 worker。限定 include 之後其餘走靜態資產，不計入額度。"""
    prefix = base if base.endswith("/") else base + "/"
    (dist / "_worker.js").write_text(
        WORKER_JS % {"prefix": json.dumps(prefix), "binding": binding}, encoding="utf-8")
    (dist / "_routes.json").write_text(
        json.dumps({"version": 1, "include": [prefix + "*"], "exclude": []},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_project(start: Path | None = None) -> str:
    """預設專案名優先讀 wrangler.toml 的 name。寫死的預設值很危險：漏了 --project-name
    就會把另一個專案蓋掉，而且 _worker.js 的 R2 binding 只綁在對的那個專案上，蓋過去是壞的。"""
    d = (start or Path.cwd()).resolve()
    for p in [d, *d.parents]:
        f = p / "wrangler.toml"
        if f.exists():
            m = re.search(r'^\s*name\s*=\s*"([^"]+)"', f.read_text(encoding="utf-8"), re.MULTILINE)
            if m:
                return m.group(1)
    return "atlas-of-knowledge"


def deploy(dist: Path, project: str) -> None:
    cmd = ["wrangler", "pages", "deploy", str(dist), "--project-name", project]
    if not shutil.which("wrangler"):
        cmd = ["npx", "--yes", "wrangler@latest", *cmd[1:]]
        if not shutil.which("npx"):
            raise SystemExit("找不到 wrangler 也沒有 npx：npm i -g wrangler 之後再跑 wrangler login")
    print("\n$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    ap.add_argument("--out", type=Path, help="預設 <workspace 的上一層>/dist")
    ap.add_argument("--project-name", default=None,
                    help="Cloudflare Pages 專案名（預設讀 wrangler.toml 的 name）")
    ap.add_argument("--deploy", action="store_true", help="整理完直接用 wrangler 部署")
    ap.add_argument("--media-base", default="",
                    help="語音解析 mp3 與截圖的公開網址前綴（例如 https://media.example.com/learn）："
                         "它們改放 --media-out，HTML 裡的路徑換成絕對網址")
    ap.add_argument("--media-out", type=Path, help="--media-base 時 mp3 的輸出目錄，預設 <dist 旁>/dist-media")
    ap.add_argument("--r2-binding", default="",
                    help="--media-base 是站內路徑（例如 /media）時，產生 dist/_worker.js 從這個 R2 binding 取檔")
    args = ap.parse_args(argv)

    ws = args.workspace
    project = args.project_name or default_project()
    dist = args.out or ws.parent / "dist"
    base = args.media_base.rstrip("/")
    media = (args.media_out or dist.parent / "dist-media") if base else None
    with locked(ws / ".publish.lock", "dist/"):  # 兩個 publish 同時跑會互刪 dist/
        site, mp3s = build(ws, dist, media, base)
        if args.r2_binding:
            if base.startswith(("http://", "https://")):
                raise SystemExit("--r2-binding 要搭配站內路徑的 --media-base（例如 /media），"
                                 "絕對網址的話 R2 要自己接自訂網域，不需要 worker")
            write_worker(dist, base, args.r2_binding)
            print(f"產生 dist/_worker.js：{base}/… → R2 binding {args.r2_binding}（含 Range 支援）")
            print(f"產生 dist/_routes.json：只有 {base}/* 進 worker，其餘走靜態資產（不計入每日請求額度）")
        big = report(ws, dist, site, mp3s, media)
        if args.deploy:
            if big:
                raise SystemExit("有檔案超過 25 MB：改用 --media-base 把 mp3 分出去，或降位元率")
            deploy(dist, project)
    if not args.deploy:
        print(f"\n要部署：uv run scripts/publish.py --deploy --project-name {project}")
        print("首次使用先 npm i -g wrangler && wrangler login；部署後到 Cloudflare Zero Trust → Access 加上登入限制。")
    if mp3s:
        print(f"\n媒體檔還要另外同步上去（{media}，增量、只傳有變的）：")
        print(f"  rclone sync {media} r2:<bucket>/       # Cloudflare R2")
        print(f"  rclone sync {media} b2:<bucket>/       # Backblaze B2")
        print("  bucket 要開公開讀取、且支援 Range 請求（不然進度條拖不動）。")
        print("  上傳完抽一個檔驗一下（要看到 206、Content-Range、audio/mpeg）：")
        print(f"    curl -sI -r 0-1 '{base}/<站>/lesson.mp3' | grep -iE 'HTTP/|content-(range|type)'")
    elif not base:
        print("mp3 與截圖想分開放（省重傳、避開單檔 25 MiB）：加 --media-base <公開網址前綴>。")


if __name__ == "__main__":
    main()
