"""RSS / Atom → _posts/ (the "Updates" in the feed)

Short written updates come from any feed listed under
`sources.updates_feeds` in _config.yml — Tumblr, Bluesky, Mastodon,
Micro.blog, WordPress… anything with RSS or Atom. The team posts from that
service's own app and the site picks it up; no Markdown or GitHub needed.

Posts without a real title (most text posts) get `note: true` and show in
the feed like a tweet: the words, not a headline.

  python _python/fetch_updates.py
"""
from __future__ import annotations

import html
import re

import bleach
import feedparser

import pesos

IMG = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)


def plain_text(markup: str) -> str:
    text = bleach.clean(re.sub(r"</p>|<br\s*/?>", "\n", markup or "", flags=re.I), tags=[], strip=True)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def is_untitled(title: str, text: str) -> bool:
    """No title, or one the service made from the opening words."""
    title = (title or "").strip().rstrip("…").rstrip(".").strip()
    if not title or title.lower() in {"photo", "untitled", "post", "text"}:
        return True
    return text.lower().startswith(title.lower())


def to_item(entry, via: str) -> tuple[dict, str]:
    content = entry.get("content") or []
    markup = content[0].get("value") if content else entry.get("summary", "")
    text = plain_text(markup)
    title = html.unescape(entry.get("title", "")).strip()
    note = is_untitled(title, text)
    fields = {
        "source_id": (entry.get("id") or entry.get("link")).strip(),
        "title": (pesos.first_line(text, 90) or "Update") if note else title,
        "date": pesos.to_datetime(entry.get("published_parsed") or entry.get("updated_parsed")
                                  or entry.get("published")),
        "link": entry.get("link"),
        "note": note,
        "via": via,
        # Imported text is never Liquid
        "render_with_liquid": False,
    }
    image = IMG.search(markup or "")
    if image:
        fields["image"] = image.group(1)
    return fields, pesos.html_to_markdown(markup)


def run() -> int:
    feeds = pesos.load_sources().get("updates_feeds") or []
    if not feeds:
        print("Updates: no feeds configured, skipping.")
        return 0
    known = pesos.existing_ids(pesos.ROOT / "_posts")
    added = 0
    for f in feeds:
        feed = feedparser.parse(f["url"])
        if not feed.entries:
            print(f"::warning::No entries in {f['url']}")
            continue
        for entry in feed.entries:
            try:
                fields, body = to_item(entry, f.get("name", "rss"))
                path = pesos.write_item("posts", fields, body, known)
                if path:
                    added += 1
                    print(f"+ {path.name}")
            except Exception as e:
                print(f"x {entry.get('link')}: {e}")
    print(f"Updates: {added} new.")
    return added


if __name__ == "__main__":
    run()
