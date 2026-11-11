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
| developer | related tests of the changed files + mapped guards (`BASE-10`), type-check, build once | web screens: the sweep (§3) of the final build over the screens and **states the task changed** (every renderer of a changed shared component included), every contact sheet looked at and fixed before `DONE`; no audit of screens the task does not change; Flutter/native: widget/golden tests at the size tiers |
| reviewer | none (one test via the wrapper to prove a finding; the dependency audit when a manifest changed) | design QA on the contact sheets of the build; captures only a state no sheet shows |
| qc (per task) | the integration/e2e tests it adds | acceptance criteria in the DOM or widget tree; judges the developer's sheets; one sweep of the final build over **every state** of the changed screens (the developer covered only the changed ones); again only when the build id changed |
| qc (sign-off) | full suite once | cross-task flows, plus one sweep over every screen the feature touched (§5) |

## 2. Heavy commands and browsers
- Test suites, builds, e2e runs, dependency audits and every Playwright / Chromium / WebKit launch go through `$TEAM_BIN/run-heavy.sh`. The wrapper lets one heavy command run at a time on the machine (or `heavy_workers` slots when the profile says so), so agents may work in parallel without starting browsers and runners in parallel. Lightpanda checks and a single `lightpanda fetch` are light.
- One launch per run: `overflow-check.mjs` takes every URL × width × theme in one browser launch. Never a new hand-written script and a new launch per screen; checks the script cannot do go into one shared script under `$TEAM_WS/qa-artifacts/` that also loops over all URLs in one launch. Throwaway scripts and specs live there too, never in the project's test or e2e directories.
- An e2e suite is a full suite: per task run only the spec files the task adds or changes (file arguments or `--grep`), never the whole e2e target. Lint and static analysis per task and fix round run on the changed paths; the whole-project run happens once, at the end of the task.
- **Lightest tool for the question** (every role, developer included): API data → `curl` + `jq` (no browser); DOM or text a page renders with JavaScript → `LIGHTPANDA_DISABLE_TELEMETRY=true lightpanda fetch --dump html|markdown --wait-selector <sel> <url>` when Lightpanda is installed (`command -v lightpanda`, also `~/.local/bin/lightpanda`) — light, no `run-heavy.sh` needed; layout, screenshots, overflow → Playwright through `overflow-check.mjs` and `run-heavy.sh`. Never conclude a defect from Lightpanda alone: it lacks layout and some Web APIs, so confirm a Lightpanda failure on Chromium first (`ai-dev-team:qa-verification` → `references/browser-testing.md`).
- WebKit only for criteria that depend on iOS Safari / WKWebView.
- Claude in Chrome drives the user's own browser and cannot be queued by the wrapper: only one agent uses it at a time, and only for the criteria that need it (`ai-dev-team:qa-verification` → `references/browser-testing.md`).
- Close every browser, context and tab you opened (`finally` blocks; `tabs_close_mcp`), stop `lightpanda serve`, dev servers, watchers and emulators. A tab left on an animated page keeps a renderer at full CPU for hours.

## 3. The UI sweep
Every changed web screen is checked at **every width tier and every theme** the app ships. Checking only some widths or one theme lets layout bugs through; cost is kept down by how the sweep runs, not by skipping parts of it.
- **Matrix**: the profile's `ui_widths` × `ui_themes` × each layout variant the UI spec lists for the screen (e.g. embedded vs full-screen, signed-in vs guest — as separate URLs). `ui_widths` come from the project: its target devices and the breakpoints its CSS or tokens define (a phone-only app has no desktop tiers; a desktop-only console has no phone tiers). Load worst-case content first (longest strings, many items, large amounts).
- **One command**: `$TEAM_BIN/run-heavy.sh node $TEAM_BIN/overflow-check.mjs --widths <ui_widths> --themes <ui_themes> [--theme-set '<js>'] [--ready <selector>] [--init <ui_seed>] --shots $TEAM_WS/qa-artifacts/T{id}[-r{round}] --sheet <url>...` — overflow and clipping asserted at every combination, phone widths again at 130% font size, one contact sheet per URL (`*-sheet.png`: every width × theme, red frame on cells with offenders), and `build-id.txt` beside them.
- **Look at it**: open every contact sheet and judge it against the UI spec and the `COMPACT` checks — alignment, wrapping, empty space (a control or total on a row of its own that would fit beside its neighbour is a fail), contrast in dark, states. The script catches overflow; looking catches the rest, so "no offenders" is never the verdict on its own. When the task came from a user complaint, the notes quote the complaint and name the before/after cells that show it is gone. Note each problem with the sheet path and the cell (width, theme).
- **States** the URL does not show (error, empty, open sheet or dialog): a URL or query that opens the state, or one shared script that loops over them in one launch.
- **Which states**: the developer sweeps the states its change affects (the changed component open, filled, empty, error); the full list of states of the changed screens is swept once, by qc, on the final build. Fix rounds sweep only the states that round changed.
- **Audits are design work**: a sweep across screens the task does not change ("check the whole app for density") is a UI design task (`developer` in UI design mode) planned before the build, never part of a build task.
- **Worst-case content**: load it with the profile's `ui_seed` (`--init <file>`: a script that seeds storage before the app loads, kept in `$TEAM_STATE/seed/`) or the URLs it names. A task that has to build the seed writes it there and reports it in the notes; the leader adds it to the profile so later tasks reuse it.
- **Reusable flows**: steps that reach a state through the UI (log in, open an order, open the bill) are scripts in `$TEAM_STATE/flows/` listed in the profile's `ui_flows`, reused by every later developer and qc. The first agent that needs a flow writes it there (one module exporting small async helpers), reports it in its notes, and the leader adds it to the profile. Never rewrite a flow the profile lists.
- **Reading the output**: `overflow-check.mjs` groups each offender across cells (`— N cell(s): …`) and ends with a `summary:` line; `--verbose` prints one line per cell. Known, accepted offenders go in `--allow <selector>` with the reason in the notes.
- **Every renderer**: a task that changes a shared component, style or layout primitive lists every screen and route that renders it — found by searching its usages, including other apps, modes and embedded variants of the same screen — in its task row, and the sweep covers each of them.
- **Light sweep** (light-tier routes: small change, layout complaint — dev-team routing): only the phone widths of `ui_widths` (< 768) plus the widest one, every theme. Phone cells also run at 130% font size.
- **Once per build**: the developer sweeps its final build (changed states). The reviewer judges those sheets; qc sweeps every state once, and again only when `$TEAM_BIN/rule-checks.sh build-id` now prints a different value than `build-id.txt`. A fix round sweeps only the screens that round changed.
- Flutter and native UI are not swept in a browser: widget and golden tests at the same size tiers and themes play this role (`ai-dev-team:qa-verification`).

