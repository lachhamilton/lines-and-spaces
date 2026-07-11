# Lines & Spaces

Static blog for `https://linesandspaces.net`.

This project is intentionally plain HTML, CSS, and small JavaScript. There is no
framework or package install. Publishing runs a small Python generator.

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

Point Obsidian at `posts/` as the writing workspace.

- Drafts live in `posts/drafts/`.
- Published Markdown sources live in `posts/published/`.

Use front matter:

```md
---
title: "Post Title"
date: "2026-06-03"
slug: "post-title"
hook: "Optional one-liner for the Facebook/Threads announcement."
---
```

`hook` is optional — when it's missing, the announcement uses the post's
first paragraph. `topic: "..."` is also optional: it sets the Threads topic
tag for that post (default "Tech Threads"; no periods or ampersands).

### Images

Save images to `posts/images/` and reference them with normal Markdown:

```md
![A photo of a piano](../images/piano.jpg)
```

Any local path form works (`../images/piano.jpg`, `images/piano.jpg`, or just
`piano.jpg`) — the generator resolves by filename to `/posts/images/` on the
site, so use whichever path previews best in your editor. An image alone on
its own line renders full-width; images inside a sentence render inline.
Full `https://` URLs are left as-is.

Anything in `posts/published/` is published — the folder is the only switch.
To unpublish, move the file back to `posts/drafts/`.

To publish a post:

1. Move the Markdown file from `posts/drafts/` to `posts/published/`.
2. Run:

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
