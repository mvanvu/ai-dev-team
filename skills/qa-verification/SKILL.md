---
name: qa-verification
description: "QC procedure: run profile commands, verify each acceptance criterion with evidence, cross-check module boundary contracts (API vs web/mobile consumers), test UI and PWA behavior in a browser (Lightpanda for headless checks, Playwright Chromium headless shell / WebKit for visual and PWA checks, Claude in Chrome for interactive checks and last fallback), add missing integration tests, and maintain the QA report. Used by the qc agent per task and at feature sign-off. Not for code-quality review (code-review-checklist)."
---

# QC verification

Run QC incrementally after each task — not once at the end. Most integration bugs live at module boundaries, and they are cheapest to catch right after the boundary is built. Per-task QC runs in parallel with the reviewer on the same commit.

Verdicts: `QC_PASS T{id}`, `QC_FAIL T{id}` (defects below), `QC_BLOCKED T{id}` (the check cannot run — environment, missing service, a browser that needs the user — with what was checked statically). Every verdict carries the `## Rule check T{id}` table.

## Per-task procedure
1. Read the developer's test/lint/build output in the task notes; do not rerun those tests. Missing output → `QC_FAIL` ("no test evidence"), unless the profile records `tests: none` — then the notes must hold reproduction steps and command output instead. Run only the integration/e2e tests you add or that cover the task's criteria, through `.claude/team/run-heavy.sh`. The full suite is for feature sign-off. Keep trimmed real output.
2. For each acceptance criterion touched by the task: find the test that covers it; if none, write one (test files only). Mark `pass | fail | not-tested`.
3. **Boundary check** for every contract touched (see the plan's "Contracts"):
   - Read the producer (controller/handler/serializer) and every consumer (fetch hook, API client, mobile service, type definitions).
   - Compare field names and casing, types, nullability/optional, enum values, date formats, pagination shape, error codes and error body shape.
   - Any mismatch is a `QC_FAIL` even if unit tests pass.
4. UI tasks: verify each UI-spec state is reachable (loading, empty, error, success, disabled; `offline` and `reconnecting` for mobile apps). Pack-specific behavior — phone layout, lists and pickers, record lifecycle, connectivity, PWA, Capacitor — is verified rule by rule in step 5.
   **Browser testing**: any criterion observable only in a browser (UI flows, responsive layout, PWA install/offline/update, console errors, frontend network calls) is tested in the lightest browser that can prove it: headless criteria (DOM, flows, forms, console, network) on **Lightpanda**, then Playwright; visual and PWA criteria (layout per viewport, screenshots, animation, service worker, offline/reconnect) on **Playwright with Chromium headless shell** (WebKit for iOS-specific behavior), then Playwright MCP; **Claude in Chrome** for interactive criteria (install UI, a GIF the user asked for) and as the last fallback (self-connect: select a connected browser or launch Chrome and re-check). Lightpanda failures are confirmed on Playwright before being reported. Mobile viewport first, then desktop. Follow `references/browser-testing.md`. Web screens also get the `SWEEP` (`ai-dev-team:dev-team` → `references/resource-budget.md` §3): judge every contact sheet of the build; sweep again only when the build id changed.
   **Flutter / native UI**: no browser. Run the widget and golden tests the task added or touched at the profile's `ui_sizes` and both themes (`flutter test <files>` through the wrapper), `integration_test` on a device or emulator when one is available (else `not-run` with the reason), and `.claude/team/rule-checks.sh flutter-overflow` on the saved test output; native Swift/Kotlin: the project's UI tests (XCTest UI / Compose UI tests) for the changed screens.
5. **Rule check**: for every pack in the task's `Rules` that names `qc` in `ai-dev-team:dev-team` → `references/rule-packs.md` §2, verify each rule ID in the running app, with a test, or with its script when §9 of that file lists one — not by trusting the developer's table — and write the `## Rule check T{id}` table (`pass | fail | n-o`, evidence = test name, command output or artifact path). Without a `Rules` column (standalone QC), pick the packs from that file's "Applies when" table. A `fail` is a `QC_FAIL` defect with the rule ID in its title; notes without a `## Rule compliance` section are a `QC_FAIL`.
6. Append results to the QC report and send the verdict to the leader.

## Feature sign-off
One qc agent runs sign-off. Run the full suite once (through the wrapper); a failure is rerun per file (up to 3×), never the whole suite again. UI: cross-task flows plus one sweep over every web screen the feature touched (Flutter/native: the widget/golden suites once) (`ai-dev-team:dev-team` → `references/resource-budget.md` §5). Confirm every acceptance criterion is `pass`. List any `not-tested` with the reason.

## Defect format
```
QC_FAIL T{id} — <title>
Repro: <steps / command>
Expected: ...
Actual: ...
Evidence: <output excerpt or file:line on both sides of the contract>
```

## Report: `_workspace/05_qc_report.md`
```markdown
# QC report
## T{id} — <verdict>
| AC | Status | Evidence |
### Rule check
| Rule | Result | Evidence |
### Contract checks
| Contract | Producer | Consumer | Result |
### Commands
```
