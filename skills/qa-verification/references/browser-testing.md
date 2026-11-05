# Browser testing with Claude in Chrome

Use for any acceptance criterion that is only observable in a browser: UI flows, screen states, responsive layout, PWA behavior (install, offline, update prompt), console errors, network calls from the frontend.

## Contents
1. Engine selection & connection
2. Session rules
3. Test procedure
4. Mobile-first viewports
5. PWA checks in the browser
6. Evidence & reporting
7. Failure handling

## 1. Engine selection & connection

Try in this order and record which engine was used in the QA report.

**A. Claude in Chrome (preferred)**
1. Invoke the `claude-in-chrome` skill (Skill tool) before any browser tool.
2. Load all needed tools in **one** ToolSearch call:
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__form_input,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_console_messages,mcp__claude-in-chrome__read_network_requests,mcp__claude-in-chrome__resize_window,mcp__claude-in-chrome__gif_creator,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__list_connected_browsers,mcp__claude-in-chrome__select_browser`
3. Call `tabs_context_mcp`.
   - Works → connected. Continue.
   - Error / not connected → **self-connect**:
     1. `list_connected_browsers`. One or more listed → `select_browser` (prefer the one on this machine), then `tabs_context_mcp` again.
     2. None listed → launch Chrome in the background (`google-chrome` / `google-chrome-stable` / `chromium` on Linux, `open -a "Google Chrome"` on macOS) with the app URL, wait a few seconds, and call `list_connected_browsers` again — at most 3 checks. The Claude extension connects once Chrome is running and signed in.
     3. Still none → the extension is not installed or not signed in. Do not keep retrying; fall back to B.

**B. Playwright MCP** (if `mcp__plugin_playwright_playwright__*` tools exist): load `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_fill_form`, `browser_resize`, `browser_take_screenshot`, `browser_console_messages`, `browser_network_requests`, `browser_evaluate` in one ToolSearch call and run the same procedure headlessly.

**C. Project test runner**: if the project has Playwright/Cypress e2e configured (see project profile), write/run e2e tests there.

**D. None available**: mark browser-only criteria `not-tested`, state the reason, and tell the leader the user can enable it by installing/signing in to the Claude in Chrome extension and keeping Chrome open.

## 2. Session rules (Claude in Chrome)
- Never reuse tab IDs from another session. Create your own tab with `tabs_create_mcp`; only touch the user's existing tabs if the leader says the user asked for it. Close your tabs when done.
- Do not trigger `alert` / `confirm` / `prompt` dialogs — they freeze the extension. Before clicking anything that may open one (delete buttons, "leave page" guards), check with `javascript_tool` whether it uses a native dialog; if so, override it for the test (`window.confirm = () => true`) or test that path with B/C instead. If a dialog does open, stop and report that the user must dismiss it.
- Only one QA agent drives the shared Chrome at a time; the leader serializes browser QA.
- Read console output with a `pattern` filter (e.g. `error|warn|Uncaught`) instead of dumping everything.
- If a tool fails 2–3 times in a row or the page does not respond, stop and report instead of looping.
- Use only test accounts and test data; never enter real credentials or payment details.

## 3. Test procedure
1. Start the app with the dev/preview command from the project profile (background process). Note the URL. For PWA checks, use the **production preview** build (service workers are often disabled in dev).
2. For each acceptance criterion in scope, write the steps before executing them (given/when/then → concrete clicks/inputs/expected observations).
3. Execute: `navigate` → interact (`find` + `computer` click/type, or `form_input`) → verify with `read_page` / `get_page_text` / screenshot. Verify the **outcome** (text, state, URL, network call), not just that a click happened.
4. After each flow: `read_console_messages` (errors/warnings) and `read_network_requests` (failed requests, unexpected 4xx/5xx, request/response shapes vs the design contract).
5. Record multi-step flows with `gif_creator` (capture extra frames before and after actions; name files meaningfully, e.g. `T3_checkout_mobile.gif`), saved under `_workspace/qa-artifacts/`.
6. Stop the dev server you started.

## 4. Mobile-first viewports
Run every UI criterion at mobile first, then desktop (`resize_window` / `browser_resize`):
- Mobile: 390×844 (also 360×800 for narrow Android when layout is tight)
- Tablet (if the spec mentions it): 768×1024
- Desktop: 1280×800
Check at each size: correct shell (bottom nav vs sidebar), no horizontal scroll, touch targets ≥ 44px, all UI-spec states reachable (loading, empty, error, success, disabled).

## 5. PWA checks in the browser
- Manifest and service worker: `javascript_tool` → `navigator.serviceWorker.getRegistration()` resolves with an active worker; `document.querySelector('link[rel=manifest]')` present.
- Offline: after first load, go offline (DevTools offline or block the API host) and reload → app shell renders, data screens show the designed offline state.
- Update prompt: rebuild with a change, reload → prompt appears and applies.
- Installability is verified manually or via Chrome's install UI; record as `manual` if not automatable.

## 6. Evidence & reporting
Add to the QA report per criterion: engine used (A/B/C), viewport, steps, observed result, artifact path (GIF/screenshot), console/network findings. Browser defects use the standard defect format with the artifact as evidence.

## 7. Failure handling
| Situation | Action |
|---|---|
| Extension not connected after self-connect | Fall back to B → C → D; note it in the report |
| Page doesn't load / dev server fails | Capture the server log, report `QA_BLOCKED` |
| Native dialog froze the browser | Stop; report that the user must dismiss it in Chrome |
| Flaky step (timing) | Wait for a concrete condition (text/element) and retry once; then report as flaky |
