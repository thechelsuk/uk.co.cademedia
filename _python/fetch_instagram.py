"""Instagram → _instagram/

Uses the Instagram API (Instagram Login) for the account's own posts. It
needs a long-lived access token in the INSTAGRAM_ACCESS_TOKEN environment
variable (a GitHub Actions secret). Without one it does nothing.

Tokens last 60 days. `--refresh` swaps the current token for a fresh one
and prints it, so it can be saved back into the secret.

  INSTAGRAM_ACCESS_TOKEN=... python _python/fetch_instagram.py [--limit 24]
"""
from __future__ import annotations

import argparse
import os

import requests

import pesos

API = "https://graph.instagram.com"
FIELDS = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"
IMAGE_DIR = pesos.ROOT / "assets/images/instagram"


def image_url(post: dict) -> str | None:
    """Videos have a thumbnail_url; images and carousels a media_url."""
    if post.get("media_type") == "VIDEO":
        return post.get("thumbnail_url")
    return post.get("media_url")


def to_item(post: dict) -> tuple[dict, str]:
    caption = post.get("caption") or ""
    fields = {
        "source_id": str(post["id"]),
        "title": pesos.first_line(caption, 100) or "Instagram post",
        "date": pesos.to_datetime(post["timestamp"]),
        "link": post["permalink"],
        "thumbnail": f"/assets/images/instagram/{post['id']}.jpg",
        "media_type": (post.get("media_type") or "IMAGE").lower(),
    }
    return fields, pesos.text_to_markdown(caption)


def fetch_posts(token: str, limit: int) -> list[dict]:
    r = requests.get(f"{API}/me/media",
                     params={"fields": FIELDS, "limit": limit, "access_token": token}, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def refresh(token: str) -> None:
    r = requests.get(f"{API}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(f"New token (expires in {data.get('expires_in', 0) // 86400} days):")
    print(data["access_token"])


def run(limit: int = 24) -> int:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        print("Instagram: no INSTAGRAM_ACCESS_TOKEN set, skipping.")
        return 0
    try:
        posts = fetch_posts(token, limit)
    except requests.RequestException as e:
        print(f"::warning::Instagram fetch failed: {e}")
        return 0
    known = pesos.existing_ids(pesos.ROOT / "_instagram")
    added = 0
    for post in posts:
        if str(post.get("id")) in known:
            continue
        try:
            fields, body = to_item(post)
            url = image_url(post)
            if not url or not pesos.download(url, IMAGE_DIR / f"{fields['source_id']}.jpg"):
                continue
            path = pesos.write_item("instagram", fields, body, known)
            if path:
                added += 1
                print(f"+ {path.name}")
        except Exception as e:
            print(f"x {post.get('permalink')}: {e}")
    print(f"Instagram: {added} new of {len(posts)}.")
    return added


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--refresh", action="store_true", help="print a refreshed access token")
    args = parser.parse_args()
    if args.refresh:
        refresh(os.environ["INSTAGRAM_ACCESS_TOKEN"])
    else:
        run(args.limit)
