#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "posts"
PUBLISHED_POSTS = POSTS / "published"
BLOG_SITE_URL = "https://linesandspaces.net"
SITE_NAME = "Lines & Spaces"
SITE_DESCRIPTION = "Notes on Apple, AI, apps, teaching, music, and the places those things overlap."
ASSET_VERSION = "20260612-paragraph-rhythm"
FAVICON_VERSION = "20260608-wordmark"
OG_IMAGE_URL = f"{BLOG_SITE_URL}/assets/og-image.png"
OG_IMAGE_WIDTH = "1729"
OG_IMAGE_HEIGHT = "910"


@dataclass
class Post:
    title: str
    date: str
    slug: str
    source: Path
    body: str

    @property
    def date_obj(self) -> datetime:
        return datetime.strptime(self.date, "%Y-%m-%d")

    @property
    def year(self) -> str:
        return self.date_obj.strftime("%Y")

    @property
    def month(self) -> str:
        return self.date_obj.strftime("%m")

    @property
    def url_path(self) -> str:
        return f"/{self.year}/{self.month}/{self.slug}"

    @property
    def url(self) -> str:
        return f"{BLOG_SITE_URL}{self.url_path}"

    @property
    def date_display(self) -> str:
        return self.date_obj.strftime("%-d %B %Y")

    @property
    def date_rfc822(self) -> str:
        dt = self.date_obj.replace(tzinfo=timezone.utc)
        return format_datetime(dt)


def parse_front_matter(path: Path) -> Post:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} is missing front matter")

    _, raw_meta, body = text.split("---\n", 2)
    meta: dict[str, str] = {}

    for line in raw_meta.splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')

    for required in ("title", "date", "slug"):
        if required not in meta:
            raise ValueError(f"{path} is missing {required!r} front matter")

    return Post(
        title=meta["title"],
        date=meta["date"],
        slug=meta["slug"],
        source=path,
        body=body.strip(),
    )


def render_inline(text: str, footnote_numbers: dict[str, int], footnote_prefix: str = "") -> str:
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)

    def footnote_ref(match: re.Match[str]) -> str:
        marker = match.group(1)
        number = footnote_numbers.setdefault(marker, len(footnote_numbers) + 1)
        return f'<sup id="{footnote_prefix}fnref-{number}"><a href="#{footnote_prefix}fn-{number}">{number}</a></sup>'

    return re.sub(r"\[\^([^\]]+)\]", footnote_ref, text)


