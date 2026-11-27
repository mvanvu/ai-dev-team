#!/usr/bin/env bash
# Finds, remembers and compares the local checkout of this plugin's source repository (`plugin_src`).
#
# Usage: $TEAM_BIN/plugin-src.sh resolve <repo root> [--no-clone]
#          Prints `<path> <how>` (how: local, machine, self, sibling, cloned) or `none user` / `none not-found`.
#          Order: `plugin_src:` in <repo root>/.ai-dev-team/local.md (a path, or `none` = the user's choice);
#          the machine file ~/.local/state/ai-dev-team/plugin-src; the plugin itself when it runs from a
#          git checkout (claude --plugin-dir); <repo root>/../ai-dev-team; a clone of the installed
#          marketplace's repository into ~/.local/state/ai-dev-team/source/ai-dev-team.
#          A found path is written to the machine file and to the `plugin_src:` line of local.md.
#        $TEAM_BIN/plugin-src.sh set <repo root> <path|none>     the user's choice, written to both places
#        $TEAM_BIN/plugin-src.sh sync <path>                     fast-forward a clean checkout to its upstream
#        $TEAM_BIN/plugin-src.sh version <repo root>             one line: installed, source, upstream versions,
#                                                                unpushed commits, and the update command (never clones;
#                                                                without a source it reads the upstream plugin.json)
# Exit:  0 done; 2 usage or invalid path.
set -u

state="${XDG_STATE_HOME:-$HOME/.local/state}/ai-dev-team"
machine="$state/plugin-src"
here="$(cd "$(dirname "$0")" && pwd)"
plugin_root="$(cd "$here/../../.." && pwd)"
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

valid() {  # a git checkout whose plugin.json names ai-dev-team
  [ -n "${1:-}" ] && [ -f "$1/.claude-plugin/plugin.json" ] \
    && git -C "$1" rev-parse --show-toplevel >/dev/null 2>&1 \
    && grep -q '"name": *"ai-dev-team"' "$1/.claude-plugin/plugin.json"
}

