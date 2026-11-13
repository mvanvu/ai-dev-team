# Team paths

The team keeps its state inside the project repository, in one folder, `.ai-dev-team/`, so the spec, plan, board, notes and decisions travel with the repo to every machine and branch. Scripts still run from the installed plugin, so a plugin update never leaves stale copies behind. Large, machine-specific output (screenshots, contact sheets, browser installs) stays out of git.

## Contents
1. The four paths
2. Resolving them
3. What is committed
4. Moving files left by older versions
5. Rules for every agent

## 1. The four paths
| Name | What | Value |
|---|---|---|
| `TEAM_BIN` | team scripts: `run-heavy.sh`, `rule-checks.sh`, `overflow-check.mjs` | the installed plugin's `skills/project-profiling/references/` |
| `TEAM_STATE` | this project's state, kept across runs: `project-profile.md`, `local.md` (this machine's values, git-ignored), `seed/`, `flows/`, archived workspaces `workspace_<YYYYMMDD-HHMM>/` | `<repo root>/.ai-dev-team` |
| `TEAM_WS` | the current run: spec, plan, UI spec, threat model, task board, task notes, QC report, `mockups/`, `qa-artifacts/`, ledgers | `$TEAM_STATE/workspace` |
| `TEAM_TOOLS` | QA tools shared by all projects on this machine (a Playwright install when the project has none) | `${XDG_STATE_HOME:-~/.local/state}/ai-dev-team/qa-tools` |

`<repo root>` is the main repository root; git worktrees of one repository resolve to the same root, so a worktree task shares the state of its project.

## 2. Resolving them
The leader resolves the paths once per session, in Phase 0:

```bash
common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
root=${common:+$(dirname "$common")}; root=${root:-$(pwd)}
TEAM_STATE="$root/.ai-dev-team"; TEAM_WS="$TEAM_STATE/workspace"
TEAM_TOOLS="${XDG_STATE_HOME:-$HOME/.local/state}/ai-dev-team/qa-tools"
mkdir -p "$TEAM_WS"
for p in '**/qa-artifacts/' '**/sheets/' '**/*.png' '**/*.jpg' '**/*.jpeg' '**/*.webp' '**/*.gif' '**/*.mp4' '**/*.webm' '/local.md'; do
  grep -qxF "$p" "$TEAM_STATE/.gitignore" 2>/dev/null || echo "$p" >> "$TEAM_STATE/.gitignore"
done
( cd "$root" && "${TEAM_BIN:?resolve TEAM_BIN first}/rule-checks.sh" tracked-media --fix )  # images an older ignore file let into the index
( cd "$root" && "$TEAM_BIN/rule-checks.sh" env-drift )  # keys .env lacks against .env.example (names only)
echo "TEAM_STATE=$TEAM_STATE TEAM_WS=$TEAM_WS TEAM_TOOLS=$TEAM_TOOLS"
```

`TEAM_BIN` is `<dev-team skill base directory>/../project-profiling/references`, resolved to an absolute path (the base directory is printed at the top of the loaded `dev-team` skill). Without it, use the newest `~/.claude/plugins/cache/*/ai-dev-team/*/skills/project-profiling/references`.

Every brief starts with the four absolute values (`TEAM_BIN=… TEAM_STATE=… TEAM_WS=… TEAM_TOOLS=…`), plus `PLAYWRIGHT_DIR=<profile playwright_dir>` when the task uses a browser. Agents never recompute them and never use relative paths for team files. Shell state does not carry over between tool calls, so commands use the absolute paths, not the variable names.

