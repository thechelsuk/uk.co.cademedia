"""Offline tests for the PESOS importers (no network)."""
import datetime as dt
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fetch_instagram  # noqa: E402
import fetch_podcast  # noqa: E402
import fetch_tiktok  # noqa: E402
import fetch_updates  # noqa: E402
import fetch_youtube  # noqa: E402
import pesos  # noqa: E402


class Entry(dict):
    """Stand-in for a feedparser entry (dict keys + attributes)."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e


def front_matter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


# ---------- pesos ----------

class TestSlugify:
    def test_basic(self):
        assert pesos.slugify("Ep 154: What Happened, Cannondale?") == "ep-154-what-happened-cannondale"

    def test_accents_and_quotes(self):
        assert pesos.slugify("Pogačar Filmed ‘Riding Recklessly’") == "pogacar-filmed-riding-recklessly"

    def test_drops_hashtags(self):
        assert pesos.slugify("Big day out #cycling #bike") == "big-day-out"

    def test_cuts_at_word_boundary(self):
        slug = pesos.slugify("word " * 30, max_len=20)
        assert len(slug) <= 20 and not slug.endswith("-")

    def test_empty(self):
        assert pesos.slugify("") == "item"


class TestText:
    def test_first_line_skips_blank_and_hashtags(self):
        assert pesos.first_line("\n\nThe recce doesn't always work #fyp #bike\nmore") == "The recce doesn't always work"

    def test_summary_skips_ads_links_and_timestamps(self):
        text = ("EXCLUSIVE NordVPN Deal ➼ <https://nordvpn.com/wildones>\n"
                "Thanks to Garmin for supporting the podcast!\n"
                "00:57 tribute to a fallen comrade\n"
                "email us at wildonespodcast@cademedia.co.uk\n"
                "This week the lads debate whether wearing a helmet is safe.")
        assert pesos.summary_line(text) == "This week the lads debate whether wearing a helmet is safe."

    def test_summary_skips_contact_boilerplate(self):
        text = ("Or you can send us a voice note on Whatsapp: +44 7860 860 213\n"
                "Join the CADE Club on Patreon for bonus episodes every week\n"
                "Learn more about your ad choices. Visit podcastchoices.com/adchoices")
        assert pesos.summary_line(text) is None

    def test_repeated_lines_are_boilerplate(self):
        notes = [f"Episode {i} is about bikes and more bikes\nThanks and see you next time." for i in range(5)]
        boiler = pesos.repeated_lines(notes)
        assert boiler == {"Thanks and see you next time."}
        assert pesos.summary_line("Thanks and see you next time.", boilerplate=boiler) is None

    def test_summary_none_when_nothing_fits(self):
        assert pesos.summary_line("00:00 intro\nhttps://example.com") is None

    def test_clean_html_strips_scripts_and_attrs(self):
        html = '<p onclick="x()">Hi <script>bad()</script><a href="https://a.b" style="c">link</a></p>'
        out = pesos.clean_html(html)
        assert "<script" not in out and "onclick" not in out and "style" not in out
        assert '<a href="https://a.b">link</a>' in out


class TestDates:
    def test_iso_z(self):
        assert pesos.to_datetime("2026-10-29T13:00:24+00:00") == dt.datetime(2026, 10, 29, 13, 0, 24, tzinfo=dt.timezone.utc)

    def test_instagram_offset(self):
        assert pesos.to_datetime("2026-10-01T09:30:00+0000").utcoffset() == dt.timedelta(0)

    def test_unix(self):
        assert pesos.to_datetime(0).year == 1970

    def test_struct_time(self):
        import time
        assert pesos.to_datetime(time.gmtime(86400)).day == 2


class TestWriteItem:
    def fields(self, **kw):
        base = {"source_id": "abc", "title": "Hello World", "date": dt.datetime(2026, 1, 2, 3, 4, tzinfo=dt.timezone.utc)}
        base.update(kw)
        return base

    def test_writes_file_with_front_matter_and_body(self, tmp_path):
        path = pesos.write_item("videos", self.fields(), "Body text", root=tmp_path)
        assert path.name == "2026-01-02-hello-world.md"
        fm = front_matter(path)
        assert fm["source_id"] == "abc" and fm["title"] == "Hello World"
        assert str(fm["date"]).startswith("2026-01-02 03:04:00")
        assert path.read_text().rstrip().endswith("Body text")

    def test_skips_known_id_and_keeps_hand_edits(self, tmp_path):
        path = pesos.write_item("videos", self.fields(), "Original", root=tmp_path)
        path.write_text(path.read_text().replace("Original", "Edited by hand"))
        again = pesos.write_item("videos", self.fields(title="New title"), "Changed", root=tmp_path)
        assert again is None
        assert "Edited by hand" in path.read_text()
        assert len(list((tmp_path / "_videos").glob("*.md"))) == 1

    def test_same_day_same_title_gets_suffix(self, tmp_path):
        a = pesos.write_item("tiktoks", self.fields(source_id="1"), root=tmp_path)
        b = pesos.write_item("tiktoks", self.fields(source_id="2"), root=tmp_path)
        assert a.name != b.name and b.name.endswith("-2.md")

    def test_existing_ids_reads_quoted_ids(self, tmp_path):
        folder = tmp_path / "_instagram"
        folder.mkdir()
        (folder / "x.md").write_text("---\nsource_id: '17890'\ntitle: x\n---\n")
        assert pesos.existing_ids(folder) == {"17890"}


# ---------- YouTube ----------

def yt_entry(**kw):
    e = Entry(
        title="This Bike Isn’t Quite What It Seems... Wilier Rapida First Look",
        link="https://www.youtube.com/watch?v=abcdefghijk",
        published="2026-10-26T17:00:00+00:00",
        yt_videoid="abcdefghijk",
        media_statistics={"views": "12345"},
        summary="Wilier's Rapida is here.",
    )
    e.update(kw)
    return e


class TestYouTube:
    def test_main_channel_video(self):
        fields, body = fetch_youtube.to_item(yt_entry())
        assert fields["source_id"] == "abcdefghijk"
        assert fields["thumbnail"] == "https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg"
        assert fields["views"] == 12345 and fields["short"] is False
        assert fields["channel"] == "main" and "type" not in fields
        assert body == "Wilier's Rapida is here."

    def test_short(self):
        fields, _ = fetch_youtube.to_item(yt_entry(link="https://www.youtube.com/shorts/abcdefghijk"))
        assert fields["short"] is True

    def test_clips_channel_is_a_clip(self):
        fields, _ = fetch_youtube.to_item(yt_entry(), "clips")
        assert fields["type"] == "clip" and "clip" in fields["categories"]


# ---------- Podcast ----------

class TestPodcast:
    def test_durations(self):
        assert fetch_podcast.format_duration("3725") == "1h 2m"
        assert fetch_podcast.format_duration("00:45:10") == "45m"
        assert fetch_podcast.format_duration("59:25") == "59m"
        assert fetch_podcast.format_duration("") is None

    def test_episode(self):
        e = Entry(
            id="bf5712ee", title="Ep 154: What Happened, Cannondale?",
            published="2026-10-29T13:00:00+00:00",
            enclosures=[{"href": "https://x/ep.mp3", "type": "audio/mpeg"}],
            itunes_episode="154", itunes_duration="3725",
            content=[{"value": "<p>Sponsored by a deal https://x.y</p><p>This week the lads chat about bikes and more.</p>"}],
        )
        fields, body = fetch_podcast.to_item(e)
        assert fields["audio"] == "https://x/ep.mp3"
        assert fields["episode"] == 154 and fields["duration"] == "1h 2m"
        assert fields["description"] == "This week the lads chat about bikes and more."
        assert "This week the lads" in body


# ---------- TikTok ----------

class TestTikTok:
    def test_cover_prefers_cover(self):
        e = {"thumbnails": [{"id": "dynamicCover", "url": "d"}, {"id": "cover", "url": "c"}]}
        assert fetch_tiktok.cover_url(e) == "c"

    def test_item(self):
        e = {"id": 7698717351000280352, "description": "The recce doesn't always work... #cycling",
             "timestamp": 1792497302, "url": "https://www.tiktok.com/@cade_media/video/7698717351000280352",
             "view_count": 999}
        fields, body = fetch_tiktok.to_item(e, "cade_media")
        assert fields["source_id"] == "7698717351000280352"
        assert fields["title"] == "The recce doesn't always work..."
        assert fields["thumbnail"] == "/assets/images/tiktok/7698717351000280352.jpg"
        assert fields["views"] == 999 and "#cycling" in body


# ---------- Instagram ----------

class TestInstagram:
    def test_video_uses_thumbnail(self):
        assert fetch_instagram.image_url({"media_type": "VIDEO", "thumbnail_url": "t", "media_url": "m"}) == "t"
        assert fetch_instagram.image_url({"media_type": "IMAGE", "media_url": "m"}) == "m"

    def test_item(self):
        post = {"id": "1789", "caption": "New kit day 🔥\n#cade", "media_type": "CAROUSEL_ALBUM",
                "permalink": "https://www.instagram.com/p/xyz/", "timestamp": "2026-10-01T09:30:00+0000"}
        fields, _ = fetch_instagram.to_item(post)
        assert fields["title"] == "New kit day 🔥"
        assert fields["media_type"] == "carousel_album"
        assert fields["thumbnail"] == "/assets/images/instagram/1789.jpg"

    def test_no_token_is_a_no_op(self, monkeypatch):
        monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
        assert fetch_instagram.run() == 0


# ---------- Markdown + chapters ----------

class TestMarkdown:
    def test_links_and_line_breaks(self):
        md = pesos.text_to_markdown("Merch: https://wearethewildones.com/\nPatreon too")
        assert "<https://wearethewildones.com/>" in md
        assert md.splitlines()[0].endswith("  ")  # hard line break

    def test_escapes_markdown_and_liquid_ish_text(self):
        md = pesos.text_to_markdown("#cycling is *great* and_so_on [ad]")
        assert md.startswith("\\#cycling")
        assert "\\*great\\*" in md and "\\[ad\\]" in md and "and\\_so\\_on" in md

    def test_url_with_underscores_is_untouched(self):
        md = pesos.text_to_markdown("see https://x.com/a_b_c.")
        assert "<https://x.com/a_b_c>." in md


class TestChapters:
    def test_extracts_chapters(self):
        text = "Intro words\n00:00 disaster planning\n04:50 PicnicPostNL in crisis\n1:02:05 - the end\nOutro"
        chapters, rest = pesos.split_chapters(text)
        assert [c["seconds"] for c in chapters] == [0, 290, 3725]
        assert chapters[1] == {"seconds": 290, "title": "PicnicPostNL in crisis"}
        assert chapters[2]["title"] == "the end"
        assert rest == "Intro words\nOutro"

    def test_single_timestamp_is_not_chapters(self):
        text = "Watch from 02:10 for the crash"
        assert pesos.split_chapters(text) == ([], text)

    def test_youtube_item_has_chapters_and_source(self):
        e = yt_entry(summary="Big news\n00:00 intro\n03:15 the bike\nhttps://x.y")
        fields, body = fetch_youtube.to_item(e)
        assert len(fields["chapters"]) == 2 and fields["source"] == "youtube"
        assert "00:00" not in body and "<https://x.y>" in body
        clip, _ = fetch_youtube.to_item(e, "clips")
        assert clip["source"] == "youtube-clips"


# ---------- Updates (any RSS/Atom feed, e.g. Tumblr) ----------

class TestUpdates:
    def entry(self, **kw):
        e = Entry(
            id="https://cademedia.tumblr.com/post/123",
            link="https://cademedia.tumblr.com/post/123",
            title="",
            published="2026-10-28T09:15:00+00:00",
            summary='<p>Big week of filming ahead.</p><p><img src="https://64.media.tumblr.com/a.jpg" alt="x"> Stay tuned!</p>',
        )
        e.update(kw)
        return e

    def test_untitled_post_is_a_note(self):
        fields, body = fetch_updates.to_item(self.entry(), "tumblr")
        assert fields["note"] is True
        assert fields["title"] == "Big week of filming ahead."
        assert fields["source_id"] == "https://cademedia.tumblr.com/post/123"
        assert fields["image"] == "https://64.media.tumblr.com/a.jpg"
        assert fields["via"] == "tumblr" and fields["render_with_liquid"] is False
        assert "Stay tuned!" in body and "<img" not in body

    def test_tumblr_auto_title_from_text_is_still_a_note(self):
        fields, _ = fetch_updates.to_item(self.entry(title="Big week of filming…"), "tumblr")
        assert fields["note"] is True

    def test_real_title_is_kept(self):
        fields, _ = fetch_updates.to_item(self.entry(title="Tour of Britain plans"), "tumblr")
        assert fields["note"] is False and fields["title"] == "Tour of Britain plans"

    def test_title_entities_are_decoded(self):
        fields, _ = fetch_updates.to_item(self.entry(title="Where&rsquo;s that comment?"), "tumblr")
        assert fields["title"] == "Where’s that comment?"

    def test_no_feeds_configured_is_a_no_op(self, monkeypatch):
        monkeypatch.setattr(fetch_updates.pesos, "load_sources", lambda: {})
        assert fetch_updates.run() == 0
