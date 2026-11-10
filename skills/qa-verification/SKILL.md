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
4. UI tasks: verify each UI-spec state is reachable (loading, empty, error, success, disabled; `offline` and `reconnecting` for mobile apps). Mobile apps using online data: cut the network and restore it (airplane mode, emulator, or Playwright `setOffline`) and confirm the offline UI appears and the app reconnects to the same screen without a tap — checks in `ai-dev-team:pwa-headless-ui` → `references/connectivity.md` §10. Paginated lists: with many pages, the control shows a truncated range with ellipses (never every page), keeps its width while paging, and the current page survives reload via the URL. Resource lists and pickers: checks in `ai-dev-team:pwa-headless-ui` → `references/list-page.md` §9 (filters/sort/page survive reload via the URL query and are not in localStorage, column toggles survive reload, identifying columns cannot be hidden, actions before ID and ID last, the picker modal selects one or many per props and never changes the page URL). CRUD entities: the API and UI checks in `ai-dev-team:technical-design` → `references/record-lifecycle.md` §10, including bulk actions behaving exactly like the single-row actions.
   **Browser testing**: any criterion observable only in a browser (UI flows, responsive layout, PWA install/offline/update, console errors, frontend network calls) is tested in the lightest browser that can prove it: headless criteria (DOM, flows, forms, console, network) on **Lightpanda**, then Playwright; visual and PWA criteria (layout per viewport, screenshots, animation, service worker, offline/reconnect) on **Playwright with Chromium headless shell** (WebKit for iOS-specific behavior), then Playwright MCP; **Claude in Chrome** for interactive criteria (install UI, a GIF the user asked for) and as the last fallback (self-connect: select a connected browser or launch Chrome and re-check). Lightpanda failures are confirmed on Playwright before being reported. Mobile viewport first, then desktop. Follow `references/browser-testing.md`.
5. Append results to the QA report and send the verdict to the leader.

## Feature sign-off
Run the full suite once (through the wrapper) and confirm every acceptance criterion is `pass`. List any `not-tested` with the reason.

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