## 3. What is committed
- Everything under `.ai-dev-team/` is meant to be committed with the work it belongs to — profile, spec, plan, UI spec, board, notes, ledgers, mockups, seeds, flows — except generated images and video — `qa-artifacts/`, contact `sheets/`, screenshots and recordings (`*.png`, `*.jpg`, `*.webp`, `*.mp4`, `*.webm`) — which are large and rebuilt on demand; `.ai-dev-team/.gitignore` leaves them out. Mockups stay committed as their HTML, kit and screen data files; images a mockup needs come from the project's own assets or are inlined small.
- The team still never commits on its own (`BASE-7`): the files show up in `git status` and go in with the user's commit. When the user asks for a commit, `.ai-dev-team/` changes are included unless the user says otherwise.
- The resolve snippet adds any ignore line missing from an existing `.ai-dev-team/.gitignore` (one written by an older version included) and keeps lines the user added. Before every commit that includes team files, the leader runs `$TEAM_BIN/rule-checks.sh staged-media`; a hit is unstaged with `git rm --cached` and the ignore file fixed before the commit is made.
- Images and video that are already tracked (committed while an older ignore file was in place) stay tracked until they are removed from the index: the resolve snippet runs `rule-checks.sh tracked-media --fix`, which untracks them and keeps the files; the leader tells the user, and the removal goes into the next commit. Their copies in earlier commits stay in the history unless the user asks for a history rewrite.
- **Paths in committed files are repo-relative** (`.ai-dev-team/workspace/02_plan.md`, `apps/web/src/…`): notes, boards, specs, plans and the profile never hold an absolute path of one machine (`/home/<user>/…`), so another machine reads them unchanged. Absolute paths appear only in briefs, built from the resolved `TEAM_*` values.
- On another machine, Phase 0 finds `.ai-dev-team/` in the checkout and resumes from its board like any resume. Machine-specific values live in the git-ignored `$TEAM_STATE/local.md` (`ai-dev-team:project-profiling` step 9) and are filled on each machine; the committed profile never changes because the machine did.

## 4. Moving files left by older versions
Before anything else, when team files of an older version exist:
1. `~/.local/state/ai-dev-team/projects/<slug>/` (state kept outside the repo; `<slug>` is the repo root path with every character other than a letter or digit replaced by `-`) → `.ai-dev-team/`: profile, `workspace/`, `workspace_*/`, `seed/`, `flows/` (keep the newer file when both exist). Leave the old folder in place and tell the user it can be deleted.
2. `.claude/team/project-profile.md` → `.ai-dev-team/project-profile.md`; delete `.claude/team/run-heavy.sh`, `rule-checks.sh`, `overflow-check.mjs`; remove `.claude/team/` when empty.
3. `_workspace/` → `$TEAM_WS/` (or `$TEAM_STATE/workspace_<timestamp>/` when `$TEAM_WS` is not empty); each `_workspace_*/` → `$TEAM_STATE/`.
4. `.superpowers/` (mockups, brainstorm and plan files written by `superpowers` during a team run) → `$TEAM_WS/mockups/` and `$TEAM_WS/`; ask first when the user keeps their own files there.
5. Profile commands that hold `.claude/team/<script>` or a versioned plugin path are rewritten to `$TEAM_BIN/<script>`. Lines the team added to `.git/info/exclude` (`_workspace/`, `_workspace_*/`, `.claude/team/`) are removed.
6. Machine fields in the committed profile (`playwright_dir`, `heavy_workers`, an app URL with a port, local tool paths) move to `$TEAM_STATE/local.md`; a field written twice keeps the newer value, once, in front matter. Absolute paths of a machine in committed team files (`/home/<user>/<repo>/…`) are rewritten once to repo-relative paths — one `sed` over `.ai-dev-team/`, not a hand edit per file.

## 5. Rules for every agent
- Team files (notes, reports, screenshots, mockups, throwaway scripts and specs, files of third-party skills run by the team such as `.superpowers/`) are written only under `TEAM_STATE` / `TEAM_WS`, and downloaded tools only under `TEAM_TOOLS` — never anywhere else in the repo. The rest of the repo receives only the code and tests the task asks for, and the approved mockup in the profile's `mockup_dir` (`ai-dev-team:ui-ux-design` → `references/design-gate.md` §5).
- Commands run with the project root as the working directory; the scripts find the project from there.
- Files the agent writes under `TEAM_STATE` / `TEAM_WS` name other files by repo-relative path (§3).
- A tool that can only write to its own output directory (some browser MCP servers) saves there, and the agent moves the file to `$TEAM_WS/qa-artifacts/` right away.
- `TEAM_TOOLS` is outside the project, so installing Playwright there may ask for permission once; the user can add `~/.local/state/ai-dev-team` to `permissions.additionalDirectories`. The plugin never edits settings itself.