version_of() { sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$1" 2>/dev/null | head -1; }

local_md() { printf '%s/.ai-dev-team/local.md' "$1"; }

read_local() { sed -n 's/^plugin_src: *\([^ #]*\).*/\1/p' "$(local_md "$1")" 2>/dev/null | head -1; }

write_local() {  # replace the plugin_src line in place; add it before the closing front-matter line if missing
  f="$(local_md "$1")"; [ -f "$f" ] || return 0
  if grep -q '^plugin_src:' "$f"; then
    sed -i "s|^plugin_src:.*|plugin_src: $2   # local checkout of the plugin's source repository; none = proposals only|" "$f"
  else
    awk -v l="plugin_src: $2" 'n<2 && /^---$/ {n++; if (n==2) print l} {print}' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  fi
}

remember() {  # $1 repo root, $2 path, $3 how
  mkdir -p "$state"; printf '%s\n' "$2" > "$machine"
  write_local "$1" "$2"; echo "$2 $3"
}

marketplace() {  # the marketplace name this installed plugin came from (cache/<marketplace>/ai-dev-team/<version>)
  case "$plugin_root" in */plugins/cache/*/ai-dev-team/*) basename "$(dirname "$(dirname "$plugin_root")")" ;; esac
}

repo_url() {  # clone URL of the marketplace this plugin was installed from
  m="$(marketplace)"; [ -n "$m" ] || return 1
  python3 - "$cfg/plugins/known_marketplaces.json" "$m" <<'EOF'
import json, sys
s = json.load(open(sys.argv[1])).get(sys.argv[2], {}).get("source", {})
if s.get("source") == "github": print(f"https://github.com/{s['repo']}.git")
elif s.get("url"): print(s["url"])
elif s.get("path"): print(s["path"])
EOF
}

sync() {  # fast-forward only, and only a clean tree on a branch with an upstream
  src="$1"
  git -C "$src" rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 || return 0
  [ -z "$(git -C "$src" status --porcelain)" ] || { echo "plugin_src has local changes; not synced" >&2; return 0; }
  git -C "$src" fetch -q 2>/dev/null || { echo "plugin_src fetch failed (offline?)" >&2; return 0; }
  git -C "$src" merge -q --ff-only '@{u}' 2>/dev/null || echo "plugin_src diverged from its upstream; not synced" >&2
}

resolve() {
  root="$1"; clone="${2:-}"
  v="$(read_local "$root")"
  case "$v" in
    none) echo "none user"; return 0 ;;
    ""|ask) ;;
    *) valid "$v" && { remember "$root" "$v" local >/dev/null; echo "$v local"; return 0; } ;;
  esac
  v="$(cat "$machine" 2>/dev/null)"
  valid "$v" && { remember "$root" "$v" machine; return 0; }
  valid "$plugin_root" && { remember "$root" "$(git -C "$plugin_root" rev-parse --show-toplevel)" self; return 0; }
  v="$(cd "$root/.." 2>/dev/null && pwd)/ai-dev-team"
  valid "$v" && { remember "$root" "$v" sibling; return 0; }
  [ "$clone" = "--no-clone" ] && { echo "none not-found"; return 0; }
  dest="$state/source/ai-dev-team"
  valid "$dest" && { remember "$root" "$dest" machine; return 0; }
  url="$(repo_url)" || url=""
  [ -n "$url" ] || { echo "none not-found"; return 0; }
  mkdir -p "$state/source"
  git clone -q "$url" "$dest" 2>/dev/null && valid "$dest" && { remember "$root" "$dest" cloned; return 0; }
  echo "none not-found"
}

case "${1:-}" in
resolve) resolve "${2:?repo root}" "${3:-}" ;;
set)
  root="${2:?repo root}"; v="${3:?path or none}"
  if [ "$v" = none ]; then write_local "$root" none; echo "none user"
  else v="$(cd "$v" 2>/dev/null && pwd)"; valid "$v" || { echo "not a checkout of ai-dev-team: $3" >&2; exit 2; }
       remember "$root" "$v" user; fi
  ;;
sync) sync "${2:?path}" ;;
version)
  root="${2:?repo root}"
  installed="$(version_of "$plugin_root/.claude-plugin/plugin.json")"
  read -r src how <<<"$(resolve "$root" --no-clone)"
  line="plugin: installed $installed"
  upstream=""
  if [ "$src" != none ]; then
    git -C "$src" fetch -q 2>/dev/null  # fetch only: the checkout itself is fast-forwarded by monitor-integrate.sh start
    line="$line · source $(version_of "$src/.claude-plugin/plugin.json") at $src"
    if git -C "$src" rev-parse '@{u}' >/dev/null 2>&1; then
      upstream="$(git -C "$src" show '@{u}:.claude-plugin/plugin.json' 2>/dev/null | sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' | head -1)"
      n="$(git -C "$src" rev-list --count '@{u}..HEAD' 2>/dev/null || echo 0)"
      [ "$n" -gt 0 ] && line="$line ($n unpushed)"
    fi
  else
    url="$(repo_url 2>/dev/null)"
    case "$url" in https://github.com/*)
      r="${url#https://github.com/}"; r="${r%.git}"
      upstream="$(curl -fsS --max-time 5 "https://raw.githubusercontent.com/$r/HEAD/.claude-plugin/plugin.json" 2>/dev/null \
        | sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' | head -1)" ;;
    esac
  fi
  [ -n "$upstream" ] && line="$line · upstream $upstream"
  m="$(marketplace)"
  if [ -n "$upstream" ] && [ -n "$m" ] && [ "$upstream" != "$installed" ] \
     && [ "$(printf '%s\n%s\n' "$installed" "$upstream" | sort -V | tail -1)" = "$upstream" ]; then
    line="$line · update available: claude plugin marketplace update $m && claude plugin update ai-dev-team@$m, then restart the session"
  elif [ -z "$m" ]; then
    line="$line · running from a checkout (--plugin-dir)"
  else
    line="$line · up to date"
  fi
  echo "$line"
  ;;
*) sed -n 2,16p "$0"; exit 2 ;;
esac
