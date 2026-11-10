# Dev Team orchestrator — test scenarios

Expected behavior of the `ai-dev-team:dev-team` skill, used when changing or evaluating the orchestrator.

## Normal flow — feature
1. User: "Add password reset by email." Profile exists (Symfony + React); `superpowers` is installed.
2. Leader runs `superpowers:brainstorming`: one question at a time, token TTL defaults to 30 min, spec approved; leader adds `has_ui=true`, `security_sensitive=true`, `AC-1…AC-5`.
3. Phase 3: developer (UI design) and reviewer (threat model, `SEC-1…SEC-3`) run in parallel while the leader writes the plan with `superpowers:writing-plans`, stopping before its execution handoff; board: 4 tasks, 2 tagged `security`, 1 `ui`.
4. Build loop: T2's `DONE` is accepted only with its `## Rule compliance` table; T2's reviewer (code + security) and qc run in parallel and each returns a `## Rule check T2` table; reviewer reports `high` (token not single-use) → same developer fixes, Rounds = 1 → reviewer re-verifies `APPROVED`; `QC_PASS` stands.
5. One qc sign-off: full suite once. Final review workflow: `correctness` + `security` + `ui`, all `reviewer` agents, 1 minor finding. Report lists 4 tasks done, all ACs pass.

## Normal flow — small change
1. User: "Quick fix: the CSV export date is off by one." Profile exists.
2. Leader writes a one-row board (Rules: `QUERY` not needed; `BASE` implied) and briefs a developer; the developer adds a failing test, fixes, reports `DONE` with `BASE-1/2/3/4/9` rows.
3. One reviewer `APPROVED`; no qc, no Phase 5. Report in a few lines.

## Normal flow — new template pack
1. User: "Add a 'corporate' template." Profile: Vue 3 + reka-ui, PWA, Capacitor.
2. Developer (UI design) specs tokens + per-component recipe changes; a developer copies `src/templates/default/` → `corporate/`, edits only tokens/recipes/shells, sweeps the changed screens at every `ui_widths` × `ui_themes`.
3. Reviewer confirms `git diff` touches nothing under `src/ui/core/` or `src/features/` and judges the contact sheets; qc runs component tests against both templates without re-sweeping the same build id.

## Error flow — Phase 5 dimension fails
1. The `ui` dimension agent fails twice → returns null.
2. Workflow logs "1 review dimension(s) failed"; `missingDimensions: 1`.
3. Leader reports the missing UI review and offers to resume it via `resumeFromRunId`.

## Error flow — missing compliance report
1. Developer reports `DONE T3`; the notes have no `## Rule compliance` rows for `COMPACT`.
2. Leader returns the task with the missing rule IDs (not a fix round); the developer finds `COMPACT-3` failing (two buttons stacked), fixes it, reports again.
3. Qc marks `COMPACT-2` `fail` (a long name overflows at 360px on the contact sheet) → fix request, ledger entry; after the fix qc re-checks → `pass` → task `done`.

## Error flow — interrupted run
1. A usage limit hits while T4 is in fix round 2. Leader writes `_workspace/gaps.md`; the board shows T4 `fix`, Rounds 2.
2. User: "continue". Phase 0 sees unfinished tasks, reads `04_dev_T4.md` and `git diff`, briefs a fresh developer "continue T4 from these notes"; the round cap stays at 3 with 1 round left.

## Error flow — QC blocked
1. Qc returns `QC_BLOCKED T2`: the test database container is down.
2. Leader starts it with the profile's command (or asks the user), then sends qc the same request again; T2 is not marked `done` meanwhile.
