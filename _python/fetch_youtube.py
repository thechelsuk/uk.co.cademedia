"""YouTube → _videos/

Reads each channel's public RSS feed (latest 15 uploads, no API key needed).
Channels are listed under `sources.youtube_channels` in _config.yml.
Videos from the clips channel are marked `type: clip`, and Shorts get
`short: true`, so the site can show them apart.

  python _python/fetch_youtube.py
"""
from __future__ import annotations

import feedparser

import pesos

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"


def is_short(entry) -> bool:
    return "/shorts/" in (entry.get("link") or "")


def to_item(entry, channel: str = "main") -> tuple[dict, str]:
    """Front matter and body for one feed entry."""
    video_id = entry.get("yt_videoid")
    stats = entry.get("media_statistics") or {}
    description = (entry.get("summary") or "").strip()
    fields = {
        "source_id": video_id,
        "title": entry.get("title", "").strip(),
        "date": pesos.to_datetime(entry.get("published")),
        "link": entry.get("link") or f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "channel": channel,
        "source": "youtube-clips" if channel == "clips" else "youtube",
        "short": is_short(entry),
    }
    if channel == "clips":
        # Overrides the collection defaults, so these sit with the clips
        fields.update(type="clip", type_label="YouTube Clip", categories=["clip", "youtube"])
    if stats.get("views"):
        fields["views"] = int(stats["views"])
    chapters, rest = pesos.split_chapters(description)
    if chapters:
        fields["chapters"] = chapters
    return fields, pesos.text_to_markdown(rest)


def run() -> int:
    channels = pesos.load_sources()["youtube_channels"]
    known = pesos.existing_ids(pesos.ROOT / "_videos")
    added = 0
    for ch in channels:
        feed = feedparser.parse(FEED.format(ch["id"]))
        if not feed.entries:
            print(f"No entries in the YouTube feed for {ch['name']}.")
            continue
        for entry in feed.entries:
            try:
                fields, body = to_item(entry, ch["name"])
                path = pesos.write_item("videos", fields, body, known)
                if path:
                    added += 1
                    print(f"+ {path.name}")
            except Exception as e:  # one bad entry should not stop the rest
                print(f"x {entry.get('link')}: {e}")
    print(f"YouTube: {added} new.")
    return added


if __name__ == "__main__":
    run()
