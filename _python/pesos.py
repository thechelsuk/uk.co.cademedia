"""Shared helpers for the PESOS importers.

Each importer turns items from somewhere else (YouTube, the podcast feed,
TikTok, Instagram) into one Markdown file per item in a Jekyll collection.
Files are matched on the item's source id, and existing files are never
overwritten, so hand edits to an imported item are kept.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from pathlib import Path

import bleach
import requests
import yaml
from markdownify import markdownify

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "Mozilla/5.0 (compatible; cademedia-pesos/1.0; +https://www.cademedia.co.uk)"

ALLOWED_TAGS = ["a", "p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "blockquote"]
ALLOWED_ATTRS = {"a": ["href", "title"]}

# `source_id`, not `id`: Jekyll reserves `id` on documents for the page path
ID_LINE = re.compile(r"^source_id:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", re.M)


def load_sources() -> dict:
    """The `sources:` block from _config.yml, so feed ids live in one place."""
    config = yaml.safe_load((ROOT / "_config.yml").read_text(encoding="utf-8"))
    return config.get("sources") or {}


def slugify(text: str, max_len: int = 60) -> str:
    """ASCII, lower-case, hyphenated slug cut at a word boundary."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"#\w+", "", text)  # drop hashtags
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0]
    return slug or "item"


def first_line(text: str, max_len: int = 120) -> str:
    """First non-empty line of a caption, trimmed, for use as a title."""
    for line in (text or "").splitlines():
        line = re.sub(r"(?:\s*#\w+)+\s*$", "", line).strip()
        if line:
            return line if len(line) <= max_len else line[: max_len - 1].rsplit(" ", 1)[0] + "…"
    return ""


def clean_html(html: str) -> str:
    """Strips a feed's HTML down to simple, safe tags."""
    return bleach.clean(html or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
                        protocols=["http", "https", "mailto"], strip=True)


def html_to_markdown(html: str) -> str:
    md = markdownify(clean_html(html), heading_style="ATX", bullets="-")
    return re.sub(r"\n{3,}", "\n\n", md).strip()


URL = re.compile(r"https?://[^\s<>()\"']*[^\s<>()\"'.,;:!?]")
MD_SPECIAL = re.compile(r"([\\`*_\[\]<>|])")
CHAPTER = re.compile(r"^\s*\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*[-–—:|]?\s*(\S.*?)\s*$")


def escape_markdown(line: str) -> str:
    """Escapes Markdown in plain text, turning bare URLs into autolinks."""
    out, last = [], 0
    for m in URL.finditer(line):
        out.append(MD_SPECIAL.sub(r"\\\1", line[last:m.start()]))
        out.append(f"<{m.group(0)}>")
        last = m.end()
    out.append(MD_SPECIAL.sub(r"\\\1", line[last:]))
    text = "".join(out)
    return "\\" + text if text.startswith("#") else text


def text_to_markdown(text: str) -> str:
    """Plain caption text to Markdown: escaped, links clickable, and line
    breaks kept (two trailing spaces) the way they were written."""
    text = (text or "").replace("\r\n", "\n").strip()
    lines = [escape_markdown(line.rstrip()) for line in text.split("\n")]
    md = "\n".join(line + "  " if line else "" for line in lines)
    return re.sub(r"\n{3,}", "\n\n", md).rstrip()


def to_seconds(stamp: str) -> int:
    seconds = 0
    for part in stamp.split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


def split_chapters(text: str) -> tuple[list[dict], str]:
    """Pulls '04:50 Topic' lines out as chapters. Needs at least two, so a
    lone timestamp in a sentence stays put. Returns (chapters, rest)."""
    chapters, rest = [], []
    for line in (text or "").splitlines():
        m = CHAPTER.match(line)
        if m:
            # No "time" string: YAML 1.1 reads 03:03 as a base-60 number
            chapters.append({"seconds": to_seconds(m.group(1)),
                             "title": m.group(2).replace("\\", "")})
        else:
            rest.append(line)
    if len(chapters) < 2:
        return [], text
    return chapters, re.sub(r"\n{3,}", "\n\n", "\n".join(rest)).strip()


