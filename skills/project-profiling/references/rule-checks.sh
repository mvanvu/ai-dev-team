#!/usr/bin/env bash
# Mechanical checks for ai-dev-team rules that a script can decide.
# Each violation is printed as "<RULE-ID> <file>:<line>: <text>"; the output is the
# evidence for that rule in the task notes (## Rule compliance) and in rule checks.
#
# Usage: $TEAM_BIN/rule-checks.sh <check> [args...]
#   arch [dir...]           ARCH-1    feature/page code importing headless or interaction libraries, or a template pack
#   list-storage [dir...]   LIST-4    list state (filters, sort, page, search) kept in web storage
#   commits [base]          BASE-7    AI attribution in commit messages of base..HEAD (default: upstream, else the
#                                     merge-base with the default branch); an unknown base exits 64
#   prerelease              TOOL-2    pre-release versions in package.json / pubspec.yaml dependencies
#   flutter-overflow <log>  COMPACT-6 "overflowed" in saved flutter test / run output
#   ai-look [dir...]        REAL-2/4  placeholder copy (lorem ipsum, John Doe, Acme) and gradient text (candidates)
#   all [base]              every check above except flutter-overflow
#   staged-media            BASE-7    images or video staged under .ai-dev-team/ (they must stay git-ignored);
#                                     run before every commit that includes team files
#   build-id                not a check: prints one id of the working tree (HEAD + uncommitted changes +
#                           untracked files), equal for every agent on the same tree; screenshots record it
# Exit: 0 no violation (or the check does not apply here), 1 violations found, 64 usage error.
# Portable to bash 3.2 (macOS): no mapfile, empty arrays expanded with ${a[@]+"${a[@]}"}.
set -u

SRC_EXT=(--include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.vue' --include='*.mjs')
SKIP_DIRS=(--exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build --exclude-dir=.git --exclude-dir=coverage --exclude-dir=.ai-dev-team)

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
  find . \( -name node_modules -o -name .git -o -name dist -o -name build -o -name .ai-dev-team \) -prune -o \
    -type d \( -path '*/src/features' -o -path '*/src/pages' \) -print
}

source_dirs() {
  find . \( -name node_modules -o -name .git -o -name dist -o -name build -o -name .ai-dev-team \) -prune -o \
    -type d -name src -print
}

check_arch() {
  local dirs=(${@+"$@"}) d
  if [ "${#dirs[@]}" -eq 0 ]; then
    while IFS= read -r d; do dirs+=("$d"); done < <(feature_dirs)
  fi
  if [ "${#dirs[@]}" -eq 0 ]; then echo "ARCH-1 n-a: no src/features or src/pages directory"; return 0; fi
  local libs="reka-ui|radix-ui|@radix-ui/[^'\"]+|react-aria-components|motion|motion/[^'\"]+|motion-v|vaul|vaul-vue|sonner|vue-sonner|@use-gesture/[^'\"]+|@tanstack/(vue|react)-(virtual|table)"
  # App template packs only, not any path that happens to contain /templates/.
  local templates="@/templates(/[^'\"]*)?|([^'\"]*/)?src/templates(/[^'\"]*)?"
  local hits
  # Comment lines and type-only imports carry no runtime dependency.
  hits=$(grep -rnE "${SRC_EXT[@]}" "${SKIP_DIRS[@]}" \
    "(from|import|require\()[[:space:]]*\(?['\"]($libs|$templates)['\"]" "${dirs[@]}" 2>/dev/null \
    | grep -vE '^[^:]+:[0-9]+:[[:space:]]*(//|\*|/\*|<!--|#)' \
    | grep -vE '^[^:]+:[0-9]+:[[:space:]]*import[[:space:]]+type[[:space:]{]')
  report ARCH-1 "$hits"
}

check_list_storage() {
  local dirs=(${@+"$@"}) d
  if [ "${#dirs[@]}" -eq 0 ]; then
    while IFS= read -r d; do dirs+=("$d"); done < <(source_dirs)
  fi
  if [ "${#dirs[@]}" -eq 0 ]; then echo "LIST-4 n-a: no src directory"; return 0; fi
  # Storage access on a line that names list state; column visibility is allowed in localStorage.
  local hits
  hits=$(grep -rnEi "${SRC_EXT[@]}" "${SKIP_DIRS[@]}" \
    "(localStorage|sessionStorage|useLocalStorage|useSessionStorage|useStorage)[^;]*(filter|sort|search|order|query|page|offset)" \
    "${dirs[@]}" 2>/dev/null | grep -viE "column|\.(spec|test)\.")
  report LIST-4 "$hits"
}

