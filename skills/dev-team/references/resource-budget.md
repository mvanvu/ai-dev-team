# Resource budget for tests, builds and UI sweeps

Agents cost almost no local CPU; the commands they run do. Runs slow down when the same check runs twice, when several agents start test runners or browsers at once, and when agents wait for each other in polling loops — not when coverage is complete. This file holds two rule packs: `COST` (every task: how heavy commands run) and `SWEEP` (tasks that change a web-rendered screen: full width × theme coverage, run cheaply and once per build).

## Contents
1. Who runs what
2. Heavy commands and browsers
3. The UI sweep
4. Waiting for queued work
5. Feature sign-off
6. Leader rules
7. `COST` checks
8. `SWEEP` checks

## 1. Who runs what
Each check runs once, by the agent that owns it. Later agents read the earlier evidence instead of reproducing it.

| Agent | Tests | UI |
|---|---|---|
| developer | related tests of the changed files + mapped guards (`BASE-10`), type-check, build once | web screens: the sweep (§3) of the final build, every contact sheet looked at and fixed before `DONE`; Flutter/native: widget/golden tests at the size tiers |
| reviewer | none (one test via the wrapper to prove a finding; the dependency audit when a manifest changed) | design QA on the contact sheets of the build; captures only a state no sheet shows |
| qc (per task) | the integration/e2e tests it adds | acceptance criteria in the DOM or widget tree; judges the contact sheets itself; sweeps again only when the build id changed |
| qc (sign-off) | full suite once | cross-task flows, plus one sweep over every screen the feature touched (§5) |

## 2. Heavy commands and browsers
- Test suites, builds, e2e runs, dependency audits and every Playwright / Chromium / WebKit launch go through `.claude/team/run-heavy.sh`. The wrapper lets one heavy command run at a time on the machine (or `heavy_workers` slots when the profile says so), so agents may work in parallel without starting browsers and runners in parallel. Lightpanda checks and a single `lightpanda fetch` are light.
- One launch per run: `overflow-check.mjs` takes every URL × width × theme in one browser launch. Never a new hand-written script and a new launch per screen; checks the script cannot do go into one shared script under `_workspace/qa-artifacts/` that also loops over all URLs in one launch.
- WebKit only for criteria that depend on iOS Safari / WKWebView.
- Claude in Chrome drives the user's own browser and cannot be queued by the wrapper: only one agent uses it at a time, and only for the criteria that need it (`ai-dev-team:qa-verification` → `references/browser-testing.md`).
- Close every browser, context and tab you opened (`finally` blocks; `tabs_close_mcp`), stop `lightpanda serve`, dev servers, watchers and emulators. A tab left on an animated page keeps a renderer at full CPU for hours.

## 3. The UI sweep
Every changed web screen is checked at **every width tier and every theme** the app ships. Checking only some widths or one theme lets layout bugs through; cost is kept down by how the sweep runs, not by skipping parts of it.
- **Matrix**: the profile's `ui_widths` × `ui_themes` × each layout variant the UI spec lists for the screen (e.g. embedded vs full-screen, signed-in vs guest — as separate URLs). `ui_widths` come from the project: its target devices and the breakpoints its CSS or tokens define (a phone-only app has no desktop tiers; a desktop-only console has no phone tiers). Load worst-case content first (longest strings, many items, large amounts).
- **One command**: `.claude/team/run-heavy.sh node .claude/team/overflow-check.mjs --widths <ui_widths> --themes <ui_themes> [--theme-set '<js>'] [--ready <selector>] --shots _workspace/qa-artifacts/T{id}[-r{round}] --sheet <url>...` — overflow and clipping asserted at every combination, phone widths again at 130% font size, one contact sheet per URL (`*-sheet.png`: every width × theme, red frame on cells with offenders), and `build-id.txt` beside them.
- **Look at it**: open every contact sheet and judge it against the UI spec — alignment, wrapping, empty space, contrast in dark, states. The script catches overflow; looking catches the rest. Note each problem with the sheet path and the cell (width, theme).
- **States** the URL does not show (error, empty, open sheet or dialog): a URL or query that opens the state, or one shared script that loops over them in one launch.
- **Once per build**: the developer sweeps its final build. The reviewer and qc judge those same sheets; qc sweeps again only when `.claude/team/rule-checks.sh build-id` now prints a different value than `build-id.txt`. A fix round sweeps only the screens that round changed.
- Flutter and native UI are not swept in a browser: widget and golden tests at the same size tiers and themes play this role (`ai-dev-team:qa-verification`).

## 4. Waiting for queued work
- Call `run-heavy.sh` in the foreground: it waits for its slot by itself. Never wrap it in `sleep`, `pgrep` or polling loops, and never wait for another agent's process.
- A long command you must not block on → run it in the background and wait for the completion notification (or `Monitor` with an until-condition). No `sleep` longer than 10 s, and none in a loop, except while waiting for a server you started to answer.
- A command that queues past `AI_DEV_TEAM_LOCK_WAIT` (exit 75) is reported to the leader, not retried in a loop.

## 5. Feature sign-off
- One `qc` agent runs sign-off; it is not split into parallel agents per area.
- The full suite runs once. A failure → rerun that one file up to 3 times; a test that fails only sometimes is a defect. Never rerun the whole suite to prove stability.
- UI: the cross-task flows of the spec, plus one sweep over every web screen the feature touched (Flutter/native: the widget/golden suites once), every contact sheet looked at.

## 6. Leader rules
- A brief never raises this budget (repeated full-suite runs, a second sweep of an unchanged build, parallel sign-off agents, a "check every task again" pass before sign-off) unless the user asked; when the user asks, tell them the cost first.
- QC runs once per task, right after the task's build, never batched again later.
- Hand sign-off the list of per-task artifacts.

## 7. `COST` checks
1. **Heavy commands** — test suites, builds, e2e, audits and browser launches went through `run-heavy.sh`; one browser launch per run covering all its URLs and widths.
2. **Own role only** — the agent ran only the tests and UI checks §1 gives it.
3. **No polling** — no `sleep` loops, `pgrep` waits or waits on another agent's process; queued commands ran in the foreground or as background tasks with a completion notification.
4. **Suite once** — no full-suite run per task or fix round; at sign-off one full run, flaky failures rerun per file.
5. **Cleanup** — every browser, context, tab, `lightpanda serve`, dev server, watcher and emulator started was stopped before reporting.

## 8. `SWEEP` checks
1. **Full matrix** — every changed web screen (and each layout variant in the UI spec) ran through every `ui_widths` × `ui_themes` combination with worst-case content, in one `overflow-check.mjs --sheet` run; no offenders left.
2. **Looked at** — every contact sheet was judged against the UI spec, problems noted by sheet path and cell.
3. **Once per build** — `build-id.txt` sits beside the sheets; no second sweep of an unchanged build; a fix round re-swept only the screens it changed.
