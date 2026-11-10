# Browser testing (Lightpanda → Playwright headless shell → Claude in Chrome)

Use for any acceptance criterion that is only observable in a browser: UI flows, screen states, responsive layout, PWA behavior (install, offline, update prompt), console errors, network calls from the frontend.

The engine order favors the lightest browser that can prove the criterion, so QA does not load the machine with a full desktop Chrome when a headless one is enough.

## Contents
1. Engine selection & connection
2. Session rules
3. Test procedure
4. Mobile-first viewports
5. PWA checks in the browser
6. Evidence & reporting
7. Failure handling

## 1. Engine selection & connection

Classify each browser criterion first, then pick the engine. Record the engine used per criterion in the QA report.

| Criterion type | Examples | Engine order |
|---|---|---|
| **Headless** — observable from DOM, JS, console or network | flows, form submit/validation, navigation/URL, text and element state, console errors, frontend network calls vs the API contract, auth redirects | **L → P → M → A** |
| **Visual / device** — needs real rendering | responsive layout per viewport, screenshots, animation and transitions, touch targets, service worker, offline/reconnect, update prompt | **P → M → A** (skip L) |
| **Interactive** — needs a real desktop browser or a recording a person watches | installability via Chrome's install UI, a GIF the user asked for, a flow only reproducible in the user's signed-in Chrome | **A → P** |

**L. Lightpanda — lightest, headless criteria only**
Lightpanda is a headless browser without a graphical rendering engine: it runs JS (V8), DOM, XHR/fetch, forms, clicks, cookies and network interception at a fraction of Chrome's cost, but it does not compute visual layout, so it cannot judge visuals, viewports or PWA features.
1. Detect: `command -v lightpanda` (also `~/.local/bin/lightpanda`). Not installed → skip to P and tell the leader once that the user can install it (`brew install lightpanda-io/browser/lightpanda`, or the official installer / release binary from github.com/lightpanda-io/browser). Do not install it yourself.
2. Always set `LIGHTPANDA_DISABLE_TELEMETRY=true`.
3. Drive it in this order:
   - **MCP**: if `mcp__lightpanda__*` tools exist (user configured `lightpanda mcp`), load them in one ToolSearch call and use them.
   - **CDP + Playwright**: start `LIGHTPANDA_DISABLE_TELEMETRY=true lightpanda serve --host 127.0.0.1 --port <free port>` in the background, then run a short script with `playwright-core` — `chromium.connectOverCDP('ws://127.0.0.1:<port>')` — or point the project's Playwright/Puppeteer e2e at that endpoint. Each QA agent uses its own port, so Lightpanda runs do not need to be serialized.
   - **Quick checks**: `lightpanda fetch --dump html|markdown --wait-selector <sel> <url>` to assert rendered DOM/text without a script.
4. Stop the `lightpanda serve` process you started before reporting.
5. **Never report a defect on Lightpanda alone.** A failure that may come from an unsupported Web API (JS error in a browser API, missing element that depends on layout, `matchMedia`/`IntersectionObserver`/`ResizeObserver`-driven behavior) is re-run on P; it is a defect only if it reproduces there. A crash or protocol error in Lightpanda itself → switch to P for the rest of the task.

**P. Playwright with Chromium headless shell (default for visual criteria) + WebKit for iOS**
`chromium-headless-shell` is Chromium's rendering engine without the browser UI, extensions or profile: real layout, screenshots, service workers and DevTools protocol at a much lower cost than desktop Chrome. Playwright uses it for `headless: true` launches.
1. Runner, in this order:
   - The project's Playwright e2e setup (project profile) — add or run specs there for the task's criteria.
   - Otherwise a QA script outside the project manifest: set up once in `_workspace/qa-tools/` (`npm init -y && npm i -D playwright@latest`), install only the shell `npx playwright install chromium --only-shell`, and keep scripts in `_workspace/qa-artifacts/`. Never add dependencies to the project for QA scripts.
