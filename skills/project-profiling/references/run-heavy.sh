#!/usr/bin/env bash
# Runs a CPU-heavy command (test suite, build, e2e, dependency audit) for the ai-dev-team agents.
# Only one heavy command runs at a time on this machine, at low CPU priority, so parallel
# agents queue instead of saturating the CPU and freezing the desktop.
#
# Usage: .claude/team/run-heavy.sh <command> [args...]
# Env:   AI_DEV_TEAM_LOCK       lock path (default: $TMPDIR or /tmp + ai-dev-team-heavy.lock; machine-wide)
#        AI_DEV_TEAM_LOCK_WAIT  max seconds to wait for the lock (default 1800)
# Exit:  the command's exit code, or 75 when the lock wait timed out.
set -u

lock="${AI_DEV_TEAM_LOCK:-${TMPDIR:-/tmp}/ai-dev-team-heavy.lock}"
wait_s="${AI_DEV_TEAM_LOCK_WAIT:-1800}"

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <command> [args...]" >&2
  exit 64
fi

low_priority() {
  if command -v nice >/dev/null 2>&1; then nice -n 10 "$@"; else "$@"; fi
}

if command -v flock >/dev/null 2>&1; then
  # -o: the command does not inherit the lock fd, so daemons it leaves behind
  # (Gradle, Flutter, test containers) cannot hold the lock after it exits.
  exec flock -o -w "$wait_s" -E 75 "$lock" nice -n 10 "$@"
fi

# Fallback for systems without flock (macOS): an atomic mkdir lock with stale-owner cleanup.
dir="$lock.d"
start=$(date +%s)
until mkdir "$dir" 2>/dev/null; do
  owner=$(cat "$dir/pid" 2>/dev/null || true)
  if [ -n "$owner" ] && ! kill -0 "$owner" 2>/dev/null; then
    rm -rf "$dir"
    continue
  fi
  if [ $(( $(date +%s) - start )) -ge "$wait_s" ]; then
    echo "run-heavy: waited ${wait_s}s for $dir" >&2
    exit 75
  fi
  sleep 2
done
echo $$ > "$dir/pid"
trap 'rm -rf "$dir"' EXIT INT TERM
low_priority "$@"
