#!/usr/bin/env python3
"""Announce newly published Lines & Spaces posts on social media.

Runs after publish-writing pushes a new build. Compares posts/published/
against a local ledger (.announced.json, gitignored) and posts anything
new to the Facebook Page (and later Threads). A post is only added to the
ledger after a platform accepts it, so transient failures retry on the
next publish.

Credentials live in .env.local (gitignored):
  FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN   — Facebook Page (token never expires)

Usage:
  python3 scripts/announce.py            # announce anything new
  python3 scripts/announce.py --dry-run  # show what would be posted, post nothing
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_POSTS = ROOT / "posts" / "published"
LEDGER = ROOT / ".announced.json"
ENV_FILE = ROOT / ".env.local"
BLOG_SITE_URL = "https://linesandspaces.net"
GRAPH = "https://graph.facebook.com/v23.0"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def load_ledger() -> dict[str, dict[str, str]]:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {}


def save_ledger(ledger: dict[str, dict[str, str]]) -> None:
    LEDGER.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def parse_post(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    _, raw_meta, body = text.split("---\n", 2)
    meta: dict[str, str] = {}
    for line in raw_meta.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    if not all(meta.get(k) for k in ("title", "date", "slug")):
        return None
    year, month = meta["date"][:4], meta["date"][5:7]
    meta["url"] = f"{BLOG_SITE_URL}/{year}/{month}/{meta['slug']}"
    meta["hook"] = excerpt(body)
    return meta


def excerpt(markdown: str, limit: int = 200) -> str:
    clean = re.sub(r"^\[\^[^\]]+\]:.*$", "", markdown, flags=re.MULTILINE).strip()
    first = re.split(r"\n\s*\n", clean, maxsplit=1)[0]
    first = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", first)
    first = re.sub(r"[*_`>#]", "", first)
    first = " ".join(first.split())
    if len(first) > limit:
        first = first[: limit - 1].rsplit(" ", 1)[0] + "…"
    return first


def compose_message(post: dict[str, str]) -> str:
    return f"{post['title']}\n\n{post['hook']}"


def post_to_facebook(env: dict[str, str], post: dict[str, str]) -> str:
    page_id = env.get("FB_PAGE_ID")
    token = env.get("FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token or token == "PASTE_TOKEN_HERE":
        raise RuntimeError("Facebook credentials missing from .env.local")
    data = urllib.parse.urlencode(
        {
            "message": compose_message(post),
            "link": post["url"],
            "access_token": token,
        }
    ).encode("utf-8")
    with urllib.request.urlopen(f"{GRAPH}/{page_id}/feed", data=data) as response:
        result = json.load(response)
    post_id = result.get("id")
    if not post_id:
        raise RuntimeError(f"Facebook did not return a post id: {result}")
    return post_id


PLATFORMS = [
    ("facebook", post_to_facebook),
]


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    env = load_env()
    ledger = load_ledger()

    posts = []
    for path in sorted(PUBLISHED_POSTS.glob("*.md")):
        post = parse_post(path)
        if post:
            posts.append(post)

    failures = 0
    for post in sorted(posts, key=lambda p: p["date"]):
        record = ledger.setdefault(post["slug"], {})
        for platform, publish in PLATFORMS:
            if platform in record:
                continue
            if dry_run:
                print(f"[dry-run] would post to {platform}: {post['title']} — {post['url']}")
                print(f"[dry-run]   message: {compose_message(post)!r}")
                continue
            try:
                record[platform] = publish(env, post)
                save_ledger(ledger)
                print(f"Announced on {platform}: {post['title']} ({record[platform]})")
            except Exception as error:  # noqa: BLE001 — a platform failure must not block others
                failures += 1
                print(f"FAILED to announce on {platform}: {post['title']} — {error}", file=sys.stderr)

    if not dry_run:
        save_ledger(ledger)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
