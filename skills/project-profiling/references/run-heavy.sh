#!/usr/bin/env bash
# Runs a CPU-heavy command (test suite, build, e2e, dependency audit, browser launch) for the ai-dev-team
# agents. At most `heavy_slots` heavy commands run at a time on this machine, at low CPU priority, so
# parallel agents (of every project on the machine) queue instead of saturating the CPU.
#
# Usage: $TEAM_BIN/run-heavy.sh <command> [args...]
#        $TEAM_BIN/run-heavy.sh --status      print every slot: free, or the command, directory and start time
# Env:   AI_DEV_TEAM_LOCK       lock path (default: $TMPDIR or /tmp + ai-dev-team-heavy.lock; machine-wide; slot N > 1
#                               uses <lock>.N; without flock there is one slot, the directory <lock>.d holding the pid)
#        AI_DEV_TEAM_SLOTS      slots (default: `heavy_slots` in .ai-dev-team/local.md of the working directory,
#                               else max(1, CPU threads / 8))
#        AI_DEV_TEAM_LOCK_WAIT  max seconds to wait for a slot (default 1800)
#        AI_DEV_TEAM_TIMEOUT    max seconds the command may run once it has a slot (default 1800; 0 = no limit).
#                               A hung test runner or build is killed instead of holding the slot and its
#                               caller forever; needs `timeout` (coreutils), else the command runs unlimited.
# Exit:  the command's exit code, 75 when the wait for a slot timed out, 124 when the command ran past the timeout.
# While waiting it prints, once to stderr, what holds each slot (command, directory = project, start time).
set -u

lock="${AI_DEV_TEAM_LOCK:-${TMPDIR:-/tmp}/ai-dev-team-heavy.lock}"
wait_s="${AI_DEV_TEAM_LOCK_WAIT:-1800}"
run_s="${AI_DEV_TEAM_TIMEOUT:-1800}"
limit=""
if [ "$run_s" != "0" ] && command -v timeout >/dev/null 2>&1; then
  limit="timeout -k 30 $run_s"
fi

slots="${AI_DEV_TEAM_SLOTS:-}"
if [ -z "$slots" ] && [ -f .ai-dev-team/local.md ]; then
  slots=$(sed -n 's/^heavy_slots:[[:space:]]*\([0-9][0-9]*\).*/\1/p' .ai-dev-team/local.md | head -n 1)
fi
if [ -z "$slots" ]; then
  threads=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 8)
  slots=$(( threads / 8 ))
fi
[ "$slots" -ge 1 ] 2>/dev/null || slots=1
command -v flock >/dev/null 2>&1 || slots=1

slot_lock() { if [ "$1" -eq 1 ]; then echo "$lock"; else echo "$lock.$1"; fi; }

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <command> [args...] | --status" >&2
  exit 64
fi

owner_file="$lock.owner"
slot_free() {
  # A slot is free when its lock can be taken right now (the lock is released before the probe returns).
  command -v flock >/dev/null 2>&1 || { [ ! -d "$lock.d" ]; return; }
  flock -n "$(slot_lock "$1")" true 2>/dev/null
}
status() {
  local i=1
  while [ "$i" -le "$slots" ]; do
    if slot_free "$i"; then echo "slot $i/$slots: free"
    else echo "slot $i/$slots: $(cat "$(slot_lock "$i").owner" 2>/dev/null || echo unknown)"; fi
    i=$(( i + 1 ))
  done
}
say_waiting() {
  echo "run-heavy: all $slots heavy slot(s) busy, waiting; held by:" >&2
  status | sed 's/^/  /' >&2
}

if [ "$1" = "--status" ]; then
  status
  exit 0
fi

low_priority() {
  if command -v nice >/dev/null 2>&1; then $limit nice -n 10 "$@"; else $limit "$@"; fi
}

timed_out() {
  echo "run-heavy: timed out after ${run_s}s and was stopped: $*" >&2
  echo "run-heavy: report it as hung (which test or step was running), do not rerun it unchanged" >&2
}

if command -v flock >/dev/null 2>&1; then
  # Take the first free slot; check again every 2 s until AI_DEV_TEAM_LOCK_WAIT.
  start=$(date +%s)
  announced=0
  got=0
  while [ "$got" -eq 0 ]; do
    i=1
    while [ "$i" -le "$slots" ]; do
      exec 9>>"$(slot_lock "$i")"
      if flock -n 9; then got=$i; break; fi
      exec 9>&-
      i=$(( i + 1 ))
    done
    [ "$got" -ne 0 ] && break
    if [ "$announced" -eq 0 ]; then say_waiting; announced=1; fi
    if [ $(( $(date +%s) - start )) -ge "$wait_s" ]; then
      echo "run-heavy: waited ${wait_s}s for a heavy slot" >&2
      exit 75
    fi
    sleep 2
  done
  printf "%s  [%s, since %s]\n" "$*" "$PWD" "$(date +%H:%M:%S)" > "$(slot_lock "$got").owner" 2>/dev/null
  # 9>&-: the command does not inherit the lock, so daemons it leaves behind
  # (Gradle, Flutter, test containers) cannot hold the slot after it exits.
  low_priority "$@" 9>&-
  rc=$?
  exec 9>&-
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
