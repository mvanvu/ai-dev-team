# Team paths

The team writes nothing into the project repository: no profile, no workspace, no scripts. Scripts run from the installed plugin, and everything a run produces lives in a per-project state directory outside the repo. A plugin update therefore never leaves stale copies behind, and `git status` stays clean.

## Contents
1. The four paths
2. Resolving them
3. Moving files left by older versions
4. Rules for every agent

## 1. The four paths
| Name | What | Value |
|---|---|---|
| `TEAM_BIN` | team scripts: `run-heavy.sh`, `rule-checks.sh`, `overflow-check.mjs` | the installed plugin's `skills/project-profiling/references/` |
| `TEAM_STATE` | this project's state, kept across runs: `project-profile.md`, archived workspaces `workspace_<YYYYMMDD-HHMM>/` | `${XDG_STATE_HOME:-~/.local/state}/ai-dev-team/projects/<slug>` |
| `TEAM_WS` | the current run: spec, plan, task board, task notes, QC report, `qa-artifacts/`, ledgers | `$TEAM_STATE/workspace` |
| `TEAM_TOOLS` | QA tools shared by all projects (a Playwright install when the project has none) | `${XDG_STATE_HOME:-~/.local/state}/ai-dev-team/qa-tools` |

`<slug>` is the absolute path of the main repository root with every character other than a letter or digit replaced by `-`. Git worktrees of one repository resolve to the same root, so a worktree task shares the state of its project.

## 2. Resolving them
The leader resolves the paths once per session, in Phase 0:

```bash
common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
root=${common:+$(dirname "$common")}; root=${root:-$(pwd)}
base="${XDG_STATE_HOME:-$HOME/.local/state}/ai-dev-team"
TEAM_STATE="$base/projects/$(printf %s "$root" | tr -c 'A-Za-z0-9' '-')"
TEAM_WS="$TEAM_STATE/workspace"; TEAM_TOOLS="$base/qa-tools"
mkdir -p "$TEAM_WS"
echo "TEAM_STATE=$TEAM_STATE TEAM_WS=$TEAM_WS TEAM_TOOLS=$TEAM_TOOLS"
```

`TEAM_BIN` is `<dev-team skill base directory>/../project-profiling/references`, resolved to an absolute path (the base directory is printed at the top of the loaded `dev-team` skill). Without it, use the newest `~/.claude/plugins/cache/*/ai-dev-team/*/skills/project-profiling/references`.

Every brief starts with the four absolute values (`TEAM_BIN=… TEAM_STATE=… TEAM_WS=… TEAM_TOOLS=…`). Agents never recompute them and never use relative paths for team files. Shell state does not carry over between tool calls, so commands use the absolute paths, not the variable names.

## 3. Moving files left by older versions
Before anything else, when the repo still holds team files from an older version:
1. `.claude/team/project-profile.md` → `$TEAM_STATE/project-profile.md` (keep the newer one when both exist). Rewrite its commands from `.claude/team/<script>` to `$TEAM_BIN/<script>`.
2. `.claude/team/run-heavy.sh`, `rule-checks.sh`, `overflow-check.mjs` → delete. Remove `.claude/team/` when it is empty.
3. `_workspace/` → `$TEAM_WS/` (only when `$TEAM_WS` is empty; otherwise archive it as `$TEAM_STATE/workspace_<timestamp>/`); each `_workspace_*/` → `$TEAM_STATE/`.
4. Remove the lines the team added to `.git/info/exclude` (`_workspace/`, `_workspace_*/`, `.claude/team/`). Entries in a tracked `.gitignore` are the user's: mention them, do not edit.
5. Any of these files tracked by git → ask the user before moving, since that changes the repository.

## 4. Rules for every agent
- Team files (notes, reports, screenshots, throwaway scripts and specs, downloaded tools) are written only under `TEAM_WS`, `TEAM_STATE` or `TEAM_TOOLS` — never in the repo. The repo receives only the code and tests the task asks for.
- Commands run with the project root as the working directory; the scripts find the project from there.
- A tool that can only write inside the project (some browser MCP servers restrict their output directory) saves there, and the agent moves the file to `$TEAM_WS/qa-artifacts/` right away.
- Writing outside the project may ask for permission. To avoid prompts, the user can add `~/.local/state/ai-dev-team` to `permissions.additionalDirectories` in their Claude Code settings; the plugin never edits settings itself.
