# Lines & Spaces

Static blog for `https://linesandspaces.net`.

This project is intentionally plain HTML, CSS, and small JavaScript. There is no
framework, package install, or build step.

## Run Locally

From this folder:

```sh
python3 -m http.server 4174
```

Then open:

```txt
http://localhost:4174
```

## Writing

Write drafts as Markdown files in `drafts/`. Use front matter:

```md
---
title: "Post Title"
date: "2026-06-03"
slug: "post-title"
status: "draft"
---
```

To publish a post:

1. Move the Markdown file from `drafts/` to `posts/`.
2. Change `status` to `"published"`.
3. Run:

```sh
python3 scripts/build-writing.py
```

The script generates canonical `linesandspaces.net` links and:

- `index.html` - Lines & Spaces index
- `<year>/<month>/<slug>/index.html` - post pages
- `feed.xml` - RSS feed

## Vercel

Suggested project settings:

- Framework preset: `Other`
- Build command: leave blank
- Output directory: leave blank
- Install command: leave blank

The production domain is:

- `linesandspaces.net`
- `www.linesandspaces.net` redirects to the apex domain
