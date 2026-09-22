"""部落格文章當來源：抓 HTML → 主文（段落、標題、程式碼、清單、圖片）→ 跟影片同一種 transcript.json。

時間軸用「閱讀時間」：每個段落是一個 event，start = 讀到這裡累積的秒數（速度在 config/estimate.yaml 的
blog.cjk_chars_per_min / words_per_min）。這樣 segments / shots / clips 的 start、end、t 仍然是秒數，
validate / render / narrate 不必另外分支；render 顯示時把秒數換回「第幾段（¶n）」與原文的 text fragment 連結。
文章裡的圖片記在 transcript.images（t = 出現的位置），步驟 4 挑到的就直接下載到 frames/，不用 ffmpeg。
"""
from __future__ import annotations

import mimetypes
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, urljoin

from common import config_file, load_yaml

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
DEFAULT_CFG = {"cjk_chars_per_min": 350, "words_per_min": 220, "fetch_sec": 5, "sec_per_image": 1}
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯]")
_WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_'’-]*")
_LANG_ATTR = re.compile(r"<html[^>]*\slang=[\"']?([A-Za-z-]+)", re.IGNORECASE)
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"}


def blog_cfg() -> dict:
    cfg = load_yaml(config_file("estimate.yaml")).get("blog") or {}
    return {**DEFAULT_CFG, **cfg}


def fetch_html(url: str) -> str:
    """先用 trafilatura 抓（會處理編碼、重試）；它偶爾回 None（UA 被擋、暫時性錯誤）就換瀏覽器 UA 直接抓。"""
    import trafilatura

    html = trafilatura.fetch_url(url)
    if html:
        return html
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=30) as r:
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip()
            if ctype and "html" not in ctype and "xml" not in ctype:
                raise SystemExit(f"{url} 不是 HTML 頁面（{ctype}）")
            charset = r.headers.get_content_charset() or "utf-8"
            return r.read().decode(charset, errors="replace")
    except OSError as e:
        raise SystemExit(f"抓不到 {url}：{e}（網站擋了、需要登入、或網路問題）") from e


def reading_seconds(text: str, cfg: dict) -> float:
    """中文字算字數、其他語言算詞數，各用各的閱讀速度；每個段落至少 1 秒。"""
    cjk = len(_CJK.findall(text))
    words = len(_WORD.findall(_CJK.sub(" ", text)))
    sec = cjk / cfg["cjk_chars_per_min"] * 60 + words / cfg["words_per_min"] * 60
    return max(1.0, round(sec, 2))


def guess_lang(html: str, text: str) -> str:
    m = _LANG_ATTR.search(html)
    if m:
        return m.group(1)
    cjk = len(_CJK.findall(text))
    return "zh" if text and cjk / max(1, len(text.replace(" ", ""))) > 0.3 else "en"


def _text(el: ET.Element) -> str:
    if el.tag == "list":
        return "\n".join("• " + " ".join(it.itertext()).strip() for it in el.iter("item"))
    if el.tag == "table":
        rows = ["｜".join(" ".join(c.itertext()).strip() for c in row.iter("cell")) for row in el.iter("row")]
        return "\n".join(r for r in rows if r.strip("｜ "))
    return re.sub(r"[ \t]+", " ", " ".join(el.itertext())).strip()


def _kind(el: ET.Element) -> str:
    if el.tag == "head":
        return el.get("rend", "h2")
    return {"p": "p", "code": "code", "quote": "quote", "list": "list", "table": "table"}.get(el.tag, "p")


