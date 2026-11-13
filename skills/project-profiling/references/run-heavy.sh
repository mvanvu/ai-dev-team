#!/usr/bin/env bash
# Runs a CPU-heavy command (test suite, build, e2e, dependency audit) for the ai-dev-team agents.
# Only one heavy command runs at a time on this machine, at low CPU priority, so parallel
# agents queue instead of saturating the CPU and freezing the desktop.
#
# Usage: $TEAM_BIN/run-heavy.sh <command> [args...]
# Env:   AI_DEV_TEAM_LOCK       lock path (default: $TMPDIR or /tmp + ai-dev-team-heavy.lock; machine-wide;
#                               without flock the lock is the directory <lock>.d holding the owner's pid)
#        AI_DEV_TEAM_LOCK_WAIT  max seconds to wait for the lock (default 1800)
#        AI_DEV_TEAM_TIMEOUT    max seconds the command may run once it has the lock (default 1800; 0 = no limit).
#                               A hung test runner or build is killed instead of holding the lock and its
#                               caller forever; needs `timeout` (coreutils), else the command runs unlimited.
# Exit:  the command's exit code, 75 when the lock wait timed out, 124 when the command ran past the timeout.
# While waiting it prints the holder's command and directory (from <lock>.owner) once to stderr.
set -u

lock="${AI_DEV_TEAM_LOCK:-${TMPDIR:-/tmp}/ai-dev-team-heavy.lock}"
wait_s="${AI_DEV_TEAM_LOCK_WAIT:-1800}"
run_s="${AI_DEV_TEAM_TIMEOUT:-1800}"
limit=""
if [ "$run_s" != "0" ] && command -v timeout >/dev/null 2>&1; then
  limit="timeout -k 30 $run_s"
fi

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <command> [args...]" >&2
  exit 64
fi

owner_file="$lock.owner"
say_waiting() {
  echo "run-heavy: waiting for the heavy lock, held by: $(cat "$owner_file" 2>/dev/null || echo unknown)" >&2
}

low_priority() {
  if command -v nice >/dev/null 2>&1; then $limit nice -n 10 "$@"; else $limit "$@"; fi
}

timed_out() {
  echo "run-heavy: timed out after ${run_s}s and was stopped: $*" >&2
  echo "run-heavy: report it as hung (which test or step was running), do not rerun it unchanged" >&2
}

if command -v flock >/dev/null 2>&1; then
  # -o: the command does not inherit the lock fd, so daemons it leaves behind
  # (Gradle, Flutter, test containers) cannot hold the lock after it exits.
  flock -n "$lock" true 2>/dev/null || say_waiting
  # The child records itself as the holder once it has the lock, then becomes the command.
  flock -o -w "$wait_s" -E 75 "$lock" sh -c \
    'owner="$1"; shift; printf "%s  [%s, since %s]\n" "$*" "$PWD" "$(date +%H:%M:%S)" > "$owner" 2>/dev/null; exec $0 nice -n 10 "$@"' \
    "${limit:-env}" "$owner_file" "$@"
  rc=$?
  [ "$rc" -eq 124 ] && [ -n "$limit" ] && timed_out "$@"
  exit "$rc"
fi

# Fallback for systems without flock (macOS): an atomic mkdir lock. The owner pid is written
# atomically (pid.tmp then mv), so a reader sees either no pid or the whole pid.
dir="$lock.d"
start=$(date +%s)
nopid_since=""
announced=0
while :; do
  if mkdir "$dir" 2>/dev/null; then
    # Ours only if the pid lands in it (a breaker may have renamed the directory meanwhile).
    if echo $$ > "$dir/pid.tmp" 2>/dev/null && mv -f "$dir/pid.tmp" "$dir/pid" 2>/dev/null \
      && [ "$(cat "$dir/pid" 2>/dev/null || true)" = "$$" ]; then
      break
    fi
    continue
  fi
  owner=$(cat "$dir/pid" 2>/dev/null || true)
  stale=0
  if [ -n "$owner" ]; then
    nopid_since=""
    kill -0 "$owner" 2>/dev/null || stale=1
  else
    # No pid yet: the owner may be between mkdir and writing it. Stale after 10 s without one.
    now=$(date +%s)
    if [ -z "$nopid_since" ]; then nopid_since=$now
    elif [ $(( now - nopid_since )) -ge 10 ]; then stale=1
    fi
  fi
  if [ "$stale" -eq 1 ]; then
    # Break the stale lock by an atomic rename: of several waiters only one gets the directory.
    rm -rf "$dir.stale.$$"
    if mv "$dir" "$dir.stale.$$" 2>/dev/null; then
      taken=$(cat "$dir.stale.$$/pid" 2>/dev/null || true)
      if [ "$taken" != "$owner" ]; then
        # Not the lock judged stale: another waiter broke that one and a new owner took the path
        # in between. Hand it back while nobody has claimed the path yet, and wait again.
        if mkdir "$dir" 2>/dev/null && [ -n "$taken" ]; then mv "$dir.stale.$$/pid" "$dir/pid" 2>/dev/null; fi
      fi
      rm -rf "$dir.stale.$$"
    fi
    nopid_since=""
    continue
  fi
  if [ "$announced" -eq 0 ]; then say_waiting; announced=1; fi
  if [ $(( $(date +%s) - start )) -ge "$wait_s" ]; then
    echo "run-heavy: waited ${wait_s}s for $dir" >&2
    exit 75
  fi
  sleep 2
done
release() {
  # Remove the lock only while it is still ours.
  if [ "$(cat "$dir/pid" 2>/dev/null || true)" = "$$" ]; then rm -rf "$dir"; fi
}
printf "%s  [%s, since %s]\n" "$*" "$PWD" "$(date +%H:%M:%S)" > "$owner_file" 2>/dev/null
trap release EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
low_priority "$@"
rc=$?
[ "$rc" -eq 124 ] && [ -n "$limit" ] && timed_out "$@"
exit "$rc"
