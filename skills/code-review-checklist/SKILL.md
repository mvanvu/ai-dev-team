---
name: code-review-checklist
description: "Checklist and output format for reviewing a code diff: correctness, edge cases, contract conformance, error handling, tests, maintainability, performance; plus adversarial verification of findings. Used by the reviewer agent and by the dev-team final review workflow. Not for security-specific audits (security-review-checklist) or UI conformance (ui-ux-design)."
---

# Code review checklist

## Determine scope
- Task review: the task's own diff — its commit, or `$TEAM_BIN/rule-checks.sh task-diff T{id} -- <task files>` as the brief says (a plain `git diff` mixes in every other uncommitted task). Read the diff itself, every changed file; the developer's notes say what was intended, the diff says what was done. List the files in a `## Files read` section of the verdict (`read`, or `skipped — <why>` for generated files and lockfiles). Read added response fields, serializers, normalizers, log and audit output line by line: data leaks hide there.
- Reuse (`BASE-16`): anything the task added that the project already had (`$TEAM_STATE/capabilities.md`, a search by name) is a finding — `major` when it duplicates logic that must stay in one place (access checks, money, validation), else `minor`.
- Branch/PR review: `git diff <base>...HEAD`.

Test, lint and build results come from the task notes; do not rerun them. Missing or failing output in the notes is itself a finding (`major`).

## Rule check
The brief lists the task's rule packs. For `BASE` (except its self-attested rules) and every pack that names `reviewer` in `ai-dev-team:dev-team` → `references/rule-packs.md` §2, check each rule ID against the code — open the developer's evidence, then verify the rule itself (rerun its script when §9 of that file lists one; they are light commands) — and return the `## Rule check T{id}` table (`pass | fail | n-o`) with the verdict. A `fail` is also a finding with the rule ID in its title; a `pass` claimed without real evidence, or notes without a `## Rule compliance` section, is a `major` finding. Without a `Rules` column (branch/PR review), pick the packs from that file's "Applies when" table. Severity of a failed rule: `ARCH`, `LIST`, `LIFE`, `QUERY` and `BASE-2`/`BASE-9` are `major` or higher (they break template swapping, list reuse, single-row/bulk parity, contracts or security defaults); `COMPACT` is `major` when content can overflow or clip and `minor` when it only wastes space; untruncated pagination is `minor`. Any `major` fail means `CHANGES_REQUESTED`.

## Checklist (in priority order)
1. **Correctness** — does the code do what the spec/acceptance criteria say? Trace one realistic input end to end.
2. **Edge cases** — empty, null, boundaries, duplicates, concurrency, partial failure, time zones.
3. **Contract conformance** — request/response shapes, types, nullability and error codes match the design exactly.
4. **Error handling** — errors are not swallowed; user-facing errors are meaningful; resources are released.
5. **Tests** — critical logic has tests; tests assert behavior, not implementation; failure paths covered.
6. **Maintainability** — follows repo conventions; no dead code, no needless abstraction or duplication of existing utilities.
7. **Performance** — query count must not grow with row count: no query or request per row, relations and aggregates loaded by eager loading / keyed batch / grouped query, set-based bulk writes, a query-count test for each list, export and bulk path (`references/query-performance.md` §4, rule pack `QUERY` — always check it when the diff touches data access, even without a `Rules` column; an N+1 on a list or bulk path is `major`). Also unbounded loops/queries, missing pagination, heavy work on hot paths or the UI thread.
8. **Security** — when the brief does not already include the security checklist and you see a security smell, load `ai-dev-team:security-review-checklist` and check it in the same pass.

## Finding format
```
[severity] file:line — title
Scenario: <input/state> → <wrong result>
Fix: <concrete suggestion>
```
Severity: `blocker | major | minor`. Verdict: `APPROVED` (no blocker/major) or `CHANGES_REQUESTED`.

**Severity anchors** — judge by what a user would hit, not by the size of the fix:
- `blocker`: data loss or corruption, a security hole, the build or main flow broken.
- `major`: the task's feature does not work, or fails silently, in a state a user can reach — a sound that never plays after a refresh, edits dropped on retry, a list that never updates, a queue that grows without bound and delays other messages; a contract mismatch; a missing test for a changed behavior.
- `minor`: no change in behavior a user can see — naming, structure, a defensive check for a caller that does not exist yet, style.
A one-line fix can still be `major`; a `minor` with "never", "lost", "silently" or "stops working" in its scenario is mis-filed.

## Structured output (workflow)
```json
{ "findings": [ { "title": "", "file": "", "line": 0, "severity": "blocker|major|minor", "scenario": "", "fix": "" } ] }
```

## Adversarial verification
When asked to verify a finding: actively try to refute it (read surrounding code, callers, guards, tests). Return `confirmed` only if the failure scenario is reachable; `refuted` if a guard or invariant prevents it; `uncertain` otherwise. Always give the reason.
