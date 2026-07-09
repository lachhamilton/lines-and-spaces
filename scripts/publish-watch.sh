#!/bin/sh
# Auto-publish watcher.
#
# Launched by launchd (net.linesandspaces.publish) whenever the contents of
# posts/published/ change — e.g. a draft is moved in. It waits briefly for a
# burst of file operations to settle, then runs the normal publish flow
# (build + commit + push). Vercel deploys on push.
#
# publish-writing is a no-op when the build produces no changes, so extra
# triggers are harmless.
set -u

# launchd's environment is minimal; make sure git (and its osxkeychain
# credential helper) and python3 are found.
PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PATH

cd "$(dirname "$0")/.." || exit 1

# Let a batch of moves/saves settle before building.
sleep 3

printf '\n===== %s publish-watch triggered =====\n' "$(date '+%Y-%m-%d %H:%M:%S')"
./publish-writing
