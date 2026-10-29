# cademedia.co.uk

Jekyll site for CADE Media. Videos, podcast episodes, TikToks and Instagram
posts are pulled in automatically (PESOS) by Python scripts in `_python/`,
run on a schedule by GitHub Actions.

## Run locally

```bash
bundle install
bundle exec jekyll serve --port 2023 --livereload --livereload-port 35723
```

Then open <http://localhost:2023>.

## Content

| What | Where | How it gets there |
| --- | --- | --- |
| Pages | `_pages/` | By hand |
| Updates (short posts in the feed) | `_posts/` | `fetch_updates.py` from any RSS/Atom feed, or by hand |
| YouTube videos (main + clips channel) | `_videos/` | `fetch_youtube.py` |
| The Wild Ones Podcast | `_podcasts/` (each episode has a page) | `fetch_podcast.py` |
| TikTok | `_tiktoks/` + `assets/images/tiktok/` | `fetch_tiktok.py` |
| Instagram | `_instagram/` + `assets/images/instagram/` | `fetch_instagram.py` |
| Sponsored posts | `_sponsors/` | By hand (see below) |

Every imported item has its own page (e.g. `/video/<title>/`,
`/wild-ones-podcast/<title>/`, `/clips/tiktok/<title>/`, `/instagram/<title>/`)
with the embed or player, the description, and clickable chapter markers
pulled from the timestamps in the description.

Every item gets `type`, `type_label`, `source` and `categories` from the
collection defaults in `_config.yml`, so imported files stay small. `source`
picks the avatar and name shown in the feed (`_data/sources.yml`). Importers
never overwrite an existing file (they match on its `source_id`), so hand
edits are kept.

Feed sources (channel ids, podcast RSS, usernames) live under `sources:` in
`_config.yml`.

- `/feed/` — everything as one timeline, newest first, 20 per page
  (`/feed/page/2/` …), with a page set per type (`/feed/video/`,
  `/feed/podcast/`, `/feed/clip/`, `/feed/instagram/`, `/feed/post/`).
  The feed is the blog: written updates live there, and `/blog/` redirects
  to `/feed/post/`. Built
  by `_plugins/feed_pages.rb`; page size and filters are in `_config.yml`.
- `/feed/all.xml` — RSS of everything (latest 100)
- `/feed.xml` — RSS of updates only

The header has a light / dark / system theme toggle; the choice is saved in
the browser.

## Importers

```bash
python3 -m venv .venv
.venv/bin/pip install -r _python/requirements.txt
.venv/bin/python _python/fetch_youtube.py
.venv/bin/python _python/fetch_podcast.py
.venv/bin/python _python/fetch_tiktok.py
.venv/bin/python _python/fetch_updates.py
INSTAGRAM_ACCESS_TOKEN=... .venv/bin/python _python/fetch_instagram.py
.venv/bin/python -m pytest _python/test
```

Notes:

- **Updates** come from any RSS or Atom feed listed under
  `sources.updates_feeds` in `_config.yml`, so the team can post from an app
  (Tumblr, Bluesky, Mastodon, Micro.blog…) instead of writing Markdown.
  Posts without a real title get `note: true` and show like a tweet.
- **YouTube** uses the public channel RSS, which only lists the latest 15
  uploads per channel.
- **TikTok** has no feed, so it uses `yt-dlp`. TikTok sometimes blocks cloud
  servers; if the scheduled run warns, run it locally and commit.
- **Instagram** needs a long-lived token from the Instagram API (Instagram
  Login) saved as the `INSTAGRAM_ACCESS_TOKEN` repository secret. Tokens last
  60 days: `fetch_instagram.py --refresh` prints a new one to save back.

## GitHub Actions

- `fetch-feeds.yml` — every 30 minutes (at :13 and :43): runs the importers,
  commits new items, redeploys
- `deploy-pages.yml` — builds and deploys to GitHub Pages on push to `main`,
  and daily so sponsored posts switch on and off on time
- `test.yml` — importer tests and a site build, on pull requests and changes
- `dependency-review.yml` — checks new dependencies on pull requests
- `.github/dependabot.yml` — daily updates for pip, bundler and actions

Shared steps live in `.github/actions/`: `python-setup`, `jekyll-build` and
`commit-and-push`. The footer shows the 6-character commit the site was built
from (linked to GitHub in Actions).

Privacy, Terms and Security pages and `/.well-known/security.txt` use the
contact email in `legal:` in `_config.yml`.

## SEO and AI

Titles (≤60 characters), descriptions (70–160, with sponsor reads, links and
timestamps skipped), share images and noindex for mock content are worked
out per page by `_plugins/seo_data.rb`; front matter `seo_title`,
`description` or `image` override them. `_includes/seo.html` writes the meta,
Open Graph and Twitter tags, and `_includes/structured-data.html` the
schema.org JSON-LD (VideoObject with chapter key moments, PodcastEpisode,
SocialMediaPosting, breadcrumbs, and the organisation with its profiles).
`robots.txt` welcomes search and AI crawlers (with notes on opting out of AI
training) and `llms.txt` gives AI assistants a summary with key links.

## Sponsored posts

Each file in `_sponsors/` is one sponsored post. It shows 3rd on every feed
page (including filtered and later pages) while today is between its `start`
and `end` dates; with several active they rotate page by page. Fields:
`sponsor`, `title`, `start`, `end`, `link`, `cta`, `image`, optional `logo`,
and the post text as the body. The site rebuilds daily so they switch on and
off on time. Sponsored posts aren't counted in the sidebar or included in RSS.

## Mock content

Some items are placeholders for show and have `mock: true` in their front
matter (8 Instagram posts, 2 updates and the Garmin sponsored post). Remove them once real content flows:

```bash
grep -rl '^mock: true' _instagram _posts _sponsors | xargs rm
rm assets/images/instagram/mock-*.jpg
```