## 4. Waiting for queued work
- Call `run-heavy.sh` in the foreground: it waits for its slot by itself. Never wrap it in `sleep`, `pgrep` or polling loops, and never wait for another agent's process.
- A long command you must not block on → run it in the background and wait for the completion notification (or `Monitor` with an until-condition). No `sleep` longer than 10 s, and none in a loop, except while waiting for a server you started to answer. Waiting for an output file to appear (`until [ -s file ]; do sleep …`, `timeout … bash -c 'until …'`) is polling too: run the producing command in the foreground or as a background task with a notification.
- `run-heavy.sh` prints the command that holds the lock (and its directory) when it has to wait; a holder from another project is normal machine-wide queuing — report the wait in the notes, do not work around the wrapper.
- A command that queues past `AI_DEV_TEAM_LOCK_WAIT` (exit 75) is reported to the leader, not retried in a loop.

## 5. Feature sign-off
- One `qc` agent runs sign-off; it is not split into parallel agents per area.
- The full suite runs once. A failure → rerun that one file up to 3 times; a test that fails only sometimes is a defect. Never rerun the whole suite to prove stability.
- UI: the cross-task flows of the spec, plus one sweep over every web screen the feature touched (Flutter/native: the widget/golden suites once), every contact sheet looked at.
- Sign-off starts only after the last task is confirmed (its review, qc or quick-pass re-check done).
- **Light sign-off** — a run made only of light-tier tasks (small changes, layout complaints): one `qc` runs the union of the tasks' related tests and guards, the type-check, and one smoke pass of the touched flows; no full suite, no sweep (each task already swept its states). The full suite runs instead when the user asks to commit, push or open a PR, or when the run touched shared code (shared modules, schema, build config).
- **Build currency** is checked with `$TEAM_BIN/rule-checks.sh build-id` against the `build-id.txt` beside the last sheets — never by rebuilding. A different id means the last build is stale: report it; rebuild only when the leader says so.

## 6. Leader rules
- A brief never raises this budget (repeated full-suite runs, a second sweep of an unchanged build, parallel sign-off agents, a "check every task again" pass before sign-off) unless the user asked; when the user asks, tell them the cost first.
- QC runs once per task, right after the task's build, never batched again later.
- Hand sign-off the list of per-task artifacts, the profile's `playwright_dir` and `ui_flows`, and which sign-off it is (full or light).
- A brief never asks an agent to rebuild just to check that a build is current (§5 Build currency).

## 7. `COST` checks
1. **Heavy commands** — test suites, builds, e2e, audits and browser launches went through `run-heavy.sh`; one browser launch per run covering all its URLs and widths.
2. **Own role only** — the agent ran only the tests and UI checks §1 gives it.
3. **No polling** — no `sleep` loops, `pgrep` waits or waits on another agent's process; queued commands ran in the foreground or as background tasks with a completion notification.
4. **Suite once** — no full-suite run (unit, integration or e2e target) per task or fix round; at sign-off one full run, flaky failures rerun per file.
5. **Cleanup** — every browser, context, tab, `lightpanda serve`, dev server, watcher and emulator started was stopped before reporting.
6. **No audits in a build task** — the developer swept only the screens and states its task changed (plus every renderer of a changed shared component); wider audits were a planned UI design task.
7. **Lightest tool** — API data was read with `curl`/`jq`, rendered DOM or text with `lightpanda fetch` when installed, and a browser launched only for layout or screenshots; no defect was concluded from Lightpanda alone.

## 8. `SWEEP` checks
1. **Full matrix** — every changed web screen (and each layout variant in the UI spec) ran through every `ui_widths` × `ui_themes` combination (light tier: the light sweep of §3) with worst-case content, in one `overflow-check.mjs --sheet` run; no offenders left.
2. **Looked at** — every contact sheet was judged against the UI spec, problems noted by sheet path and cell.
3. **Once per build** — `build-id.txt` sits beside the sheets; no second sweep of an unchanged build; a fix round re-swept only the screens it changed.
4. **Every renderer** — a change to a shared component, style or layout primitive listed every screen and route that renders it (usage search in the notes) and swept each.
