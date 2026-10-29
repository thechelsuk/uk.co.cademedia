"""The Wild Ones Podcast → _podcasts/

Reads the podcast RSS feed; every episode gets its own page on the site.

  python _python/fetch_podcast.py
"""
from __future__ import annotations

import re

import feedparser

import pesos


def format_duration(value) -> str | None:
    """'3725' or '1:02:05' → '1h 2m'; '00:45:10' → '45m'."""
    if not value:
        return None
    value = str(value).strip()
    if re.fullmatch(r"\d+", value):
        seconds = int(value)
    else:
        parts = [int(p) for p in value.split(":") if p.isdigit()]
        seconds = 0
        for p in parts:
            seconds = seconds * 60 + p
    h, m = divmod(seconds // 60, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m" if m else None


def audio_url(entry) -> str | None:
    for enc in entry.get("enclosures") or []:
        if (enc.get("type") or "").startswith("audio") or enc.get("href", "").endswith(".mp3"):
            return enc.get("href")
    return None


def to_item(entry, boilerplate: set[str] | None = None) -> tuple[dict, str]:
    content = entry.get("content") or []
    html = content[0].get("value") if content else entry.get("summary", "")
    fields = {
        "source_id": (entry.get("id") or entry.get("guid") or audio_url(entry)).strip(),
        "title": entry.get("title", "").strip(),
        "date": pesos.to_datetime(entry.get("published_parsed") or entry.get("published")),
        "audio": audio_url(entry),
    }
    if entry.get("itunes_episode"):
        fields["episode"] = int(entry["itunes_episode"])
    duration = format_duration(entry.get("itunes_duration"))
    if duration:
        fields["duration"] = duration
    image = (entry.get("image") or {}).get("href")
    if image:
        fields["image"] = image
    chapters, body = pesos.split_chapters(pesos.html_to_markdown(html))
    if chapters:
        fields["chapters"] = chapters
    summary = pesos.summary_line(body, boilerplate=boilerplate)
    if summary:
        fields["description"] = summary
    return fields, body


def run() -> int:
    url = pesos.load_sources()["podcast_feed"]
    feed = feedparser.parse(url)
    if not feed.entries:
        print("No entries in the podcast feed.")
        return 0
    known = pesos.existing_ids(pesos.ROOT / "_podcasts")
    # Lines repeated across episodes are sign-offs, not summaries
    boilerplate = pesos.repeated_lines([to_item(e)[1] for e in feed.entries])
    added = 0
    for entry in feed.entries:
        try:
            fields, body = to_item(entry, boilerplate)
            path = pesos.write_item("podcasts", fields, body, known)
            if path:
                added += 1
                print(f"+ {path.name}")
        except Exception as e:
            print(f"x {entry.get('title')}: {e}")
    print(f"Podcast: {added} new of {len(feed.entries)}.")
    return added


if __name__ == "__main__":
    run()
