---
name: implementation
description: "How the developer implements a task: read plan/UI spec/threat model, TDD red-green-refactor, run profile commands, write task notes, apply review feedback, and fix bugs via reproduce-first root-cause analysis. Used by the developer agent for every implementation task (backend, frontend, mobile). Not for planning (technical-design) or reviewing (code-review-checklist)."
---

# Implementation

## Before coding
1. Read the task row in `$TEAM_WS/02_tasks.md`, the related plan contract, the UI spec section (tag `ui`) and threat-model requirements (tag `security`).
2. Checking data or pages while working: the lightest tool (`ai-dev-team:dev-team` → `references/resource-budget.md` §2) — `curl`/`jq` for API data, `lightpanda fetch` for rendered DOM, a browser only for layout.
3. Read the rule list in the leader's brief (one line per rule ID; index in `ai-dev-team:dev-team` → `references/rule-packs.md` §2) — these are the rules you will report on, one by one. Open a pack's reference file only for the section behind a rule this task exercises.
4. Read the code you will touch and its existing tests. Match local conventions from the project profile.
5. **Reuse first** (`BASE-16`): before adding a feature, component, service, helper, endpoint, script or fixture, check `$TEAM_STATE/capabilities.md`, the reuse notes in the brief, then search by name (a bounded `grep`, not a crawl of the repo). Use or extend what fits; build new only when nothing does, and say why in a `## Reuse` table of the notes. Add what you build that others can reuse to `capabilities.md`.

Work in few turns (`COST-8`, `ai-dev-team:dev-team` → `references/resource-budget.md` §2): batch reads, write new files whole, make all edits to a file in one pass, run tests after a group of changes.

## TDD loop
1. **Red**: write a test for the first acceptance behavior; run it; confirm it fails for the right reason.
2. **Green**: write the minimal code to pass.
3. **Refactor**: clean up while green.
4. Repeat until the task's done-criteria are covered, then run once: the profile's `test (related)` command on the files you changed, the guard tests the profile maps to the areas you touched, lint / type-check, and the build if the task changes built output. That run is the task's evidence.
5. Never run the whole test suite or every guard suite per task, unless the leader asks or the change touches shared infrastructure; the full suite runs once at feature sign-off.
6. A test you did not touch, for code you did not change, fails: rerun that single file once. Still failing → write it in the notes as `not mine: <file> — <first error line>` and report it; do not rerun the suite to investigate, do not edit other tasks' files to make it pass. Concurrent edits by another agent and stale built output are the usual cause, and the leader resolves them.

## Running commands
- Heavy commands (related runs over more than ~5 test files, builds, e2e, native builds, whole-project type-check) run through the profile's wrapped commands — `$TEAM_BIN/run-heavy.sh <cmd>` with the worker cap. The red/green loop on a single test file and small related runs run directly (`ai-dev-team:dev-team` → `references/resource-budget.md` §2). Related runs name test files, never whole test directories.
- A command that may outlast the foreground limit: start it as a background task and end your turn; you are resumed when it finishes. No waiting loops (`BASE-14`).
- Stop only processes you started (`BASE-15`); never install an SDK or shared tool (`BASE-17`). Scratch tests or probes that commit data (forked processes, a second connection, calls to the running app) delete what they wrote; the notes show the count before and after.
- Foreground only: never leave watchers, dev servers, emulators or daemons running when you report.
- Paste the trimmed output of the final test/lint/build runs into the task notes — reviewers rely on it instead of rerunning them.

Where a test is impractical (pure styling, config), state why in the task notes and verify another way (build, screenshot, manual command).

## Rules that matter
- Stay in task scope. Note unrelated problems in the task notes instead of fixing them.
- Contracts are fixed by the plan. If one is wrong, report `BLOCKED` with the reason.
- Security defaults: validate and normalize input at the boundary, parameterized queries, authorization check on every entry point, no secrets in code or logs, output encoding.
- Data access: the number of queries (and client requests) must not grow with the number of rows — eager-load or batch relations, aggregate in SQL, write in bulk, and add a query-count test for each list, export and bulk path (`ai-dev-team:code-review-checklist` → `references/query-performance.md`).
- UI: use design tokens and existing components; implement every state in the UI spec; meet the accessibility checklist.
- Comments in English, explaining *why*; never describe bug history.
- Commits only when the user asked. Message: English, imperative, concise, no AI/Claude attribution.

## Bug fixes
1. Reproduce with a failing test (or exact command) first.
2. Find the root cause — trace data backward from the symptom; do not patch the symptom.
3. Fix, confirm the test passes, run the related suite for regressions.
4. For hard bugs, use the `superpowers:systematic-debugging` skill when it is installed in this session; otherwise keep to steps 1–3.

## Task notes: `$TEAM_WS/04_dev_T{id}.md`
```markdown
# T{id} <title>
- Files changed:
- Tests added:
- Commands run + result (trimmed output):
- Deviations from the plan (with reason):
- Out-of-scope issues noticed:

## Reuse
| Needed | Looked in | Result |
|---|---|---|
| e.g. error card with retry | capabilities.md, `grep -rn ErrorState src` | reused `src/ui/ErrorState.tsx` |

## Rule compliance
| Rule | Status | Evidence |
|---|---|---|
```
One row per rule ID of `BASE`, `COST` and every assigned pack: `pass` with evidence another agent can open (test name, `file:line`, command output, artifact path), `n-a` with the reason, or `fail`. A `fail` or an unchecked rule means the task is not done — fix it or report `BLOCKED`. Rules with a script (`$TEAM_BIN/rule-checks.sh`, `$TEAM_BIN/overflow-check.mjs` — §9 of that file) are proven by the script's output. Format and rules: `ai-dev-team:dev-team` → `references/rule-packs.md` §6. The leader returns a `DONE` whose notes lack this table.

## Applying feedback
Fix each listed finding; reply per finding `fixed` / `disagree: <reason>`; update the `## Rule compliance` rows the fix touches; rerun only the related tests of the files changed in this round (and rebuild once if built output changed); report `DONE T{id}` again.
