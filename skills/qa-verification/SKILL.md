---
name: qa-verification
description: "QA procedure: run profile commands, verify each acceptance criterion with evidence, cross-check module boundary contracts (API vs web/mobile consumers), add missing integration tests, and maintain the QA report. Used by qa-engineer per task and before feature sign-off. Not for code-quality review (code-review-checklist)."
---

# QA verification

Run QA incrementally after each task — not once at the end. Most integration bugs live at module boundaries, and they are cheapest to catch right after the boundary is built.

## Per-task procedure
1. Run the test/lint/build commands from `.claude/team/project-profile.md`. Keep trimmed real output.
2. For each acceptance criterion touched by the task: find the test that covers it; if none, write one (test files only). Mark `pass | fail | not-tested`.
3. **Boundary check** for every contract touched (see design "Contracts"):
   - Read the producer (controller/handler/serializer) and every consumer (fetch hook, API client, mobile service, type definitions).
   - Compare field names and casing, types, nullability/optional, enum values, date formats, pagination shape, error codes and error body shape.
   - Any mismatch is a `QA_FAIL` even if unit tests pass.
4. UI tasks: verify each UI-spec state is reachable (loading, empty, error, success, disabled).
5. Append results to the QA report and send the verdict to the leader.

## Feature sign-off
Run the full suite once more and confirm every acceptance criterion is `pass`. List any `not-tested` with the reason.

## Defect format
```
QA_FAIL T{id} — <title>
Repro: <steps / command>
Expected: ...
Actual: ...
Evidence: <output excerpt or file:line on both sides of the contract>
```

## Report: `_workspace/05_qa_report.md`
```markdown
# QA report
## T{id} — <verdict>
| AC | Status | Evidence |
### Contract checks
| Contract | Producer | Consumer | Result |
### Commands
```
