---
name: implementation
description: "How the developer implements a task: read design/UI spec/threat model, TDD red-green-refactor, run profile commands, write task notes, apply review feedback, and fix bugs via reproduce-first root-cause analysis. Used by developer. Not for planning (technical-design) or reviewing (code-review-checklist)."
---

# Implementation

## Before coding
1. Read the task row in `_workspace/02_architect_tasks.md`, the related design contract, the UI spec section (tag `ui`) and threat-model requirements (tag `security`).
2. Read the code you will touch and its existing tests. Match local conventions from the project profile.

## TDD loop
1. **Red**: write a test for the first acceptance behavior; run it; confirm it fails for the right reason.
2. **Green**: write the minimal code to pass.
3. **Refactor**: clean up while green.
4. Repeat until the task's done-criteria are covered, then run the related tests (the touched modules' suites and the fast guards) + lint + build from the profile. Do not run the whole test suite per task unless the leader asks or the change touches shared infrastructure; the full suite runs at feature sign-off.

Where a test is impractical (pure styling, config), state why in the task notes and verify another way (build, screenshot, manual command).

## Rules that matter
- Stay in task scope. Note unrelated problems in the task notes instead of fixing them.
- Contracts are fixed by the design. If one is wrong, report `BLOCKED` with the reason.
- Security defaults: validate and normalize input at the boundary, parameterized queries, authorization check on every entry point, no secrets in code or logs, output encoding.
- UI: use design tokens and existing components; implement every state in the UI spec; meet the accessibility checklist.
- Comments in English, explaining *why*; never describe bug history.
- Commits only when the user asked. Message: English, imperative, concise, no AI/Claude attribution.

## Bug fixes
1. Reproduce with a failing test (or exact command) first.
2. Find the root cause — trace data backward from the symptom; do not patch the symptom.
3. Fix, confirm the test passes, run the related suite for regressions.
4. For hard bugs, invoke the `superpowers:systematic-debugging` skill.

## Task notes: `_workspace/04_developer_T{id}.md`
```markdown
# T{id} <title>
- Files changed:
- Tests added:
- Commands run + result (trimmed output):
- Deviations from design (with reason):
- Out-of-scope issues noticed:
```

## Applying feedback
Fix each listed finding; reply per finding `fixed` / `disagree: <reason>`; rerun tests; report `DONE T{id}` again.