2. Launch `chromium.launch({ headless: true })` (do not set a `channel`, which would switch to full Chrome). Use a `browser.newContext()` per scenario with the mobile device descriptor (`devices['Pixel 7']`, `devices['iPhone 15']`) for mobile runs.
3. **WebKit** for criteria that depend on iOS Safari / WKWebView behavior (PWA on iOS, Capacitor iOS, safe areas, iOS-only CSS): `npx playwright install webkit`. If WebKit's system libraries are missing (install needs root via `--with-deps`), report those criteria `not-run` with the command the user must run; do not use `sudo`.
4. Run scripts and e2e through `.claude/team/run-heavy.sh` (they launch a browser process); close the browser in a `finally` block.
5. Capabilities used: `page.setViewportSize`, `page.screenshot({ fullPage: true })`, `context` option `recordVideo` for multi-step flows, `page.on('console' | 'pageerror' | 'requestfailed' | 'response')`, `context.setOffline(true|false)`, `context.serviceWorkers()` (Chromium), `page.route()` to block an API host. Native dialogs never freeze it: handle with `page.on('dialog', (d) => d.accept())` when a flow needs one.

**M. Playwright MCP** — when P cannot run here (no Node/npm, no network for the browser download) and `mcp__plugin_playwright_playwright__*` tools exist: load `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_fill_form`, `browser_resize`, `browser_take_screenshot`, `browser_console_messages`, `browser_network_requests`, `browser_evaluate` in one ToolSearch call and run the same procedure.

