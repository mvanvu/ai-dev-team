# Rule packs and compliance reports

Rules are followed when two things are true: the agent doing the work was handed exactly the rules that apply to its task, and it has to show evidence for each one. This file is the single index of the team's rule packs and the report format every role uses.

## Contents
1. How it works
2. Rule packs
3. `BASE` — rules for every task
4. `TOOL` — greenfield toolchain
5. Assigning packs to tasks (planning)
6. Compliance report (developer)
7. Rule check (reviewer, qc)
8. Leader gates
9. Automated checks

## 1. How it works
- A **rule pack** is a numbered list of checks kept in one reference file. A **rule ID** is the pack ID plus the item number in that list: `COMPACT-3` is item 3 of the checks in `compact-layout.md` §7.
- The leader writes the packs that apply to each task in the `Rules` column of the task board while planning (§5).
- The leader puts those rules into the brief of the developer and of the task's reviewer and qc as a **rule list**: one line per rule ID with its check text, copied from the reference (`COMPACT-3 — <check text>`), plus the must-read file path per pack. Agents work from the rule list and open a reference file only for the part they are applying (§6) — they do not read every must-read file up front.
- The developer reports one row per rule ID with evidence. The reviewer and qc re-check the rules they can observe and report one row per rule ID too.
- The leader accepts a task only when every rule ID is `pass` (or a justified `n-a`) from the developer and, for observable rules, confirmed by the reviewer or qc. Process rules nobody else can observe are **self-attested** (§2): the developer's evidence plus the leader's spot-check.

## 2. Rule packs
Paths are relative to the plugin's `skills/` directory. "Verified by" names the agent that must return a rule check for the pack (`reviewer` or `qc`); other agents may still raise findings against it. **Self-attested** rules describe how the developer worked (tests seen failing, commands used, processes stopped); no other agent can observe them, so they need the developer's evidence and the leader's spot-check of it, and they are excluded from verifier coverage (§8).

| Pack | Applies when the task… | Must read | Numbered checks | Verified by |
|---|---|---|---|---|
| `BASE` | always (implied, not written in the `Rules` column) | this file §3 | §3 | reviewer; `BASE-3`, `BASE-4`, `BASE-5`, `BASE-10`, `BASE-11`, `BASE-13`, `BASE-14`, `BASE-15`, `BASE-17`, `BASE-18`, `BASE-19` self-attested |
| `COST` | always (implied, not written) — how tests, builds and other heavy commands are run | `dev-team/references/resource-budget.md` | §7 | self-attested; qc for its own runs |
| `SWEEP` | builds or changes a web-rendered screen (web app, PWA, Capacitor WebView) — not Flutter or native, which qc covers with widget/golden tests | `dev-team/references/resource-budget.md` | `resource-budget.md` §8 | qc, reviewer (design QA) |
| `TOOL` | scaffolds a new project, app or package | `technical-design/SKILL.md` → Latest-stable toolchain | this file §4 | reviewer |
| `ARCH` | adds or changes web frontend code in a project that uses the headless core-component architecture (profile or plan says so) | `pwa-headless-ui/SKILL.md`, `pwa-headless-ui/references/architecture.md` | `architecture.md` §9 | reviewer |
| `COMPACT` | builds or changes a phone-sized screen (mobile web, PWA, Capacitor, Flutter, native) | `pwa-headless-ui/references/compact-layout.md` | §7 | qc, reviewer |
| `LIST` | builds or changes a paginated resource list or a record picker | `pwa-headless-ui/references/list-page.md` | §9 | reviewer, qc |
| `LIFE` | creates or changes a CRUD entity (active flag, trash, restore, purge, bulk actions) — backend and UI tasks alike | `technical-design/references/record-lifecycle.md` | §10 | reviewer, qc |
| `QUERY` | reads or writes the database for a list, a detail with children, an export, a bulk action, a background job or a GraphQL resolver — or a client screen that loads data per row | `code-review-checklist/references/query-performance.md` | §4 | reviewer, qc |
| `PTR` | builds or changes a phone screen that shows server data in a vertically scrolling list or feed (mobile web, PWA, Capacitor, Flutter, native) | `pwa-headless-ui/references/pull-to-refresh.md` | §8 | qc, reviewer |
| `DESIGN` | is a UI design task (developer in UI design mode: UI spec, mockups, layout options) | `ui-ux-design/references/design-gate.md` | §6 | reviewer (design QA), leader for `DESIGN-6` |
| `REAL` | builds or changes any user-facing screen, template pack or marketing page | `ui-ux-design/references/authentic-design.md` | §5 | reviewer |
| `EASE` | builds, changes or designs any user-facing screen (always together with `REAL`) | `ui-ux-design/references/ease-of-use.md` | §3 | reviewer (design QA), qc for `EASE-5` on the build |
| `CONN` | touches a mobile app or installed PWA that uses online data | `pwa-headless-ui/references/connectivity.md` | §10 | qc |
| `FEEL` | touches navigation, page transitions, gestures, sheets/overlays or long lists | `pwa-headless-ui/references/native-feel.md` | §11 | reviewer, qc |
| `PWA` | touches the manifest, service worker, caching, offline fallback or update flow | `pwa-headless-ui/references/pwa.md` | Checks section | qc |
| `CAP` | touches Capacitor config, plugins or the native shell (always together with `CAPFEEL`) | `pwa-headless-ui/references/capacitor.md` | Checks section | qc |
| `CAPFEEL` | same as `CAP` | `pwa-headless-ui/references/capacitor-native-feel.md` | §10 | qc |
| `ABUSE` | adds or changes a public or unauthenticated endpoint, a list/search/export endpoint, an upload or other endpoint that stores data per call, or an AI/agent feature | `security-review-checklist/references/automated-abuse.md` | sections §2–§9 (`ABUSE-3` = §3) | reviewer |
| `RESEARCH` | is the request research the user asked for before planning (dev-team Phase 2) | `dev-team/references/request-research.md` | §5 | leader |

