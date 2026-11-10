# Resource budget for tests and browser checks

Agents cost almost no local CPU; the commands they run do. A real run (rj-labs, 15 tasks of one PWA) spent most of its wall-clock time on local work nobody asked for: three sign-off QA agents in parallel, each launching its own Chromium; one of them running the full Vitest suite five times "to prove stability"; each screen swept at 6 widths × 2 modes × 2 themes with a new hand-written script and a new browser launch per screen; the same sweep repeated by the implementer, the design QA, the per-task QA and again in a batch before sign-off; agents blocked in `sleep 240` and `while pgrep …; do sleep 5; done` loops waiting for each other's test containers. The full sweep itself is not the waste — UI bugs keep slipping through when a run checks only a few widths or one theme. This file is the `COST` rule pack: full coverage, run cheaply and once per build.

## Contents
1. Who runs what
2. Browser sessions
3. Screenshots, widths and themes
4. Waiting for queued work
5. Feature sign-off
6. Leader rules
7. Checks

## 1. Who runs what
Each check runs once, by the role that owns it. Later roles read the earlier evidence instead of reproducing it.

| Role | Tests | Browser |
|---|---|---|
| Implementer | related tests of the changed files + mapped guards (`BASE-10`), type-check, build once | after the final build: the full sweep (§3) of the changed screens; looks at every contact sheet and fixes what is wrong before `DONE` |
| Code reviewer / security auditor | none (one test via the wrapper to prove a finding) | none |
| Design QA (`ui-ux-designer`) | none | none of its own: judges the contact sheets of the build against the UI spec; captures only a state no sheet shows |
| Per-task QA | the integration/e2e tests it adds | the task's acceptance criteria (flows, states) in the DOM; judges the implementer's contact sheets itself, sheet by sheet, and sweeps again only when the build changed since (§3) |
| Sign-off QA | full suite once | flows that cross task boundaries, plus one full sweep over every screen the feature touched (§5) |

## 2. Browser sessions
- Every Playwright, Chromium, WebKit or e2e run is a heavy command: it goes through `.claude/team/run-heavy.sh`, so only one browser runs on the machine at a time. Lightpanda (no rendering) and a single `lightpanda fetch` are light.
- One run per sweep: `.claude/team/overflow-check.mjs` takes every URL × width × theme in one browser launch. Never a new hand-written script and a new launch per screen; extra checks the script cannot do go in one shared script under `_workspace/qa-artifacts/` that also loops over all URLs in one launch.
- Close every browser, context and tab you opened (`finally` blocks; `tabs_close_mcp` in Claude in Chrome) and stop `lightpanda serve`. A tab left on an animated app page keeps a renderer at full CPU for hours.

## 3. The full sweep
Every changed screen is checked at **every width tier and every theme** the app ships. Fewer widths or one theme lets UI bugs through; the cost is kept down by how the sweep runs, not by skipping parts of it.
- **Matrix**: the profile's `ui_widths` (the project's breakpoint tiers; default `360,390,768,1024,1280,1440,1920`) × `ui_themes` (default `light,dark` when the app has a dark theme) × each display mode the screen has (e.g. embedded and full screen, as separate URLs), with worst-case content (longest strings, many items, large amounts) seeded first.
- **One command**: `.claude/team/run-heavy.sh node .claude/team/overflow-check.mjs --widths <ui_widths> --themes <ui_themes> [--theme-set '<js>'] --shots _workspace/qa-artifacts/T{id}[-r{round}] --sheet <url>...` — every URL, width and theme in one browser launch, overflow and clipping asserted at each combination, phone widths again at 130% font size, and one contact sheet per URL (`*-sheet.png`: all widths × themes, red frame on cells with offenders).
- **Look at it**: open every contact sheet (one image per screen) and judge it against the UI spec — alignment, wrapping, empty space, contrast in dark, states. The assertions catch overflow; the eyes catch the rest. Note each problem with the sheet path and the cell (width, theme).
- **States** the sweep URL does not show (error, empty, open sheet or dialog): add a URL or query that opens the state, or one shared script that loops over them in one launch.
- **Engines**: Chromium headless shell; WebKit only for iOS-specific criteria.
- **Once per build**: the implementer sweeps its final build and records the build id (bundle hash or `git diff` hash) beside the sheets. QA and design QA judge those same sheets with their own eyes; QA sweeps again only when the build id differs. A fix round sweeps only the screens that round changed. A sweep is never repeated on an unchanged build.

## 4. Waiting for queued work
- Call `run-heavy.sh` in the foreground: it waits for its slot by itself. Never wrap it in `sleep`, `pgrep` or polling loops, and never wait for another agent's process.
- A long command you must not block on → run it in the background and wait for the completion notification (or `Monitor` with an until-condition). No `sleep` longer than 10 s, and none in a loop, except while waiting for a server you started to answer.
- A command that queues past `AI_DEV_TEAM_LOCK_WAIT` (exit 75) is reported to the leader, not retried in a loop.

## 5. Feature sign-off
- One `qa-engineer` runs sign-off. It is not split into parallel agents per area.
- The full suite runs once. A failure → rerun that one file up to 3 times; a test that fails only sometimes is a defect. Never rerun the whole suite to prove stability.
- Browser: the cross-task flows of the spec, plus one full sweep (§3) over every screen the feature touched, in one run, every contact sheet looked at.

## 6. Leader rules
- At most **one agent with browser work at a time**. Other agents (implementers, reviewers, browser-free QA) run in parallel within `max_agents`; a second QA that needs a browser waits.
- A brief never raises the budget above this file (no repeated full-suite runs, no second sweep of an unchanged build, no parallel browser agents, no "QA every task again" pass before sign-off) unless the user asked; when the user asks, tell them the cost first.
- Per-task QA happens once per task, right after its review, never batched again later. Before sign-off, rebuild once and hand sign-off the list of per-task artifacts.
- Put "follow `COST` (`ai-dev-team:dev-team` → `references/resource-budget.md`)" in every implementer, QA and design-QA brief.

## 7. Checks
1. **Heavy browsers** — every Playwright / Chromium / WebKit / e2e run went through `run-heavy.sh`, one browser launch per run covering all its URLs and widths.
2. **Full sweep** — every changed screen ran through every `ui_widths` × `ui_themes` combination (and display mode) in one `overflow-check.mjs --sheet` run per build, and every contact sheet was looked at, with problems noted by sheet and cell.
3. **Own role only** — the role ran only the tests and browser checks §1 gives it.
4. **No polling** — no `sleep` loops, `pgrep` waits or waits on another agent's process; queued commands ran in the foreground or as background tasks with a completion notification.
5. **Suite once** — no full-suite run per task or fix round; at sign-off one full run, flaky failures rerun per file.
6. **Cleanup** — every browser, context, tab, `lightpanda serve`, dev server and watcher started was stopped before reporting.