**A. Claude in Chrome — interactive criteria, and last fallback**
Uses the user's real desktop Chrome, so it is the heaviest option and is shared with the user.
1. Invoke the `claude-in-chrome` skill (Skill tool) before any browser tool.
2. Load all needed tools in **one** ToolSearch call:
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__form_input,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_console_messages,mcp__claude-in-chrome__read_network_requests,mcp__claude-in-chrome__resize_window,mcp__claude-in-chrome__gif_creator,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__list_connected_browsers,mcp__claude-in-chrome__select_browser`
3. Call `tabs_context_mcp`.
   - Works → connected. Continue.
   - Error / not connected → **self-connect**:
     1. `list_connected_browsers`. One or more listed → `select_browser` (prefer the one on this machine), then `tabs_context_mcp` again.
     2. None listed → launch Chrome in the background (`google-chrome` / `google-chrome-stable` / `chromium` on Linux, `open -a "Google Chrome"` on macOS) with the app URL, wait a few seconds, and call `list_connected_browsers` again — at most 3 checks. The Claude extension connects once Chrome is running and signed in.
     3. Still none → the extension is not installed or not signed in. Do not keep retrying; use the next engine in the criterion's order.

**None available**: mark browser-only criteria `not-tested`, state the reason, and tell the leader what the user can enable: Lightpanda (headless criteria), Node + `npx playwright install chromium --only-shell` (visual criteria), or the Claude in Chrome extension.

## 2. Session rules
- Lightpanda and Playwright (L, P, M) run in the QA agent's own processes and ports, so several QA agents may use them in parallel within the resource budget. Stop every process you started.
- Claude in Chrome (A) is shared with the user: only one QA agent drives it at a time (the leader serializes it); never reuse tab IDs from another session; create your own tab with `tabs_create_mcp` and close it when done; only touch the user's existing tabs if the leader says the user asked for it.
- In A, do not trigger `alert` / `confirm` / `prompt` dialogs — they freeze the extension. Before clicking anything that may open one, check with `javascript_tool`; if it uses a native dialog, test that path on P instead. If a dialog does open, stop and report that the user must dismiss it.
- Filter console output for `error|warn|Uncaught` instead of dumping everything.
- If a tool fails 2–3 times in a row or the page does not respond, stop and report instead of looping.
- Use only test accounts and test data; never enter real credentials or payment details.

## 3. Test procedure
1. Start the app with the dev/preview command from the project profile (background process). Note the URL. For PWA checks, use the **production preview** build (service workers are often disabled in dev).
2. For each acceptance criterion in scope, write the steps before executing them (given/when/then → concrete clicks/inputs/expected observations) and classify it (section 1).
3. Execute on the chosen engine: navigate → interact → verify the **outcome** (text, state, URL, network call, screenshot), not just that a click happened.
   - L/P/M: Playwright locators (`getByRole`, `getByText`) and `expect`-style assertions in the script, or the MCP equivalents.
   - A: `find` + `computer` click/type or `form_input`, verify with `read_page` / `get_page_text` / screenshot.
4. After each flow: check console errors/warnings and network traffic (failed requests, unexpected 4xx/5xx, request/response shapes vs the design contract).
5. Evidence for multi-step flows: Playwright video (`recordVideo`) or screenshots per step on P; `gif_creator` on A (capture extra frames before and after actions). Name files meaningfully (e.g. `T3_checkout_mobile.webm`) under `_workspace/qa-artifacts/`.
6. Stop the dev server and any browser process you started.

## 4. Mobile-first viewports
Run every UI criterion at mobile first, then desktop (`page.setViewportSize` / device descriptors on P, `browser_resize` on M, `resize_window` on A):
- Mobile: 390×844 (also 360×800 for narrow Android when layout is tight); use `isMobile` + `hasTouch` device descriptors on P
- Tablet (if the spec mentions it): 768×1024
- Desktop: 1280×800
Check at each size: correct shell (bottom nav vs sidebar), no horizontal scroll, touch targets ≥ 44px, all UI-spec states reachable (loading, empty, error, success, disabled; offline and reconnecting for mobile apps).

At both mobile sizes also run the compact-layout checks (`ai-dev-team:pwa-headless-ui` → `references/compact-layout.md` §7) on P with worst-case content (longest locale, long unbroken strings, large amounts) and again at font scale 130%: `.claude/team/overflow-check.mjs` reports no offenders, adjacent button pairs that fit share one row, icon/text rows leave no dead space. Attach one long-content screenshot per screen.

## 5. PWA checks in the browser (P on Chromium, A as fallback)
- Manifest and service worker: `page.evaluate(() => navigator.serviceWorker.getRegistration())` resolves with an active worker (or `context.serviceWorkers()`); `link[rel=manifest]` present.
- Offline and reconnect: after first load, `context.setOffline(true)` (or block the API host with `page.route`) → app shell renders and screens show the designed offline banner/screen; `context.setOffline(false)` → the app reconnects to the same screen by itself (`ai-dev-team:pwa-headless-ui` → `references/connectivity.md` §10).
- Update prompt: rebuild with a change, reload → prompt appears and applies.
- Installability: verified on A via Chrome's install UI, or recorded as `manual` if not automatable.

## 6. Evidence & reporting
Add to the QA report per criterion: engine used (L/P-chromium/P-webkit/M/A, plus the confirming engine when an L failure was re-run), viewport/device, steps, observed result, artifact path (video/screenshot/GIF), console/network findings. Browser defects use the standard defect format with the artifact as evidence.

## 7. Failure handling
| Situation | Action |
|---|---|
| Lightpanda not installed, crashes, or lacks an API the page needs | Continue on P; note it in the report |
| Playwright browser cannot be installed (no network, no Node) | Use M, then A; note it in the report |
| WebKit system libraries missing | Report the WebKit criteria `not-run` with the install command for the user |
| Claude in Chrome extension not connected after self-connect | Use the next engine in the criterion's order, or `not-tested` for interactive-only criteria |
| Page doesn't load / dev server fails | Capture the server log, report `QA_BLOCKED` |
| Native dialog froze Chrome (A) | Stop; report that the user must dismiss it in Chrome |
| Flaky step (timing) | Wait for a concrete condition (text/element) and retry once; then report as flaky |
