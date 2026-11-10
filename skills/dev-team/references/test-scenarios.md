# Dev Team orchestrator — test scenarios

Expected behavior of the `ai-dev-team:dev-team` skill, used when changing or evaluating the orchestrator.

## Normal flow
1. User: "Add password reset by email." Profile exists (Symfony + React).
2. Architect (spec mode) returns spec with `has_ui=true`, `security_sensitive=true`, 1 open question (token TTL; default 30 min) → user accepts default.
3. Architect writes the spec; design phase continues the same architect + designer + security in parallel; architect reconciles → 5 tasks (2 tagged security, 1 tagged ui).
4. Build loop: each brief carries the task's rule packs; T2's `DONE` is accepted only with its `## Rule compliance` table; T2's code-reviewer, security-auditor and QA run in parallel and each returns a `## Rule check T2` table; security reports `high` (token not single-use) → developer fixes → security re-review `SECURE`; QA_PASS stands.
5. Final review workflow: 3 dimensions, 1 minor finding. Report lists 5 tasks done, all ACs pass.

## Normal flow — new template pack
1. User: "Add a 'corporate' template." Profile: Vue 3 + reka-ui, PWA, Capacitor.
2. Designer specs tokens + per-component recipe changes; pwa-frontend-engineer copies `src/templates/default/` → `corporate/`, edits only tokens/recipes/shells.
3. Code-reviewer confirms `git diff` touches no file under `src/ui/core/` or `src/features/`; type-check proves the contract is complete; QA runs component tests against both templates.

## Error flow
1. During Phase 5 the `ui` dimension agent fails twice → returns null.
2. Workflow logs "1 review dimension(s) failed"; result has `missingDimensions: 1`.
3. Leader reports the missing UI review in Phase 6 and offers to resume it via `resumeFromRunId`.

## Error flow — missing compliance report
1. `pwa-frontend-engineer` reports `DONE T3`; the notes have no `## Rule compliance` rows for `COMPACT`.
2. Leader returns the task with the missing rule IDs (not counted as a fix round); the implementer checks them, finds `COMPACT-3` failing (two buttons stacked), fixes it and reports again.
3. QA's rule check marks `COMPACT-2` `fail` (a long name overflows at 360px) → merged into the fix request, appended to `_workspace/rule-violations.md`; after the fix QA re-checks → `pass` → task `done`.
