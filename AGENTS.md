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

## Publishing

- Drafts live in `drafts/`.
- Published Markdown sources live in `posts/`.
- `scripts/build-writing.py` generates `index.html`, post pages, and `feed.xml`.
- `vercel.json` keeps deployment static and redirects `www.linesandspaces.net`
  to `https://linesandspaces.net`.
