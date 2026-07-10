# Agent Notes

This file is for Codex agents working on this repository. The user has
explicitly given permission for agents to update `AGENTS.md` whenever it is
useful to keep project context, design direction, decisions, or working notes
current.

## Project

This is the standalone Lines & Spaces blog project for
`https://linesandspaces.net`.

The site is currently a static site built with plain HTML, CSS, and small
JavaScript only. Keep it framework free unless the user explicitly changes
direction.

## Direction

- Treat Lines & Spaces as its own public blog property, not a sub-section of
  `lachlanhamilton.com`.
- The portfolio site can reference this as `Words` or as a project, but the blog
  itself should live here.
- Do not use Lachlan Hamilton portfolio branding or primary portfolio nav on the
  blog itself. The public blog shell should read as only `Lines & Spaces`.
- Keep the visual language clean, white, typographic, and direct.
- Avoid AI-looking cards, tag pills, heavy metaphors, excessive eyebrows, and
  generic editorial/score treatments.
- RSS and post permalinks should be canonical to `https://linesandspaces.net`.

## Working Constraints

- Use `apply_patch` for manual edits.
- Do not revert user changes.
- Keep copy direct and avoid over-abstract phrasing.
- Verify pages in the local browser after meaningful frontend changes.
- Keep shared CSS and JavaScript scoped to the standalone blog. Avoid carrying
  over portfolio-site selectors, scripts, or visual systems unless the blog
  explicitly needs them.

## Publishing

- Point Obsidian at `posts/` as the writing workspace.
- Drafts live in `posts/drafts/`.
- Published Markdown sources live in `posts/published/`. Location is the only
  publish switch — every `.md` in `posts/published/` is built. There is no
  `status` gate; move a file back to `posts/drafts/` to unpublish.
- `scripts/build-writing.py` generates `index.html`, post pages, and `feed.xml`.
- `vercel.json` keeps deployment static and redirects `www.linesandspaces.net`
  to `https://linesandspaces.net`.

## Auto-publish watcher

- A launchd agent (`~/Library/LaunchAgents/net.linesandspaces.publish.plist`,
  label `net.linesandspaces.publish`) watches `posts/published/` and runs
  `scripts/publish-watch.sh` on change, which calls `./publish-writing`
  (build + commit + push). Vercel deploys on push.
- It fires on directory-content changes (a file moved in, renamed, or removed),
  not on in-place content edits of an already-published file. To force a rebuild
  after editing an existing post, run `./publish-writing` manually.
- Output is logged to `.publish-watch.log` (gitignored).
- Manage it with `launchctl bootout|bootstrap gui/$(id -u) <plist>`.

## Social announcements

- After a successful push, `publish-writing` runs `scripts/announce.py`, which
  posts new pieces to the Lines & Spaces Facebook Page and to Threads
  (@lachlanhamilton, personal profile).
- New = not yet in `.announced.json` (gitignored ledger; entries added only
  after a platform accepts the post, so failures retry on the next publish).
- Credentials in `.env.local`: `FB_PAGE_ID` + `FB_PAGE_ACCESS_TOKEN` (Page
  token, never expires), `THREADS_USER_ID` + `THREADS_ACCESS_TOKEN` (long-lived,
  60 days) and `THREADS_APP_SECRET` (manual recovery only). Never commit or
  print tokens.
- The Threads token auto-refreshes on every announce run, plus weekly via
  launchd agent `net.linesandspaces.threads-refresh` (Mondays 9am,
  `--refresh-only`; logs to `.publish-watch.log`). If it ever fully lapses
  (>60 days offline), regenerate via the app dashboard's User Token Generator
  (app 1014468218134269 → Use cases → Access the Threads API).
- Test with `python3 scripts/announce.py --dry-run`.
