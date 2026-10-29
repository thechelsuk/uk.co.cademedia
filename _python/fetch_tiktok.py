"""TikTok → _tiktoks/

TikTok has no feed or simple public API, so this uses yt-dlp to list the
account's latest videos. Cover images are saved to assets/images/tiktok/
because TikTok's own image links expire after a few days.

TikTok sometimes blocks requests from cloud servers (GitHub Actions). When
that happens the script prints a warning and exits cleanly; running it
locally and committing the result works as a fallback.

  python _python/fetch_tiktok.py [--limit 30]
"""
from __future__ import annotations

import argparse

import pesos

IMAGE_DIR = pesos.ROOT / "assets/images/tiktok"


def cover_url(entry) -> str | None:
    thumbs = {t.get("id"): t.get("url") for t in entry.get("thumbnails") or []}
    return thumbs.get("cover") or thumbs.get("originCover") or entry.get("thumbnail") or (
        next(iter(thumbs.values()), None))


def to_item(entry, user: str) -> tuple[dict, str]:
    video_id = str(entry["id"])
    caption = entry.get("description") or entry.get("title") or ""
    fields = {
        "source_id": video_id,
        "title": pesos.first_line(caption, 100) or "TikTok",
        "date": pesos.to_datetime(entry.get("timestamp")),
        "link": entry.get("url") or f"https://www.tiktok.com/@{user}/video/{video_id}",
        "thumbnail": f"/assets/images/tiktok/{video_id}.jpg",
    }
    if entry.get("view_count"):
        fields["views"] = int(entry["view_count"])
    return fields, pesos.text_to_markdown(caption)


def list_videos(user: str, limit: int) -> list[dict]:
    import yt_dlp

    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "extract_flat": True, "playlistend": limit}
    info = yt_dlp.YoutubeDL(opts).extract_info(f"https://www.tiktok.com/@{user}", download=False)
    return [e for e in (info.get("entries") or []) if e and e.get("id")]


def run(limit: int = 30) -> int:
    user = pesos.load_sources()["tiktok_user"]
    try:
        entries = list_videos(user, limit)
    except Exception as e:
        print(f"::warning::TikTok listing failed (often blocked from cloud runners): {e}")
        return 0
    known = pesos.existing_ids(pesos.ROOT / "_tiktoks")
    added = 0
    for entry in entries:
        if str(entry["id"]) in known:
            continue
        try:
            fields, body = to_item(entry, user)
            url = cover_url(entry)
            if not url or not pesos.download(url, IMAGE_DIR / f"{fields['source_id']}.jpg", max_width=540):
                print(f"x No cover for {fields['link']}, skipping for now")
                continue
            path = pesos.write_item("tiktoks", fields, body, known)
            if path:
                added += 1
                print(f"+ {path.name}")
        except Exception as e:
            print(f"x {entry.get('url')}: {e}")
    print(f"TikTok: {added} new of {len(entries)}.")
    return added


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=30, help="how many recent videos to check")
    run(parser.parse_args().limit)