def render_markdown(markdown: str, footnote_prefix: str = "") -> str:
    lines = markdown.splitlines()
    blocks: list[str] = []
    footnotes: dict[str, str] = {}
    footnote_numbers: dict[str, int] = {}
    paragraph: list[str] = []
    list_items: list[str] = []
    quote_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(line.strip() for line in paragraph)
            blocks.append(f"<p>{render_inline(text, footnote_numbers, footnote_prefix)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            items = "".join(f"<li>{render_inline(item, footnote_numbers, footnote_prefix)}</li>" for item in list_items)
            blocks.append(f"<ul>{items}</ul>")
            list_items = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            text = " ".join(line.strip() for line in quote_lines)
            blocks.append(f"<blockquote><p>{render_inline(text, footnote_numbers, footnote_prefix)}</p></blockquote>")
            quote_lines = []

    for raw_line in lines:
        line = raw_line.rstrip()

        footnote = re.match(r"^\[\^([^\]]+)\]:\s*(.+)$", line)
        if footnote:
            flush_paragraph()
            flush_list()
            flush_quote()
            footnotes[footnote.group(1)] = footnote.group(2)
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_quote()
            continue

        heading = re.match(r"^(#{2,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            flush_quote()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{render_inline(heading.group(2), footnote_numbers, footnote_prefix)}</h{level}>")
            continue

        if line.startswith("- "):
            flush_paragraph()
            flush_quote()
            list_items.append(line[2:].strip())
            continue

        if line.startswith("> "):
            flush_paragraph()
            flush_list()
            quote_lines.append(line[2:].strip())
            continue

        paragraph.append(line)

    flush_paragraph()
    flush_list()
    flush_quote()

    if footnotes:
        items = []
        for marker, number in sorted(footnote_numbers.items(), key=lambda item: item[1]):
            if marker in footnotes:
                items.append(
                    f'<li id="{footnote_prefix}fn-{number}">{render_inline(footnotes[marker], footnote_numbers, footnote_prefix)} '
                    f'<a href="#{footnote_prefix}fnref-{number}" aria-label="Back to reference">back</a></li>'
                )
        if items:
            blocks.append(f'<section class="post-footnotes" aria-label="Footnotes"><ol>{"".join(items)}</ol></section>')

    return "\n".join(blocks)


def excerpt(markdown: str) -> str:
    clean = re.sub(r"^\[\^[^\]]+\]:.*$", "", markdown, flags=re.MULTILINE).strip()
    first = re.split(r"\n\s*\n", clean, maxsplit=1)[0]
    first = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", first)
    first = re.sub(r"[*_`>#]", "", first)
    return " ".join(first.split())


def page_head(title: str, description: str, href_prefix: str = ".", canonical_url: str | None = None, og_type: str = "website") -> str:
    canonical = f'\n    <link rel="canonical" href="{html.escape(canonical_url, quote=True)}" />' if canonical_url else ""
    og_url = f'\n    <meta property="og:url" content="{html.escape(canonical_url, quote=True)}" />' if canonical_url else ""
    social = f"""
    <meta property="og:site_name" content="{html.escape(SITE_NAME, quote=True)}" />
    <meta property="og:type" content="{og_type}" />
    <meta property="og:title" content="{html.escape(title, quote=True)}" />
    <meta property="og:description" content="{html.escape(description, quote=True)}" />
    <meta property="og:image" content="{OG_IMAGE_URL}" />
    <meta property="og:image:width" content="{OG_IMAGE_WIDTH}" />
    <meta property="og:image:height" content="{OG_IMAGE_HEIGHT}" />{og_url}
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{html.escape(title, quote=True)}" />
    <meta name="twitter:description" content="{html.escape(description, quote=True)}" />
    <meta name="twitter:image" content="{OG_IMAGE_URL}" />"""
    return f"""<meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description, quote=True)}" />{social}
    <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)" />
    <meta name="theme-color" content="#111111" media="(prefers-color-scheme: dark)" />
    <link rel="icon" type="image/svg+xml" href="{href_prefix}/assets/favicon-lines-spaces.svg?v={FAVICON_VERSION}" />
    <link rel="manifest" href="{href_prefix}/site.webmanifest" />
    <link rel="alternate" type="application/rss+xml" title="Lines &amp; Spaces" href="{BLOG_SITE_URL}/feed.xml" />{canonical}
    <script>
      (() => {{
        try {{
          const theme = localStorage.getItem("lines-spaces-theme");
          if (theme === "dark" || theme === "light") {{
            document.documentElement.dataset.theme = theme;
          }}
        }} catch (_error) {{}}
      }})();
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="{href_prefix}/styles.css?v={ASSET_VERSION}" />
    <script>
      window.va = window.va || function () {{ (window.vaq = window.vaq || []).push(arguments); }};
    </script>
    <script defer src="/_vercel/insights/script.js" data-sdkn="@vercel/analytics" data-sdkv="2.0.1"></script>"""


def shell(
    title: str,
    description: str,
    body: str,
    href_prefix: str = ".",
    canonical_url: str | None = None,
    footer_rss: bool = True,
    og_type: str = "website",
) -> str:
    footer = (
        f"""
      <footer class="site-footer">
        <p class="footer-meta"><a href="{BLOG_SITE_URL}/feed.xml">RSS</a></p>
      </footer>"""
        if footer_rss
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    {page_head(title, description, href_prefix, canonical_url, og_type)}
  </head>
  <body class="writing-page">
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <div class="site-shell writing-shell">
      <header class="site-header writing-header">
        <button class="theme-toggle" type="button" aria-label="Switch to dark mode" aria-pressed="false">
          <span class="theme-toggle-icon" aria-hidden="true"></span>
          <span class="theme-toggle-text">Dark</span>
        </button>
      </header>

      {body}
{footer}
    </div>
    <script src="{href_prefix}/script.js"></script>
  </body>
</html>
"""


def load_posts() -> list[Post]:
    posts = [parse_front_matter(path) for path in PUBLISHED_POSTS.glob("*.md")]
    return sorted(posts, key=lambda post: post.date, reverse=True)


def render_index(posts: list[Post]) -> None:
    items = []
    for post in posts:
        post_body = render_markdown(post.body, f"index-{post.slug}-")
        post_href = post.url
        items.append(
            f"""<article class="writing-list-item">
              <header class="writing-list-header">
                <h2><a href="{post_href}">{html.escape(post.title)}</a></h2>
                <time datetime="{post.date}">{post.date_display}</time>
              </header>
              <div class="post-body writing-list-body">
                {post_body}
                <p class="writing-list-permalink"><a href="{post_href}">Permalink</a></p>
              </div>
            </article>"""
        )

    body = f"""<main id="main-content" class="writing-index">
        <section class="writing-masthead" aria-labelledby="writing-title">
          <h1 id="writing-title" class="writing-wordmark">
            <span>Lines</span>
            <span>&amp;</span>
            <span>Spaces</span>
          </h1>
          <nav class="writing-masthead-links" aria-label="Lines &amp; Spaces links">
            <a href="{BLOG_SITE_URL}/feed.xml">RSS feed</a>
          </nav>
        </section>
        <p class="writing-byline"><a href="https://lachlanhamilton.com">By Lachlan Hamilton</a></p>

        <section class="writing-list" aria-label="Lines & Spaces archive">
          {"".join(items)}
        </section>

        <section class="writing-contact" id="contact" aria-labelledby="writing-contact-title">
          <h2 id="writing-contact-title">Follow along.</h2>
          <div>
            <p>
              New pieces are available through the RSS feed, or by checking this
              page.
            </p>
            <a class="writing-button" href="{BLOG_SITE_URL}/feed.xml">RSS feed</a>
          </div>
        </section>
      </main>"""

    (ROOT / "index.html").write_text(
        shell(
            SITE_NAME,
            SITE_DESCRIPTION,
            body,
            canonical_url=f"{BLOG_SITE_URL}/",
            footer_rss=False,
        ),
        encoding="utf-8",
    )


def render_post(post: Post) -> None:
    post_dir = ROOT / post.year / post.month / post.slug
    if post_dir.exists():
        shutil.rmtree(post_dir)
    post_dir.mkdir(parents=True, exist_ok=True)

    body_html = render_markdown(post.body)
    body = f"""<main id="main-content" class="post-page">
        <article class="post-article">
          <header class="post-header">
            <a class="post-brand" href="{BLOG_SITE_URL}/" aria-label="Lines &amp; Spaces home">
              <span>Lines</span>
              <span>&amp;</span>
              <span>Spaces</span>
            </a>
            <h1>{html.escape(post.title)}</h1>
            <time datetime="{post.date}">{post.date_display}</time>
          </header>
          <div class="post-body">
            {body_html}
          </div>
        </article>
      </main>"""

    (post_dir / "index.html").write_text(
        shell(
            f"{post.title} — {SITE_NAME}",
            excerpt(post.body),
            body,
            "../../..",
            post.url,
            og_type="article",
        ),
        encoding="utf-8",
    )


def render_feed(posts: list[Post]) -> None:
    last_build_date = posts[0].date_rfc822 if posts else format_datetime(datetime.now(timezone.utc))
    items = []
    for post in posts:
        body_html = render_markdown(post.body, f"feed-{post.slug}-")
        items.append(
            f"""    <item>
      <title>{html.escape(post.title)}</title>
      <link>{post.url}</link>
      <guid>{post.url}</guid>
      <pubDate>{post.date_rfc822}</pubDate>
      <description>{html.escape(excerpt(post.body))}</description>
      <content:encoded><![CDATA[{body_html}]]></content:encoded>
    </item>"""
        )

    feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Lines &amp; Spaces</title>
    <link>{BLOG_SITE_URL}/</link>
    <description>{SITE_DESCRIPTION}</description>
    <language>en-au</language>
    <lastBuildDate>{last_build_date}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (ROOT / "feed.xml").write_text(feed, encoding="utf-8")


def main() -> None:
    posts = load_posts()
    render_index(posts)
    for post in posts:
        render_post(post)
    render_feed(posts)


if __name__ == "__main__":
    main()
