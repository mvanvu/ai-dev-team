#!/usr/bin/env bash
# Lands a monitor agent's plugin change in the local plugin source checkout (`plugin_src` in
# .ai-dev-team/local.md) without touching anyone else's work: the change is made in a private worktree,
# then rebased, checked and fast-forwarded into the checkout's branch under one machine-wide lock, so
# monitors of several sessions never interleave. Nothing is pushed and the version is never bumped.
#
# Usage: $TEAM_BIN/monitor-integrate.sh start <plugin_src>            create a worktree, print its path
#        $TEAM_BIN/monitor-integrate.sh land <worktree> "<message>"   commit, rebase, check, fast-forward, clean up
#        $TEAM_BIN/monitor-integrate.sh drop <worktree>               discard an unfinished worktree
# Exit:  0 landed; 3 checks failed (worktree kept, fix and run `land` again); 4 the checkout has local
#        changes in the same files or is not on its branch (commit kept on branch monitor/<id>, reported);
#        5 rebase conflict (rebase aborted, worktree kept); 75 lock wait timed out.
set -u

state="$HOME/.local/state/ai-dev-team/monitor"
lock="$state/plugin-src.lock"
mkdir -p "$state"

case "${1:-}" in
start)
  src="$(cd "${2:?plugin_src}" && git rev-parse --show-toplevel)" || exit 2
  "$(dirname "$0")/plugin-src.sh" sync "$src"   # a clean checkout is fast-forwarded to its upstream first
  base="$(git -C "$src" symbolic-ref --short HEAD)" || exit 2
  id="$(date +%Y%m%d-%H%M%S)-$$"
  wt="$state/wt-$id"
  git -C "$src" worktree add -q -b "monitor/$id" "$wt" "$base" || exit 2
  printf '%s\n' "$src" > "$wt/.monitor-src"
  printf '%s\n' "$base" > "$wt/.monitor-base"
  echo "$wt"
  ;;
land)
  wt="${2:?worktree}"; msg="${3:?message}"
  src="$(cat "$wt/.monitor-src")"; base="$(cat "$wt/.monitor-base")"
  branch="$(git -C "$wt" symbolic-ref --short HEAD)"
  git -C "$wt" add -A -- . ':!.monitor-src' ':!.monitor-base'
  git -C "$wt" diff --cached --quiet || git -C "$wt" commit -q -m "$msg" || exit 2
  exec 9>"$lock"
  flock -w 900 9 || exit 75
  git -C "$wt" rebase -q "$base" || { git -C "$wt" rebase --abort; echo "rebase conflict on $base; worktree kept: $wt"; exit 5; }
  ( cd "$wt" && python3 scripts/check-plugin.py && claude plugin validate . >/dev/null \
      && claude --plugin-dir . plugin details ai-dev-team >/dev/null ) \
    || { echo "checks failed; worktree kept: $wt"; exit 3; }
  if [ "$(git -C "$src" symbolic-ref --short HEAD)" != "$base" ] \
     || ! git -C "$src" merge -q --ff-only "$branch" 2>/dev/null; then
    git -C "$src" worktree remove --force "$wt"
    echo "not landed: $src has local changes in these files or left $base; commit kept on branch $branch"
    exit 4
  fi
  git -C "$src" worktree remove --force "$wt"
  git -C "$src" branch -q -d "$branch"
  git -C "$src" log --oneline -1
  ;;
drop)
  wt="${2:?worktree}"; src="$(cat "$wt/.monitor-src")"
  branch="$(git -C "$wt" symbolic-ref --short HEAD)"
  git -C "$src" worktree remove --force "$wt" && git -C "$src" branch -q -D "$branch"
  ;;
*)
  sed -n 2,14p "$0"; exit 2
  ;;
esac