Requirements that come from the feature itself keep their own IDs and are reported the same way: acceptance criteria (`AC-n` from the spec) and threat-model requirements (`SEC-n` from `$TEAM_WS/02_threat-model.md`).

Used without a task board (a standalone review, QC or frontend task), each agent picks the packs itself from the "Applies when" column.

A check that names a tool or environment the task cannot use (a device, Xcode, an emulator) is reported `n-a` with the reason, never silently dropped.

## 3. `BASE` — rules for every task
1. **Scope** — only the task's files and behavior change; unrelated problems are written in the notes, not fixed.
2. **Contracts** — request/response shapes, types, nullability and error codes match the design exactly; a wrong contract is reported `BLOCKED`, not changed.
3. **Tests first** — each acceptance behavior the task touches has a test that was seen failing before the code existed, or the notes say why a test is impractical and how it was verified instead.
4. **Evidence** — the notes hold the trimmed real output of the final related-test, lint and type-check/build runs.
5. **Heavy commands** — test runs, builds and e2e went through `$TEAM_BIN/run-heavy.sh`; no watcher, dev server, emulator or browser is left running.
6. **Language** — code, comments, specs and notes are in English; comments explain why and never describe bug history.
7. **Commits** — none unless the user asked; messages are English and imperative; AI attribution (a `Co-Authored-By: Claude …` trailer, "Generated with Claude Code") follows the project's policy — its `CLAUDE.md` or `.claude/settings.json` `attribution` first, the user's global instructions otherwise; one commit per task, adding only the task's files and named team files (never `git add -A` or a whole folder), checked with `rule-checks.sh staged-media`.
8. **Dependencies** — no new dependency without a stated reason (maintained, size/cost acceptable, no existing utility does it); a new dependency or version was published at least 14 days before it was added, unless the user approved a newer one — the exact version named in a plan the user approved counts as approved (supply-chain attacks are usually caught within days).
9. **Security defaults** — input validated at the boundary, parameterized queries, an authorization check on every entry point, no secrets in code or logs.
10. **Test scope** — per task and per fix round only the related tests of the changed files and the mapped guards ran (no whole-suite or all-guards runs); failures outside the task are reported as `not mine`, not chased with reruns.
11. **Shared tree** — no `git stash`, `checkout`, `restore`, `reset`, branch switch, or moving / deleting tracked files on the working tree other agents share, except the files a removal task lists in its board row; to show a test failing without the change, copy the file to `$TEAM_WS/` and copy it back, or write the test before the code. This holds in fix rounds and quick passes too.
12. **Other repositories** — nothing was written outside this repository unless the brief names that repository and its files and states the user approved it.
13. **Untracked files and shared environments** — no untracked file or directory was deleted without listing it and getting the user's yes (it cannot be restored from git); before installing, uninstalling or resetting anything on an environment that mounts the repository (a container with the source bind-mounted, a CMS that deletes extension folders on uninstall), `git status` was taken, and taken again after — a tracked file that changed or vanished is restored and reported. Local secrets files (`.env`) change only by named keys, after a backup, and the notes list the keys changed.
14. **Waiting on your own command** — a test or build ran in the foreground through `run-heavy.sh` (it applies a timeout), or, when it may outlast the foreground limit, as a background task: the agent then ends its turn without a waiting loop, is resumed when the command finishes, and sends its report. No `sleep`/`until` loop, Monitor or second background task waits on the first. A command that hangs or times out is reported as hung with the step that was running, not left running.
15. **Own processes only** — the agent stopped only processes it started (by its background-task id or a pid it recorded); never `pkill`, `killall` or `kill` by name or pattern, and never a command that stops shared daemons or stacks (`gradlew --stop`, `flutter daemon` shutdown, `docker compose down` / `stop` / `restart` of a stack others use), which also kills other agents' test runners and builds. A stray process it did not start is reported to the leader.
16. **Reuse first** — before adding a feature, component, service, helper, endpoint, script or fixture, the project's capability index (`$TEAM_STATE/capabilities.md`) and the plan's reuse notes were checked, then a bounded search by name; an existing fit was used or extended. The notes hold a `## Reuse` table: what was needed, where it was looked for, and `reused <path>`, `extended <path>` or `new — <why nothing fit>`; anything new that others can reuse is added to the index.
17. **Shared toolchains and data** — no SDK, toolchain or shared tool was installed or upgraded by the task (a missing or wrong version is reported to the leader, who installs it once); scratch tests and probes that commit data outside a rolled-back transaction (forked processes, a second connection, calls to a running app) removed what they wrote, and the notes show the before/after count.