def to_datetime(value) -> dt.datetime:
    """Accepts a datetime, unix timestamp, ISO string or time.struct_time."""
    if isinstance(value, dt.datetime):
        d = value
    elif isinstance(value, (int, float)):
        d = dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    elif hasattr(value, "tm_year"):
        d = dt.datetime(*value[:6], tzinfo=dt.timezone.utc)
    else:
        s = str(value).replace("Z", "+00:00")
        if re.match(r".*[+-]\d{4}$", s):  # Instagram style +0000
            s = s[:-2] + ":" + s[-2:]
        d = dt.datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def existing_ids(folder: Path) -> set[str]:
    """Source ids of every item already in a collection folder."""
    ids = set()
    if folder.exists():
        for path in folder.rglob("*.md"):
            head = path.read_text(encoding="utf-8").split("---", 2)
            if len(head) >= 3:
                m = ID_LINE.search(head[1])
                if m:
                    ids.add(m.group(1).strip())
    return ids


def render(fields: dict, body: str = "") -> str:
    fm = yaml.safe_dump(fields, sort_keys=False, allow_unicode=True, width=1000)
    return f"---\n{fm}---\n" + (f"\n{body.strip()}\n" if body and body.strip() else "")


def filename_for(date: dt.datetime, title: str, item_id: str) -> str:
    """yyyy-mm-dd-title.md, falling back to the id when the title is empty."""
    slug = slugify(title)
    if slug == "item":
        slug = slugify(str(item_id))
    return f"{date:%Y-%m-%d}-{slug}.md"


def write_item(collection: str, fields: dict, body: str = "", known: set[str] | None = None,
               root: Path = ROOT) -> Path | None:
    """Writes one item unless its id is already in the collection.

    `fields` must hold `source_id`, `title` and `date` (a datetime). Returns the new
    file's path, or None when the item already exists.
    """
    folder = root / f"_{collection}"
    known = existing_ids(folder) if known is None else known
    item_id = str(fields["source_id"])
    if item_id in known:
        return None
    date = fields["date"]
    path = folder / filename_for(date, fields.get("title", ""), item_id)
    n = 2
    while path.exists():  # same day, same title: keep both
        path = path.with_name(f"{path.stem}-{n}.md")
        n += 1
    out = dict(fields)
    out["date"] = date.strftime("%Y-%m-%d %H:%M:%S %z")
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(render(out, body), encoding="utf-8")
    known.add(item_id)
    return path


SKIP_SUMMARY = re.compile(
    r"https?://|<http|\bwww\.|\[ad\]|\bsponsor|\bsupporting\b|\bdeal\b|\bcode\b|\bdiscount|\S+@\S+|^\s*\d{1,2}:\d{2}"
    r"|whatsapp|voice note|\bpatreon|\bsubscribe|\bjoin the\b|po box|\bsend (?:us|in)\b|\+\d{2}\s?\d|\bmerch\b|ad ?choices|podcastchoices",
    re.I)


def summary_line(text: str, max_len: int = 200, boilerplate: set[str] | None = None) -> str | None:
    """First line that reads like a summary: not an ad, link, timestamp,
    or a line in `boilerplate` (text repeated across many items)."""
    boilerplate = boilerplate or set()
    for line in (text or "").splitlines():
        line = re.sub(r"[*_]", "", line).strip()
        if len(line) >= 25 and not SKIP_SUMMARY.search(line) and line not in boilerplate:
            return first_line(line, max_len)
    return None


def repeated_lines(texts: list[str], min_count: int = 4) -> set[str]:
    """Lines that appear in at least `min_count` of the texts: sign-offs,
    sponsor reads and other boilerplate rather than a summary."""
    from collections import Counter

    counts = Counter()
    for text in texts:
        counts.update({re.sub(r"[*_]", "", l).strip() for l in (text or "").splitlines() if l.strip()})
    return {line for line, n in counts.items() if n >= min_count}


def download(url: str, dest: Path, max_width: int = 720, timeout: int = 30) -> bool:
    """Saves a remote image locally as a resized JPEG.

    Social CDNs (TikTok, Instagram) sign their image URLs and they expire,
    so the site keeps its own copy.
    """
    if dest.exists():
        return True
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"x Could not download {url}: {e}")
        return False
    from io import BytesIO

    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        img = Image.open(BytesIO(r.content)).convert("RGB")
        if img.width > max_width:
            img = img.resize((max_width, round(img.height * max_width / img.width)))
        img.save(dest, "JPEG", quality=82, optimize=True, progressive=True)
    except OSError as e:
        print(f"x Not an image {url}: {e}")
        return False
    return True
