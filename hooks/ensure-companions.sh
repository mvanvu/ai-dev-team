#!/usr/bin/env bash
# Installs companion skills that cannot be declared as plugin dependencies:
#   - ui-ux-pro-max  (plugin in a third-party marketplace; a hard dependency would disable ai-dev-team when that marketplace is absent)
#   - security-audit (plain skill distributed via `npx skills`, not a plugin)
# Runs on SessionStart, never blocks the session: missing items are installed in the background
# and become available from the next session. Opt out with AI_DEV_TEAM_NO_AUTO_INSTALL=1.
set -u

[ "${AI_DEV_TEAM_NO_AUTO_INSTALL:-0}" = "1" ] && exit 0

STATE_DIR="${HOME}/.claude/ai-dev-team"
LOG="${STATE_DIR}/companions.log"
RETRY_SECONDS=86400 # after a failed attempt, wait a day before retrying to avoid hammering the network every session
DRY_RUN="${AI_DEV_TEAM_DRY_RUN:-0}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

has_skill() {
  local name="$1"
  [ -e "${HOME}/.claude/skills/${name}/SKILL.md" ] || [ -e "${PROJECT_DIR}/.claude/skills/${name}/SKILL.md" ]
}

has_plugin() {
  local id="$1" file="${HOME}/.claude/plugins/installed_plugins.json"
  [ -f "$file" ] && grep -q "\"${id}\"" "$file"
}

recently_attempted() {
  local stamp="${STATE_DIR}/.attempt-$1"
  [ -f "$stamp" ] || return 1
  local age=$(( $(date +%s) - $(stat -c %Y "$stamp" 2>/dev/null || stat -f %m "$stamp") ))
  [ "$age" -lt "$RETRY_SECONDS" ]
}

pending=()

if ! has_skill ui-ux-pro-max && ! has_plugin "ui-ux-pro-max@ui-ux-pro-max-skill" && ! recently_attempted ui-ux-pro-max; then
  command -v claude >/dev/null 2>&1 && pending+=("ui-ux-pro-max")
fi

if ! has_skill security-audit && ! recently_attempted security-audit; then
  command -v npx >/dev/null 2>&1 && pending+=("security-audit")
fi

[ "${#pending[@]}" -eq 0 ] && exit 0

install_one() {
  case "$1" in
    ui-ux-pro-max)
      claude plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill \
        && claude plugin install ui-ux-pro-max@ui-ux-pro-max-skill ;;
    security-audit)
      npx -y skills add cloudflare/security-audit-skill -g -a claude-code -s security-audit -y ;;
  esac
}

if [ "$DRY_RUN" = "1" ]; then
  echo "ai-dev-team (dry run): would install ${pending[*]}"
  exit 0
fi

# A lock directory prevents two sessions starting at once from installing in parallel.
LOCK="${STATE_DIR}/.lock"
mkdir "$LOCK" 2>/dev/null || exit 0

for item in "${pending[@]}"; do touch "${STATE_DIR}/.attempt-${item}"; done

(
  trap 'rmdir "$LOCK" 2>/dev/null' EXIT
  for item in "${pending[@]}"; do
    echo "[$(date -u +%FT%TZ)] installing ${item}" >>"$LOG"
    if install_one "$item" >>"$LOG" 2>&1; then
      echo "[$(date -u +%FT%TZ)] ${item}: ok" >>"$LOG"
      rm -f "${STATE_DIR}/.attempt-${item}"
    else
      echo "[$(date -u +%FT%TZ)] ${item}: failed (retry after 24h)" >>"$LOG"
    fi
  done
) </dev/null >/dev/null 2>&1 &
disown 2>/dev/null || true

# SessionStart stdout is added to the session context, so the leader knows these are not available yet.
echo "ai-dev-team: installing missing companion skills in the background (${pending[*]}); they will be available from the next session. Log: ${LOG}"
exit 0