18. **No sub-agents** — the agent did not start agents of its own (the Agent tool, Workflow); work that would go faster in parallel is reported to the leader, who splits it within the run's caps and models.
19. **Notes from the start** — the task notes file was created when the work began and gained a progress line after each step (read, red test, code, related tests, sweep, each qc flow checked with its result), so a replacement agent continues from it and the watchdog sees progress.
20. **Removal checks every reference** — before deleting code, strings, keys, routes, options or assets, usages were searched including dynamically built names (prefixes such as `LABEL_`, string interpolation, config and template files, other apps of the repo); what is still used stays, and the notes list what was searched.

## 4. `TOOL` — greenfield toolchain
1. Installed versions equal the design's `## Toolchain` table; anything not in the table was looked up at install time, not recalled.
2. No beta, RC, canary or nightly; runtimes on the latest LTS where one exists.
3. Current config formats and official scaffolders; lockfile committed.
4. Any tool held below latest stable has its reason in the notes.

Severity when the reviewer finds a `TOOL` failure: `minor` for a version below the `## Toolchain` table or a legacy setup where a current one exists; `major` for a whole major behind, a pre-release in production dependencies, or an end-of-life runtime (security: `medium`, higher with known CVEs).

## 5. Assigning packs to tasks (planning)
For every task, walk the "Applies when" column and list each matching pack in the task board's `Rules` column (`BASE` and `COST` are implied and not written). Add the task's `AC-n` from the spec and `SEC-n` from the threat model. Assign by what the task touches, not only by its tags — a backend task for a CRUD entity gets `LIFE`, a list endpoint gets `ABUSE` and `QUERY`. When unsure whether a pack applies, assign it: an `n-a` row costs less than a missed rule.

## 6. Compliance report (developer)
Before coding, read the rule list in the brief. Open a pack's reference file only for the section behind a rule the task actually exercises (building a list → `list-page.md`; a phone layout → the `compact-layout.md` sections the screen uses), and skip packs whose rules are all `n-a`. Before reporting `DONE`, add this section to the task notes, one row per rule ID of every assigned pack plus `BASE` and `COST`. A task on a light-tier route (small change, layout complaint — dev-team routing) reports only `BASE-1`, `BASE-2`, `BASE-3`, `BASE-4`, `BASE-9` and its assigned packs:

```markdown
## Rule compliance
| Rule | Status | Evidence |
|---|---|---|
| BASE-1 | pass | diff touches only src/features/orders/** |
| COMPACT-2 | pass | overflow-check.mjs at 360/390: ok — $TEAM_WS/qa-artifacts/T3/orders-sheet.png |
| COMPACT-4 | n-a | screen has no icon rows |
| LIST-3 | pass | OrderPicker.spec.ts "keeps selection across pages" |
```

- Status is `pass`, `n-a` or `fail`.
- `pass` needs evidence someone else can open: a test name, `file:line`, a command with its output, or an artifact path. "Checked" or "done" is not evidence.
- `n-a` needs the reason the rule cannot apply to this task.
- `fail` means the task is not done: fix it, or report `BLOCKED T{id}` with the rule ID and the reason.
- Never mark a rule `pass` without having checked it in this task; an unchecked rule is reported as `fail`.
- A rule listed in §9 is proven by its script: the evidence is the command and its output, nothing else.

## 7. Rule check (reviewer, qc)
Each verifier adds this table to its verdict, covering the rule IDs of the packs it is named for in §2 (and any other rule it happened to check), except self-attested ones:

```markdown
## Rule check T{id}
| Rule | Result | Evidence |
|---|---|---|
| ARCH-1 | pass | lint output in notes; grep of src/features finds no reka-ui import |
| LIST-4 | fail | filter `status` stored in localStorage — src/features/orders/useOrders.ts:41 |
| COMPACT-3 | n-o | needs a rendered page |
```

- Result is `pass`, `fail` or `n-o` (not observable by this agent — say what it would take).
- Check the rule itself, not the developer's claim: open the evidence, then look at the code or the running app.
- A `fail` is also written as a normal finding or defect in the role's own format, with the rule ID in the title; severity follows the agent's checklist (a rule that protects data, access or a contract is at least `major` / `high`).
- A developer `pass` whose evidence does not exist or does not show the rule is a `fail` plus a `major` finding ("unsupported compliance claim").
- A missing `## Rule compliance` section in the notes is a `major` finding; do not review the rest as if it were there.
- **Reviewer: the whole task diff** — the reviewer reads the task's diff itself (the task's commit, or `$TEAM_BIN/rule-checks.sh task-diff T{id} -- <task files>`), not the developer's description of it, and the verdict carries a `## Files read` list: every changed file, `read` or `skipped — <why>` (generated files, lockfiles). Response fields, serializers and log or audit output added by the task are read line by line: that is where data leaks hide.

## 8. Leader gates
- **Brief**: every developer, reviewer and qc brief contains the rule list (§1: one line per rule ID with its check text, plus the must-read path per pack) for the task's `Rules` cell, `BASE` and `COST`, and for each verifier only the rules its role checks (§2), plus "report per `ai-dev-team:dev-team` → `references/rule-packs.md` §6" (developer) or "§7" (verifier). It also carries `TEAM_BIN=<absolute path>` for the team scripts.
- **DONE gate**: the report says nothing is left running; an identical report arriving again means the agent still has background work — tell it to stop everything and stay idle. Open the notes. No `## Rule compliance` section, a missing rule ID, a `pass` without evidence or an `n-a` without a reason → send the task back with the list of missing rows. This does not count as a fix round. Spot-check the self-attested rows: open one piece of evidence for each (the failing-test output, the wrapped command line, the build-id file).
- **Verifiers follow the packs**: every task gets a reviewer; qc too unless it is on a light-tier route. A pack verified only by qc on a light-tier task means that task is not small — give it qc.
- **Verdict gate**: a verdict without a `## Rule check` table for the packs that role verifies → ask that agent for it before accepting the verdict. A review whose `## Files read` list leaves a changed source file unread (or has no list) goes back to the reviewer before it counts.
- **Severity check**: a finding that says the task's feature does not work, or fails silently, in a state a user can reach (a sound that never plays, edits that are dropped or reverted to an old value, a screen that does not show what the server answered, a list that never refreshes, content that overflows or is clipped) is at least `major`; one filed as `minor` goes back to the reviewer (`ai-dev-team:code-review-checklist` → Severity).
- **Coverage**: a task is `done` when every assigned rule ID is `pass` or `n-a` from the developer **and**, except self-attested rules, `pass` from at least one verifier (an accepted `n-a` needs a verifier that does not contradict it). Rule IDs every verifier marked `n-o` are listed as `unverified` in the task board notes and in the Phase 6 report.
- **Ledger**: append every verifier `fail` to `$TEAM_WS/rule-violations.md` — a table with the header `| Task | Rule | Found by | Fixed in round |`, one row per fail; the Rule cell is always one rule ID (`COMPACT-5`, `AC-7`, `SEC-12`), never a description — a defect that maps to no rule goes to the notes, not the ledger, and a rule pack that should have caught it is a candidate for a new check.
- **Recurring defect classes**: the same kind of defect found in two or more tasks without a rule ID (a held write lost when the app goes to the background, a failed reload that leaves a silent stale screen) gets a one-line warning in every later brief, like a rule that failed twice, and is listed in the Phase 6 report as a proposed new check for the pack it belongs to. A rule that fails in two tasks goes into the brief of every later task as a one-line warning, and into the Phase 6 report.

