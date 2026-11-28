#!/usr/bin/env bash
# Lands a monitor agent's plugin change in the local plugin source checkout (`plugin_src` in
# .ai-dev-team/local.md) without touching anyone else's work: the change is made in a private worktree,
# then rebased, checked and fast-forwarded into the checkout's branch under one machine-wide lock, so
# monitors of several sessions never interleave. `land` never pushes and never bumps the version; `push`
# is run by the leader only, at a stop point with `monitor_push: auto` in local.md (ai-dev-team:monitor skill).
#
# Usage: $TEAM_BIN/monitor-integrate.sh start <plugin_src>            create a worktree, print its path
#        $TEAM_BIN/monitor-integrate.sh land <worktree> "<message>"   commit, rebase, check, fast-forward, clean up
#        $TEAM_BIN/monitor-integrate.sh drop <worktree>               discard an unfinished worktree
#        $TEAM_BIN/monitor-integrate.sh pending <plugin_src>          list unpushed commits (the proposal summary)
#        $TEAM_BIN/monitor-integrate.sh push <plugin_src>             rebase unpushed commits on the upstream, bump
#                                                                     the patch version once (upstream + 1), run the
#                                                                     checks, commit the bump, push; prints the summary
# Exit:  0 landed / pushed / nothing to push; 2 usage, not on a branch or no upstream; 3 checks failed (worktree
#        kept, fix and run `land` again; for `push`: nothing pushed, bump left uncommitted); 4 the checkout has
#        local changes in the same files or is not on its branch (commit kept on branch monitor/<id>, reported;
#        for `push`: uncommitted changes in plugin_src); 5 rebase conflict (rebase aborted, worktree kept);
#        6 push refused (account, network or permission; nothing retried); 75 lock wait timed out.
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
pending)
  src="$(cd "${2:?plugin_src}" && git rev-parse --show-toplevel)" || exit 2
  git -C "$src" fetch -q 2>/dev/null
  git -C "$src" log --format='%h %s' '@{u}..HEAD' 2>/dev/null || { echo "no upstream for $src"; exit 2; }
  ;;
push)
  src="$(cd "${2:?plugin_src}" && git rev-parse --show-toplevel)" || exit 2
  git -C "$src" symbolic-ref -q HEAD >/dev/null || { echo "$src is not on a branch"; exit 2; }
  git -C "$src" rev-parse -q --verify '@{u}' >/dev/null || { echo "$src has no upstream"; exit 2; }
  exec 9>"$lock"
  flock -w 900 9 || exit 75
  [ -z "$(git -C "$src" status --porcelain)" ] || { echo "not pushed: $src has uncommitted changes"; exit 4; }
  git -C "$src" fetch -q || { echo "not pushed: fetch failed (offline?)"; exit 6; }
  [ "$(git -C "$src" rev-list --count '@{u}..HEAD')" -gt 0 ] || { echo "nothing to push"; exit 0; }
  if [ "$(git -C "$src" rev-list --count 'HEAD..@{u}')" -gt 0 ]; then
    git -C "$src" rebase -q '@{u}' || { git -C "$src" rebase --abort; echo "not pushed: rebase conflict on the upstream"; exit 5; }
  fi
  pj="$src/.claude-plugin/plugin.json"
  ver() { sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' | head -1; }
  up="$(git -C "$src" show '@{u}:.claude-plugin/plugin.json' | ver)"
  cur="$(ver < "$pj")"
  next="${up%.*}.$(( ${up##*.} + 1 ))"
  [ "$(printf '%s\n%s\n' "$cur" "$next" | sort -V | tail -1)" = "$cur" ] && next="$cur"  # already ahead: keep it
  summary="$(git -C "$src" log --format='- %h %s' '@{u}..HEAD')"
  if [ "$cur" != "$next" ]; then
    sed -i "s/\"version\": *\"$cur\"/\"version\": \"$next\"/" "$pj"
  fi
  ( cd "$src" && python3 scripts/check-plugin.py && claude plugin validate . >/dev/null \
      && claude --plugin-dir . plugin details ai-dev-team >/dev/null ) \
    || { echo "not pushed: checks failed at $next (a change log row must start with | $next:); bump left uncommitted"; exit 3; }
  if [ "$cur" != "$next" ]; then
    git -C "$src" add .claude-plugin/plugin.json && git -C "$src" commit -q -m "Bump version to $next" || exit 2
  fi
  git -C "$src" push -q || { echo "not pushed: git push refused (account, network or permission)"; exit 6; }
  echo "pushed $next:"
  echo "$summary"
  ;;
*)
  sed -n 2,22p "$0"; exit 2
  ;;
esac
