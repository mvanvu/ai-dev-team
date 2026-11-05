---
name: code-review-checklist
description: "Checklist and output format for reviewing a code diff: correctness, edge cases, contract conformance, error handling, tests, maintainability, performance; plus adversarial verification of findings. Used by code-reviewer and by the dev-team final review workflow. Not for security-specific audits (security-review-checklist) or UI conformance (ui-ux-design)."
---

# Code review checklist

## Determine scope
- Task review: files listed in `_workspace/04_developer_T{id}.md` or `_workspace/04_pwa_T{id}.md`, plus `git diff` if the repo is under git.
- Branch/PR review: `git diff <base>...HEAD`.

## Checklist (in priority order)
1. **Correctness** — does the code do what the spec/acceptance criteria say? Trace one realistic input end to end.
2. **Edge cases** — empty, null, boundaries, duplicates, concurrency, partial failure, time zones.
3. **Contract conformance** — request/response shapes, types, nullability and error codes match the design exactly.
4. **Error handling** — errors are not swallowed; user-facing errors are meaningful; resources are released.
5. **Tests** — critical logic has tests; tests assert behavior, not implementation; failure paths covered.
6. **Maintainability** — follows repo conventions; no dead code, no needless abstraction or duplication of existing utilities.
   Frontend with headless architecture: features import only `@/ui/core`; core components hold no visual classes; templates hold no behavior; a template-only task changes nothing outside `src/templates/`. Any breach is `major` — it breaks template swapping.
7. **Performance** — N+1 queries, unbounded loops/queries, missing pagination, heavy work on hot paths or the UI thread.
8. **Security smell** — if seen, tag `→ security` (do not deep-dive; that's security-auditor's job).

## Finding format
```
[severity] file:line — title
Scenario: <input/state> → <wrong result>
Fix: <concrete suggestion>
```
Severity: `blocker | major | minor`. Verdict: `APPROVED` (no blocker/major) or `CHANGES_REQUESTED`.

## Structured output (workflow)
```json
{ "findings": [ { "title": "", "file": "", "line": 0, "severity": "blocker|major|minor", "scenario": "", "fix": "" } ] }
```

## Adversarial verification
When asked to verify a finding: actively try to refute it (read surrounding code, callers, guards, tests). Return `confirmed` only if the failure scenario is reachable; `refuted` if a guard or invariant prevents it; `uncertain` otherwise. Always give the reason.
