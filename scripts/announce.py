#!/usr/bin/env python3
"""Announce newly published Lines & Spaces posts on social media.

Runs after publish-writing pushes a new build. Compares posts/published/
against a local ledger (.announced.json, gitignored) and posts anything
new to the Facebook Page (and later Threads). A post is only added to the
ledger after a platform accepts it, so transient failures retry on the
next publish.

Credentials live in .env.local (gitignored):
  FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN       — Facebook Page (token never expires)
  THREADS_USER_ID, THREADS_ACCESS_TOKEN  — Threads (long-lived, 60 days)
  THREADS_APP_SECRET                     — kept for manual token recovery

The Threads token is refreshed (another 60 days) on every run, and a weekly
launchd job (net.linesandspaces.threads-refresh) runs --refresh-only so the
token survives publishing gaps longer than 60 days.

Usage:
  python3 scripts/announce.py                # announce anything new
  python3 scripts/announce.py --dry-run      # show what would be posted, post nothing
  python3 scripts/announce.py --refresh-only # just refresh the Threads token
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_POSTS = ROOT / "posts" / "published"
LEDGER = ROOT / ".announced.json"
ENV_FILE = ROOT / ".env.local"
BLOG_SITE_URL = "https://linesandspaces.net"
GRAPH = "https://graph.facebook.com/v23.0"
THREADS_GRAPH = "https://graph.threads.net/v1.0"
THREADS_CHAR_LIMIT = 500


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
    # Optional front-matter `hook:` overrides the auto-excerpt.
    if not meta.get("hook"):
        meta["hook"] = excerpt(body)
    return meta


def excerpt(markdown: str, limit: int = 200) -> str:
    clean = re.sub(r"^\[\^[^\]]+\]:.*$", "", markdown, flags=re.MULTILINE)
    clean = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", clean).strip()
    first = re.split(r"\n\s*\n", clean, maxsplit=1)[0]
    first = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", first)
    first = re.sub(r"[*_`>#]", "", first)
    first = " ".join(first.split())
    if len(first) > limit:
        first = first[: limit - 1].rsplit(" ", 1)[0] + "…"
    return first


def compose_message(post: dict[str, str], char_limit: int | None = None) -> str:
    """The social post text: the hook in quotes, then the URL on its own line."""
    hook = post["hook"]
    if char_limit:
        frame = len(f"“”\n\n{post['url']}")
        room = char_limit - frame
        if len(hook) > room:
            hook = hook[: room - 1].rsplit(" ", 1)[0] + "…"
    return f"“{hook}”\n\n{post['url']}"


def wait_until_live(url: str, timeout: int = 240, interval: int = 10) -> bool:
    """Wait for the deployed page to serve with its OG tags.

    Announcing races the Vercel deploy: git push returns before the new page
    exists, and platforms cache whatever their first scrape finds — a 404 at
    post time means a bare, imageless link card forever. So don't announce
    until the URL returns 200 AND carries og:image (a 200 from the previous
    deployment would pass a bare status check).
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                if response.status == 200 and b'property="og:image"' in response.read():
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(interval)
    return False


def post_to_facebook(env: dict[str, str], post: dict[str, str]) -> str:
    page_id = env.get("FB_PAGE_ID")
    token = env.get("FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token or token == "PASTE_TOKEN_HERE":
        raise RuntimeError("Facebook credentials missing from .env.local")
    # The link param is what renders the image card — the API never
    # auto-previews a URL that only appears in the message text. FB strips
    # the duplicate URL from the text; the card itself is the link.
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


def threads_get(path: str, params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{THREADS_GRAPH}/{path}?{query}") as response:
        return json.load(response)


def threads_post(path: str, params: dict[str, str]) -> dict:
    data = urllib.parse.urlencode(params).encode("utf-8")
    with urllib.request.urlopen(f"{THREADS_GRAPH}/{path}", data=data) as response:
        return json.load(response)


def post_to_threads(env: dict[str, str], post: dict[str, str]) -> str:
    user_id = env.get("THREADS_USER_ID")
    token = env.get("THREADS_ACCESS_TOKEN")
    if not user_id or not token:
        raise RuntimeError("Threads credentials missing from .env.local")

    # The URL in the text doubles as Threads' link preview source.
    text = compose_message(post, char_limit=THREADS_CHAR_LIMIT)

    container = threads_post(
        f"{user_id}/threads",
        {"media_type": "TEXT", "text": text, "access_token": token},
    )
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError(f"Threads did not return a container id: {container}")

    published = threads_post(
        f"{user_id}/threads_publish",
        {"creation_id": creation_id, "access_token": token},
    )
    media_id = published.get("id")
    if not media_id:
        raise RuntimeError(f"Threads did not publish container {creation_id}: {published}")
    return media_id


def refresh_threads_token(env: dict[str, str]) -> None:
    """Extend the Threads token another 60 days and persist it.

    Refresh requires the token to be >24h old, so failures right after a new
    token was issued are expected and harmless — the token is still fresh.
    """
    token = env.get("THREADS_ACCESS_TOKEN")
    if not token:
        return
    try:
        result = threads_get(
            "refresh_access_token",
            {"grant_type": "th_refresh_token", "access_token": token},
        )
    except Exception as error:  # noqa: BLE001
        print(f"Threads token refresh skipped: {error}", file=sys.stderr)
        return
    new_token = result.get("access_token")
    if not new_token:
        print(f"Threads token refresh skipped: {result}", file=sys.stderr)
        return
    env["THREADS_ACCESS_TOKEN"] = new_token
    lines = [
        f"THREADS_ACCESS_TOKEN={new_token}" if line.startswith("THREADS_ACCESS_TOKEN=") else line
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines()
    ]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    days = result.get("expires_in", 0) / 86400
    print(f"Threads token refreshed; expires {days:.0f} days from now.")


PLATFORMS = [
    ("facebook", post_to_facebook),
    ("threads", post_to_threads),
]


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    env = load_env()

    if "--refresh-only" in sys.argv:
        refresh_threads_token(env)
        return
    if not dry_run:
        refresh_threads_token(env)

    ledger = load_ledger()

    posts = []
    for path in sorted(PUBLISHED_POSTS.glob("*.md")):
        post = parse_post(path)
        if post:
            posts.append(post)

    failures = 0
    for post in sorted(posts, key=lambda p: p["date"]):
        record = ledger.setdefault(post["slug"], {})
        pending = [(p, fn) for p, fn in PLATFORMS if p not in record]
        if pending and not dry_run and not wait_until_live(post["url"]):
            failures += 1
            print(
                f"SKIPPED announcing {post['title']}: {post['url']} not live in time; will retry next publish.",
                file=sys.stderr,
            )
            continue
        for platform, publish in pending:
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
