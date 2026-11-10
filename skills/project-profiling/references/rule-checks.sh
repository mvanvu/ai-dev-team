#!/usr/bin/env bash
# Mechanical checks for ai-dev-team rules that a script can decide.
# Each violation is printed as "<RULE-ID> <file>:<line>: <text>"; the output is the
# evidence for that rule in the task notes (## Rule compliance) and in rule checks.
#
# Usage: .claude/team/rule-checks.sh <check> [args...]
#   arch [dir...]           ARCH-1    feature/page code importing headless or interaction libraries, or a template
#   list-storage [dir...]   LIST-4    list state (filters, sort, page, search) kept in web storage
#   commits [base]          BASE-7    AI attribution in commit messages of base..HEAD (default: upstream, else last 20)
#   prerelease              TOOL-2    pre-release versions in package.json / pubspec.yaml
#   flutter-overflow <log>  COMPACT-6 "overflowed" in saved flutter test / run output
#   ai-look [dir...]        REAL-2/4  placeholder copy (lorem ipsum, John Doe, Acme) and gradient text (candidates)
#   all [base]              every check above except flutter-overflow
# Exit: 0 no violation (or the check does not apply here), 1 violations found, 64 usage error.
set -u

SRC_EXT=(--include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.vue' --include='*.mjs')
SKIP_DIRS=(--exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build --exclude-dir=.git --exclude-dir=coverage)

# Prints grep hits prefixed with the rule ID; returns 1 when there were any.
report() {
  local rule="$1" hits="$2"
  if [ -n "$hits" ]; then
    printf '%s\n' "$hits" | sed "s|^|$rule |"
    return 1
  fi
  echo "$rule ok"
}

feature_dirs() {
  find . \( -name node_modules -o -name .git -o -name dist -o -name build \) -prune -o \
    -type d \( -path '*/src/features' -o -path '*/src/pages' \) -print
}

source_dirs() {
  find . \( -name node_modules -o -name .git -o -name dist -o -name build \) -prune -o \
    -type d -name src -print
}

check_arch() {
  local dirs=("$@")
  if [ "${#dirs[@]}" -eq 0 ]; then mapfile -t dirs < <(feature_dirs); fi
  if [ "${#dirs[@]}" -eq 0 ]; then echo "ARCH-1 n-a: no src/features or src/pages directory"; return 0; fi
  local libs="reka-ui|radix-ui|@radix-ui/[^'\"]+|react-aria-components|motion|motion/[^'\"]+|motion-v|vaul|vaul-vue|sonner|vue-sonner|@use-gesture/[^'\"]+|@tanstack/(vue|react)-(virtual|table)"
  local templates="@/templates(/[^'\"]*)?|[^'\"]*/templates/[^'\"]*"
  local hits
  hits=$(grep -rnE "${SRC_EXT[@]}" "${SKIP_DIRS[@]}" \
    "(from|import|require\()[[:space:]]*\(?['\"]($libs|$templates)['\"]" "${dirs[@]}" 2>/dev/null)
  report ARCH-1 "$hits"
}

check_list_storage() {
  local dirs=("$@")
  if [ "${#dirs[@]}" -eq 0 ]; then mapfile -t dirs < <(source_dirs); fi
  if [ "${#dirs[@]}" -eq 0 ]; then echo "LIST-4 n-a: no src directory"; return 0; fi
  # Storage access on a line that names list state; column visibility is allowed in localStorage.
  local hits
  hits=$(grep -rnEi "${SRC_EXT[@]}" "${SKIP_DIRS[@]}" \
    "(localStorage|sessionStorage|useLocalStorage|useSessionStorage|useStorage)[^;]*(filter|sort|search|order|query|page|offset)" \
    "${dirs[@]}" 2>/dev/null | grep -viE "column|\.(spec|test)\.")
  report LIST-4 "$hits"
}

check_commits() {
  git rev-parse --git-dir >/dev/null 2>&1 || { echo "BASE-7 n-a: not a git repository"; return 0; }
  local base="${1:-}" range
  if [ -z "$base" ]; then base=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true); fi
  if [ -n "$base" ]; then range="$base..HEAD"; else range="-20"; fi
  local hits
  # shellcheck disable=SC2086
  hits=$(git log $range --format='%h: %B' 2>/dev/null | grep -nEi \
    "co-authored-by:.*(claude|anthropic|copilot|chatgpt|openai|cursor|gemini)|generated (with|by).*(claude|copilot|chatgpt|gemini|\bai\b)|noreply@anthropic\.com|🤖")
  report BASE-7 "$hits"
}

check_prerelease() {
  local files hits=""
  mapfile -t files < <(find . \( -name node_modules -o -name .git -o -name dist -o -name build \) -prune -o \
    -type f \( -name package.json -o -name pubspec.yaml \) -print)
  if [ "${#files[@]}" -eq 0 ]; then echo "TOOL-2 n-a: no package.json or pubspec.yaml"; return 0; fi
  hits=$(grep -nEi "(\"[@a-z0-9_./-]+\":[[:space:]]*\"|^[[:space:]]+[a-z0-9_]+:[[:space:]]*)[~^]?[0-9]+\.[0-9]+\.[0-9]+-(alpha|beta|rc|canary|next|nightly|dev|pre)" \
    "${files[@]}" /dev/null 2>/dev/null)
  report TOOL-2 "$hits"
}

check_ai_look() {
  local dirs=("$@")
  if [ "${#dirs[@]}" -eq 0 ]; then mapfile -t dirs < <(source_dirs); fi
  if [ "${#dirs[@]}" -eq 0 ]; then echo "REAL n-a: no src directory"; return 0; fi
  local status=0 hits
  hits=$(grep -rnEi "${SRC_EXT[@]}" --include='*.html' --include='*.json' --include='*.dart' "${SKIP_DIRS[@]}" \
    "lorem ipsum|john doe|jane doe|acme (inc|corp)|example\.com" "${dirs[@]}" 2>/dev/null | grep -viE "\.(spec|test)\.|__tests__|/test/")
  report REAL-2 "$hits" || status=1
  hits=$(grep -rnE "${SRC_EXT[@]}" --include='*.css' --include='*.scss' "${SKIP_DIRS[@]}" \
    "bg-clip-text[^\"']*text-transparent|text-transparent[^\"']*bg-clip-text|background-clip:[[:space:]]*text" "${dirs[@]}" 2>/dev/null)
  report REAL-4 "$hits" || status=1
  return "$status"
}

check_flutter_overflow() {
  local log="${1:-}"
  if [ -z "$log" ] || [ ! -f "$log" ]; then echo "usage: $0 flutter-overflow <log file>" >&2; return 64; fi
  report COMPACT-6 "$(grep -nE "overflowed by" "$log" /dev/null)"
}

check="${1:-}"
[ "$#" -gt 0 ] && shift
case "$check" in
  arch) check_arch "$@" ;;
  list-storage) check_list_storage "$@" ;;
  commits) check_commits "$@" ;;
  prerelease) check_prerelease ;;
  flutter-overflow) check_flutter_overflow "$@" ;;
  ai-look) check_ai_look "$@" ;;
  all)
    status=0
    check_arch || status=1
    check_list_storage || status=1
    check_commits "$@" || status=1
    check_prerelease || status=1
    check_ai_look || status=1
    exit "$status"
    ;;
  *)
    sed -n '5,14p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 64
    ;;
esac