## 9. Automated checks
Rules a script can decide are decided by the script, not by reading. The scripts live in the plugin at `$TEAM_BIN` (the brief gives the absolute path) and run with the project root as the working directory. Each prints `<RULE-ID> ok`, `<RULE-ID> n-a: <reason>` or one line per violation, and exits 1 on violations.

| Rule | Command | Run by |
|---|---|---|
| `ARCH-1` | `$TEAM_BIN/rule-checks.sh arch` — hits are candidates; confirm each | developer, reviewer |
| `LIST-4` (list state in web storage) | `$TEAM_BIN/rule-checks.sh list-storage` — hits are candidates; confirm each | developer, reviewer |
| `BASE-7` | `$TEAM_BIN/rule-checks.sh commits [base]` — only when commits were made | developer, reviewer |
| `TOOL-2` | `$TEAM_BIN/rule-checks.sh prerelease` — hits are candidates; confirm each | developer, reviewer |
| `COMPACT-1`, `COMPACT-2`, `COMPACT-7`, `COMPACT-9`, `SWEEP-1` | `$TEAM_BIN/run-heavy.sh node $TEAM_BIN/overflow-check.mjs --widths <ui_widths> --themes <ui_themes> --touch 44 --shots $TEAM_WS/qa-artifacts/T{id} --sheet [--init <ui_seed>] <url>...` on the screens and states the task changed, loaded with worst-case content (`resource-budget.md` §3) | developer (when the app can run), qc |
| `COMPACT-6` (Flutter) | `$TEAM_BIN/rule-checks.sh flutter-overflow <saved flutter test output>` | developer, qc |
| `REAL-2`, `REAL-4` | `$TEAM_BIN/rule-checks.sh ai-look` — hits are candidates (seed data in fixtures, a brief that asks for gradient text); confirm each | developer, reviewer |
| `SWEEP-3` (build id) | `$TEAM_BIN/rule-checks.sh build-id` — same tree, same id | developer, qc |
| — (stray team files) | `$TEAM_BIN/rule-checks.sh stray-team-files` — team or third-party skill files outside `.ai-dev-team/` (`.superpowers/`, `_workspace*/`, `.claude/team/`, mockup code in the source tree); Phase 0 of every run and before a commit | leader |
| — (task diff) | `$TEAM_BIN/rule-checks.sh task-base T{id}` when the task starts (no commit per task); `task-diff T{id} [--stat] -- <task files>` for its diff | leader; reviewer |
| `BASE-7` (team media) | `$TEAM_BIN/rule-checks.sh staged-media` before a commit with team files; `tracked-media` (`--fix` untracks) in Phase 0 | leader |
| — (environment) | `$TEAM_BIN/rule-checks.sh env-drift` — keys missing from `.env` against the example file; names only, never values | leader (Phase 0), developer of an `env` task |

`$TEAM_BIN/rule-checks.sh all [base]` runs every check except `flutter-overflow`. A script that cannot run here (exit 2 from `overflow-check.mjs`: Playwright not installed) leaves the rule to the manual check in its reference file; say so in the evidence.
