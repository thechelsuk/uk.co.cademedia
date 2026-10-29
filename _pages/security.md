---
title: Security
permalink: /security/
kicker: The small print
intro: How to tell us about a security problem with this website.
---

## Reporting a problem

If you think you've found a security issue with this website, please email [{{ site.legal.email }}](mailto:{{ site.legal.email }}) with:

- what you found and where (the page or URL),
- the steps to reproduce it, and
- what you think the impact is.

We'll acknowledge your report as soon as we can and keep you updated while we look into it. Please give us reasonable time to fix the issue before sharing it publicly.

## Please don't

- access, change or delete data that isn't yours,
- run tests that could disrupt the site for others (such as denial-of-service), or
- use social engineering or phishing against the team.

## Scope

This covers **{{ site.url | remove: 'https://' }}**. Issues with YouTube, TikTok, Instagram, Bluesky, Patreon, our merch shop or our podcast host should go to those services directly.

## How the site is built

This is a static website — there are no logins, databases or forms on it. It's built automatically and hosted on GitHub Pages over HTTPS. Dependencies are kept up to date automatically.

Our [security.txt]({{ '/.well-known/security.txt' | relative_url }}) has these contact details in a machine-readable form.
