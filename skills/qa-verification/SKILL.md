---
name: qa-verification
description: "QA procedure: run profile commands, verify each acceptance criterion with evidence, cross-check module boundary contracts (API vs web/mobile consumers), test UI and PWA behavior in a browser (Lightpanda for headless checks, Playwright Chromium headless shell / WebKit for visual and PWA checks, Claude in Chrome for interactive checks and last fallback), add missing integration tests, and maintain the QA report. Used by qa-engineer per task and before feature sign-off. Not for code-quality review (code-review-checklist)."
---

# QA verification

Run QA incrementally after each task — not once at the end. Most integration bugs live at module boundaries, and they are cheapest to catch right after the boundary is built. Per-task QA runs in parallel with code review on the same commit.

## Per-task procedure
1. Read the implementer's test/lint/build output in the task notes; do not rerun those tests. Missing output → `QA_FAIL` ("no test evidence"). Run only the integration/e2e tests you add or that cover the task's criteria, through `.claude/team/run-heavy.sh`. The full suite is for feature sign-off. Keep trimmed real output.
2. For each acceptance criterion touched by the task: find the test that covers it; if none, write one (test files only). Mark `pass | fail | not-tested`.
3. **Boundary check** for every contract touched (see design "Contracts"):
   - Read the producer (controller/handler/serializer) and every consumer (fetch hook, API client, mobile service, type definitions).
   - Compare field names and casing, types, nullability/optional, enum values, date formats, pagination shape, error codes and error body shape.
   - Any mismatch is a `QA_FAIL` even if unit tests pass.
4. UI tasks: verify each UI-spec state is reachable (loading, empty, error, success, disabled; `offline` and `reconnecting` for mobile apps). Pack-specific behavior — phone layout, lists and pickers, record lifecycle, connectivity, PWA, Capacitor — is verified rule by rule in step 5.
   **Browser testing**: any criterion observable only in a browser (UI flows, responsive layout, PWA install/offline/update, console errors, frontend network calls) is tested in the lightest browser that can prove it: headless criteria (DOM, flows, forms, console, network) on **Lightpanda**, then Playwright; visual and PWA criteria (layout per viewport, screenshots, animation, service worker, offline/reconnect) on **Playwright with Chromium headless shell** (WebKit for iOS-specific behavior), then Playwright MCP; **Claude in Chrome** for interactive criteria (install UI, a GIF the user asked for) and as the last fallback (self-connect: select a connected browser or launch Chrome and re-check). Lightpanda failures are confirmed on Playwright before being reported. Mobile viewport first, then desktop. Follow `references/browser-testing.md`.
5. **Rule check**: for every pack in the task's `Rules` that names `qa-engineer` in `ai-dev-team:dev-team` → `references/rule-packs.md` §2, verify each rule ID in the running app, with a test, or with its script when §9 of that file lists one — not by trusting the implementer's table — and write the `## Rule check T{id}` table (`pass | fail | n-o`, evidence = test name, command output or artifact path). Without a `Rules` column (standalone QA), pick the packs from that file's "Applies when" table. A `fail` is a `QA_FAIL` defect with the rule ID in its title; notes without a `## Rule compliance` section are a `QA_FAIL`.
6. Append results to the QA report and send the verdict to the leader.

## Feature sign-off
One QA agent runs sign-off. Run the full suite once (through the wrapper); a failure is rerun per file (up to 3×), never the whole suite again. Browser: cross-task flows plus one overflow run over the touched screens; cite per-task artifacts for per-screen visuals (`ai-dev-team:dev-team` → `references/resource-budget.md` §5). Confirm every acceptance criterion is `pass`. List any `not-tested` with the reason.

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
### Rule check
| Rule | Result | Evidence |
### Contract checks
| Contract | Producer | Consumer | Result |
### Commands
```