# The default branch: origin/HEAD, else main, else master; empty when none exists.
default_branch() {
  local ref
  ref=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || true)
  for ref in $ref main master; do
    if git rev-parse --verify --quiet "$ref^{commit}" >/dev/null; then echo "$ref"; return 0; fi
  done
}

check_commits() {
  git rev-parse --git-dir >/dev/null 2>&1 || { echo "BASE-7 n-a: not a git repository"; return 0; }
  local base="${1:-}" branch
  if [ -n "$base" ]; then
    if ! git rev-parse --verify --quiet "$base^{commit}" >/dev/null; then
      echo "BASE-7 error: unknown base $base"
      return 64
    fi
  else
    base=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)
    if [ -z "$base" ]; then
      branch=$(default_branch)
      [ -n "$branch" ] && base=$(git merge-base HEAD "$branch" 2>/dev/null || true)
      # On the default branch itself the merge-base is HEAD: there is nothing to compare against.
      if [ -n "$base" ] && [ "$base" = "$(git rev-parse HEAD 2>/dev/null)" ]; then base=""; fi
    fi
    if [ -z "$base" ]; then echo "BASE-7 n-a: no base — pass one"; return 0; fi
  fi
  local hits
  # One output line per message line, prefixed with the commit's short hash.
  hits=$(git log "$base..HEAD" --format='%x1e%h%n%B' 2>/dev/null \
    | awk 'BEGIN { RS = "\036" } NF { n = split($0, l, "\n"); for (i = 2; i <= n; i++) if (l[i] != "") print l[1] ": " l[i] }' \
    | grep -Ei \
    "co-authored-by:.*(claude|anthropic|copilot|chatgpt|openai|cursor|gemini)|generated (with|by).*(claude|copilot|chatgpt|gemini|\bai\b)|noreply@anthropic\.com|🤖")
  report BASE-7 "$hits"
}

check_prerelease() {
  local files=() f hits=""
  while IFS= read -r f; do files+=("$f"); done < <(find . \( -name node_modules -o -name .git -o -name dist \
    -o -name build -o -name Pods -o -name .dart_tool -o -name vendor -o -path '*/android/app/build' -o -path '*/ios/Pods' \) -prune -o \
    -type f \( -name package.json -o -name pubspec.yaml \) -print)
  if [ "${#files[@]}" -eq 0 ]; then echo "TOOL-2 n-a: no package.json or pubspec.yaml"; return 0; fi
  # A pre-release tag anywhere in the version string: plain, after >=, <, ~, ^, or in an npm: alias.
  # The project's own top-level "version" (package.json) is not a dependency; a top-level
  # pubspec.yaml version has no indent and is never matched.
  local tags="(alpha|beta|rc|canary|next|nightly|dev|pre)"
  hits=$(grep -nEi "(\"[@a-z0-9_./-]+\":[[:space:]]*\"[^\"]*|^[[:space:]]+[a-z0-9_]+:[[:space:]]*[^#]*)[0-9]+\.[0-9]+\.[0-9]+-$tags" \
    "${files[@]}" /dev/null 2>/dev/null | grep -vE '^[^:]+:[0-9]+:[[:space:]]*"version"[[:space:]]*:')
  report TOOL-2 "$hits"
}