def extract(html: str, url: str, cfg: dict | None = None) -> dict:
    """HTML → {title, author, site, date(YYYYMMDD|None), lang, image, duration, events, images, chapters}。
    events 跟影片的 transcript 一樣有 start/duration/text，另有 kind（p/h1/h2/code/list…）與 para（第幾個段落）。"""
    import trafilatura

    cfg = cfg or blog_cfg()
    xml = trafilatura.extract(html, url=url, output_format="xml", include_images=True,
                              include_formatting=False, include_tables=True, include_links=False)
    if not xml:
        raise SystemExit(f"抓到頁面但抽不出正文：{url}")
    md = trafilatura.extract_metadata(html, default_url=url).as_dict()
    root = ET.fromstring(xml)
    main = root.find("main")
    events, images, t, para = [], [], 0.0, 0
    for el in list(main) if main is not None else []:
        if el.tag == "graphic":
            src = el.get("src") or ""
            if src:
                images.append({"t": round(t, 2), "src": urljoin(url, src), "alt": (el.get("alt") or "").strip(), "para": para})
            continue
        text = _text(el)
        if not text:
            continue
        # 段落裡夾的圖：位置算在這一段開頭
        for g in el.iter("graphic"):
            if g.get("src"):
                images.append({"t": round(t, 2), "src": urljoin(url, g.get("src")), "alt": (g.get("alt") or "").strip(), "para": para + 1})
        para += 1
        d = reading_seconds(text, cfg)
        events.append({"start": round(t, 2), "duration": d, "text": text, "kind": _kind(el), "para": para})
        t += d
    if not events:
        raise SystemExit(f"正文是空的：{url}")
    heads = [e for e in events if e["kind"].startswith("h")]
    chapters = [{"title": h["text"], "start": h["start"],
                 "end": (heads[i + 1]["start"] if i + 1 < len(heads) else round(t, 2))}
                for i, h in enumerate(heads)]
    full = " ".join(e["text"] for e in events)
    date = re.sub(r"\D", "", md.get("date") or "")[:8] or None
    title = md.get("title") or ""
    h1 = next((h["text"] for h in heads if h["kind"] == "h1"), None)
    if h1 and (not title or title.startswith(h1)):  # <title> 常帶「| 站名」，正文 h1 比較乾淨
        title = h1
    else:  # 沒有 h1：把「| 站名」「– 站名」這種尾巴切掉
        head = re.split(r"\s+[|–—]\s+", title)[0].strip()
        title = head if len(head) >= 5 else title
    return {
        "title": title or (heads[0]["text"] if heads else url),
        "author": md.get("author"),
        "site": md.get("sitename") or md.get("hostname"),
        "date": date if date and len(date) == 8 else None,
        "lang": md.get("language") or guess_lang(html, full),
        "image": md.get("image"),
        "duration": round(t, 2),
        "chars": len(full),
        "events": events,
        "images": images,
        "chapters": chapters,
    }


def event_at(events: list[dict], t: float) -> dict | None:
    """讀到 t 秒時在哪一段：最後一個 start <= t 的 event。"""
    hit = None
    for e in events:
        if e["start"] <= t + 1e-6:
            hit = e
        else:
            break
    return hit or (events[0] if events else None)


def snippet(text: str, n_words: int = 6, n_chars: int = 14) -> str:
    """text fragment 用的開頭片段：英文取前幾個詞，中文取前幾個字，避免標點讓瀏覽器對不到。"""
    text = re.sub(r"\s+", " ", text).strip().lstrip("•·-* ")  # 清單的項目符號是我們自己加的
    if _CJK.search(text):
        return re.split(r"[，。！？；：、「」（）\(\),.!?;:]", text)[0][:n_chars]
    words = re.split(r"[.,;:!?()\"]", text)[0].split(" ")
    return " ".join(words[:n_words])


def source_href(url: str, events: list[dict], t: float, text: str | None = None) -> str:
    """原文連結：用 text fragment 讓瀏覽器直接捲到那一段並反白。給 text（例如勘誤的逐字引文）就對它。"""
    if text is None:
        e = event_at(events, t)
        if not e:
            return url
        text = e["text"]
    s = snippet(text)
    return f"{url}#:~:text={quote(s)}" if s else url


def pos_label(events: list[dict], t: float) -> str:
    e = event_at(events, t)
    return f"¶{e['para']}" if e else "¶?"


def image_for(images: list[dict], t: float, src: str | None = None) -> dict | None:
    """挑到的 shot 對應哪張圖：有寫 src 就用它，否則取離 t 最近的那張。"""
    if src:
        hit = next((im for im in images if im["src"] == src), None)
        return hit or {"t": t, "src": src, "alt": ""}
    if not images:
        return None
    return min(images, key=lambda im: abs(im["t"] - t))


def download_image(src: str, out_stem: Path) -> Path:
    """下載一張圖到 out_stem + 副檔名（依 content-type / 網址判斷），回傳實際路徑。"""
    req = urllib.request.Request(src, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip()
    ext = Path(src.split("?")[0]).suffix.lower()
    if ext not in IMG_EXT:
        ext = mimetypes.guess_extension(ctype) or ".jpg"
        ext = {".jpe": ".jpg", ".jpeg": ".jpg"}.get(ext, ext)
    out = out_stem.with_suffix(ext)
    out.write_bytes(data)
    return out
