---
name: implementation
description: "How the developer implements a task: read design/UI spec/threat model, TDD red-green-refactor, run profile commands, write task notes, apply review feedback, and fix bugs via reproduce-first root-cause analysis. Used by developer. Not for planning (technical-design) or reviewing (code-review-checklist)."
---

# Implementation

## Before coding
1. Read the task row in `_workspace/02_architect_tasks.md`, the related design contract, the UI spec section (tag `ui`) and threat-model requirements (tag `security`).
2. Read every must-read file of the rule packs in the task's `Rules` column (listed in the leader's brief; index in `ai-dev-team:dev-team` → `references/rule-packs.md` §2) and its numbered checks — these are the rules you will report on, one by one.
3. Read the code you will touch and its existing tests. Match local conventions from the project profile.

## TDD loop
1. **Red**: write a test for the first acceptance behavior; run it; confirm it fails for the right reason.
2. **Green**: write the minimal code to pass.
3. **Refactor**: clean up while green.
4. Repeat until the task's done-criteria are covered, then run the related tests (the touched modules' suites and the fast guards) + lint + build from the profile. Do not run the whole test suite per task unless the leader asks or the change touches shared infrastructure; the full suite runs at feature sign-off.

## Running commands
- Heavy commands (module/related test runs, builds, e2e, native builds) run through the profile's wrapped commands — `.claude/team/run-heavy.sh <cmd>` with the worker cap. The red/green loop on a single test file may run directly.
- Foreground only: never leave watchers, dev servers, emulators or daemons running when you report.
- Paste the trimmed output of the final test/lint/build runs into the task notes — reviewers rely on it instead of rerunning them.

Where a test is impractical (pure styling, config), state why in the task notes and verify another way (build, screenshot, manual command).

## Rules that matter
- Stay in task scope. Note unrelated problems in the task notes instead of fixing them.
- Contracts are fixed by the design. If one is wrong, report `BLOCKED` with the reason.
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

## Task notes: `_workspace/04_developer_T{id}.md`
```markdown
# T{id} <title>
- Files changed:
- Tests added:
- Commands run + result (trimmed output):
- Deviations from design (with reason):
- Out-of-scope issues noticed:

## Rule compliance
| Rule | Status | Evidence |
|---|---|---|
```
One row per rule ID of `BASE` and every assigned pack: `pass` with evidence another agent can open (test name, `file:line`, command output, artifact path), `n-a` with the reason, or `fail`. A `fail` or an unchecked rule means the task is not done — fix it or report `BLOCKED`. Rules with a script (`.claude/team/rule-checks.sh`, `.claude/team/overflow-check.mjs` — §9 of that file) are proven by the script's output. Format and rules: `ai-dev-team:dev-team` → `references/rule-packs.md` §6. The leader returns a `DONE` whose notes lack this table.

## Applying feedback
Fix each listed finding; reply per finding `fixed` / `disagree: <reason>`; update the `## Rule compliance` rows the fix touches; rerun tests; report `DONE T{id}` again.