check_ai_look() {
  local dirs=(${@+"$@"}) d
  if [ "${#dirs[@]}" -eq 0 ]; then
    while IFS= read -r d; do dirs+=("$d"); done < <(source_dirs)
  fi
  if [ "${#dirs[@]}" -eq 0 ]; then echo "REAL n-a: no src directory"; return 0; fi
  local status=0 hits
  # Mocks, stories, tests and fixtures may hold placeholder data; example.com is the reserved
  # placeholder domain (RFC 2606) and is correct in placeholders.
  hits=$(grep -rnEi "${SRC_EXT[@]}" --include='*.html' --include='*.json' --include='*.dart' "${SKIP_DIRS[@]}" \
    --exclude-dir=__mocks__ --exclude-dir=__tests__ --exclude-dir=tests --exclude-dir=test --exclude-dir=fixtures \
    --exclude-dir=e2e --exclude='*.stories.*' --exclude='*.spec.*' --exclude='*.test.*' --exclude='*fixtures*' \
    "lorem ipsum|john doe|jane doe|acme (inc|corp)" "${dirs[@]}" 2>/dev/null \
    | grep -viE '(^|/)(__mocks__|__tests__|tests?|fixtures|e2e)/|\.(spec|test|stories)\.|fixtures')
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

sha1_stdin() {
  if command -v sha1sum >/dev/null 2>&1; then sha1sum | awk '{ print $1 }'
  elif command -v shasum >/dev/null 2>&1; then shasum -a 1 | awk '{ print $1 }'
  else openssl sha1 | awk '{ print $NF }'
  fi
}

# Same tree, same id: HEAD, the diff of tracked files against it and every untracked,
# non-ignored file (name and content, sorted). Outside git: the newest 200 file mtimes.
# The team's own output (.ai-dev-team/, _workspace*, .claude/) is left out, so writing screenshots or
# notes does not change the id of the code under test.
build_id() {
  local top
  if top=$(git rev-parse --show-toplevel 2>/dev/null) && [ -n "$top" ]; then
    (
      cd "$top" || exit 1
      local listed=(--others)
      if git rev-parse --verify --quiet HEAD >/dev/null; then
        git rev-parse HEAD
        git -c core.quotepath=off diff --no-ext-diff --no-color --binary HEAD -- . ':(exclude)_workspace*' ':(exclude).claude' ':(exclude).ai-dev-team'
      else
        echo "no-head"
        listed=(--cached --others)
      fi
      git ls-files -z "${listed[@]}" --exclude-standard -- . ':(exclude)_workspace*' ':(exclude).claude' ':(exclude).ai-dev-team' | LC_ALL=C sort -z -u | while IFS= read -r -d '' f; do
        printf '%s\0' "$f"
        [ -f "$f" ] && cat "$f"
        printf '\0'
      done
    ) | sha1_stdin
  else
    local fmt=(-f '%m %N')
    if stat -c '%Y %n' . >/dev/null 2>&1; then fmt=(-c '%Y %n'); fi
    find . \( -name node_modules -o -name .git -o -name '_workspace*' -o -name .claude -o -name .ai-dev-team \) -prune -o -type f -print0 \
      | xargs -0 stat "${fmt[@]}" 2>/dev/null | LC_ALL=C sort -k1,1nr -k2 | head -n 200 | sha1_stdin
  fi
}

check="${1:-}"
[ "$#" -gt 0 ] && shift
check_staged_media() {
  git rev-parse --git-dir >/dev/null 2>&1 || { echo "BASE-7 ok (not a git repository)"; return 0; }
  local hits
  hits=$(git diff --cached --name-only --diff-filter=AM -- .ai-dev-team \
    | grep -iE '\.(png|jpe?g|webp|gif|mp4|webm)$' | sed 's|$|: staged image or video (git rm --cached it, fix .ai-dev-team/.gitignore)|')
  report BASE-7 "$hits"
}

case "$check" in
  arch) check_arch ${@+"$@"} ;;
  list-storage) check_list_storage ${@+"$@"} ;;
  commits) check_commits ${@+"$@"} ;;
  prerelease) check_prerelease ;;
  flutter-overflow) check_flutter_overflow ${@+"$@"} ;;
  ai-look) check_ai_look ${@+"$@"} ;;
  staged-media) check_staged_media ;;
  build-id) build_id ;;
  all)
    status=0
    check_arch || status=1
    check_list_storage || status=1
    check_commits ${@+"$@"}
    rc=$?
    [ "$rc" -ne 0 ] && status=1
    check_prerelease || status=1
    check_ai_look || status=1
    [ "$rc" -eq 64 ] && status=64
    exit "$status"
    ;;
  *)
    sed -n '6,18p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 64
    ;;
esac
