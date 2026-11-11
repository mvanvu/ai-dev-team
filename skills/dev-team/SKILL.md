---
name: dev-team
description: "Orchestrates the AI software team — developer, reviewer, qc — through profile → spec → plan → build/review/QC → final review, with planning done by the leader (superpowers brainstorming and writing-plans when installed). Use for building features, fixing bugs, refactors, new web/mobile screens, PWA/Capacitor/Flutter apps, UI templates, or full reviews: 'build feature X', 'implement', 'add a screen', 'make it a PWA', 'build a mobile app', 'add a new template', 'fix this bug', 'review this branch', 'security review', 'start a new project'. Also for follow-ups: continue, resume, re-run, revise, 'only redo the design'. Skip for simple questions or one-line edits."
---

# Dev Team orchestrator

The main session is the **leader**. It profiles the repo, plans with the user, owns the task board, briefs the agents, merges their feedback and talks to the user (in the user's language). It never writes production code itself. All files the team writes are in English.

## Team

| Agent (`subagent_type`) | Model | Skills | Modes | Output |
|---|---|---|---|---|
| `developer` | opus (sonnet / fable per Model per role) | implementation; pwa-headless-ui and ui-ux-design for client tasks and UI design | implement (server or client task, per `Owner`), UI design, fix, bug | code + tests, `$TEAM_WS/04_dev_T{id}.md`, `$TEAM_WS/02_ui-spec.md` |
| `reviewer` | opus (sonnet for other-than-high-risk task reviews) | code-review-checklist; security-review-checklist; ui-ux-design (design QA) | review (code + security + design QA in one pass), threat model, final-review dimension, verify, full audit | verdicts, `$TEAM_WS/02_threat-model.md` |
| `qc` | sonnet | qa-verification | QC per task, sign-off | `$TEAM_WS/05_qc_report.md`, `$TEAM_WS/qa-artifacts/` |

The leader itself uses `project-profiling` (Phase 1), and for planning `superpowers:brainstorming` + `superpowers:writing-plans` when the `superpowers` plugin is installed in this session — otherwise `spec-writing` + `technical-design`. `technical-design` also holds the task-board format, default stack, toolchain and sizing rules the plan must meet either way.

The board's `Owner` column says which side a task is: `be` (server) or `fe` (client); the brief names it and loads only that side's skills. A task never mixes server and client code; server tasks are built, reviewed and QC'd before the client tasks that consume their contracts.

### Agent and skill names
Installed as the `ai-dev-team` plugin, agents and skills carry the `ai-dev-team:` prefix: `subagent_type: "ai-dev-team:developer"`, skills `ai-dev-team:<skill>`. If the agent list shows un-prefixed names (files copied into a project's `.claude/`), use those and pass `agentPrefix: ''` to the Phase 5 workflow.

## Routing by request type

| Request | Phases |
|---|---|
| **Small change** — a few files, no contract/schema/public-API change, no new screen ("quick fix", typo-level bug, small tweak) | 0 → 1 if no profile → one-row board → 4 (**light tier**: developer, then one reviewer; qc only when a criterion needs runtime proof) → 6 |
| Layout complaint on an existing screen (wasted space, broken or cramped layout) | 0 → 1 → `developer` in **UI design** mode (pack `DESIGN`) writes a short `$TEAM_WS/02_ui-spec.md` delta with the options in one HTML: the complaint with the sweep cells that show it, 1–3 layout options, and every conflict between rules (density vs touch-target size, truncation vs wrapping) → leader asks the user to pick when options differ in behavior → 4 (**light tier**; the reviewer's design QA on the sheets replaces qc) → 6 |
| Bug (non-trivial) | 0 → 1 → 2 (bug spec: repro, expected, `AC-n`) → 3 (board only, usually one or two rows) → 4 (the developer reproduces first on the side where the bug shows; a bug that needs server and client changes becomes a server row, then a client row) → 6; add 5 if the fix touches security |
| New feature / screen | 0 → 1 → 2 → 3 → 4 → 5 → 6 |
| New project (greenfield) | 0 → 1 → 2 → 3 (stack proposal, **user approves**) → 4 (scaffold task first, then **rerun 1** to profile the new commands, then the rest) → 5 → 6 |
| Review only ("review this branch", "security review", "audit") | 0 → 1 → 5 (`mode: 'review-only'`) → 6 |
| UI design only | 0 → 1 → 2 → 3 (developer in UI design mode only) → 6 |
| New template / theme pack | 0 → 1 → 2 (short) → 3 (developer UI design: tokens + recipes) → 4 (no core component edits) → 6 |
| PWA / Capacitor setup, mobile app | 0 → 1 → 2 → **mobile platform choice** → 3 → 4 → 5 (include `security`) → 6 |
| Continue / resume / follow-up | Phase 0 decides |

**Light tier** (small change, layout complaint): developer + one reviewer, no qc unless a criterion needs runtime proof; light sweep (`references/resource-budget.md` §3); compliance table limited per `references/rule-packs.md` §6; no Phase 5. It never applies to a task that touches auth, permissions, payments, data deletion or a schema — those take the normal route.

When unsure whether a change is small, treat it as a bug route; when a "small change" grows past its limits during work, upgrade it to the bug route.

## Resource budget
The budget lives in the project profile (`max_agents`, `heavy_workers`, the `run-heavy` wrapper, `ui_widths`, `ui_themes` — written in Phase 1):
- **Max concurrent agents: `max_agents` (default 4)**, counting every background and Workflow agent, not the leader. When the cap is reached, queue the next spawn. Priority: fix rounds, then review/QC of in-flight tasks, then light-tier tasks the user added during the run (a small change asked mid-build runs as soon as the current task is done, ahead of planned tasks), then other new tasks. Tell the user where a new task sits in the queue and roughly when it starts.
- Heavy commands (suites, builds, e2e, audits, browser launches) go through `$TEAM_BIN/run-heavy.sh`; it serializes them across agents, so the leader does not need to schedule browser or test work by hand. The scripts are never copied into the project (`ai-dev-team:project-profiling` step 7).
- `COST` applies to every task and `SWEEP` to every task that changes a web screen — `references/resource-budget.md`: each check runs once by the agent that owns it, full width × theme sweep in one run per build, no `sleep`/`pgrep` polling, one sign-off qc with one full-suite run. A brief never raises these limits unless the user asked — and then the user hears the cost first.

## Rule compliance
Every task carries its rules explicitly — procedure and formats in `references/rule-packs.md`:
- The task board's `Rules` column lists the packs per task (`BASE` and `COST` implied); a rule ID is pack + item number (`COMPACT-3`), plus the task's `AC-n` and `SEC-n`.
- **Brief**: every developer, reviewer and qc brief follows the **Brief skeleton** below, including the rule list — one line per rule ID with its check text and the must-read path per pack (§1). Agents open the reference files only for the rules the task exercises. Never brief with "follow the skill" alone.
- **DONE gate**: the notes hold a `## Rule compliance` table, one row per rule ID with evidence; spot-check self-attested rows. Missing rows → send back (not a fix round).
- **Verdict gate**: reviewer and qc verdicts carry a `## Rule check T{id}` table.
- **Coverage**: `done` when every observable rule ID has a verifier `pass`; rules nobody could observe are reported `unverified`.
- **Ledger**: verifier `fail`s go to `$TEAM_WS/rule-violations.md`; a rule that fails in two tasks becomes a warning line in every later brief.

## Brief skeleton
Every agent brief follows this order — fill each line, write `none` rather than dropping one:
1. `TEAM_BIN=… TEAM_STATE=… TEAM_WS=… TEAM_TOOLS=…` and `PLAYWRIGHT_DIR=…` when a browser is used.
2. `Task T{id} — <title>`; mode (implement / UI design / fix / quick pass / review / QC / sign-off); side `be` or `fe`; the model it was spawned on (Model per role).
3. **Skills to load** by name (`ai-dev-team:implementation`, `ai-dev-team:pwa-headless-ui`, `ai-dev-team:ui-ux-design`, `ui-ux-pro-max` when installed, …); the notes list the skills called.
4. The task's board row.
5. **Rule list**: one line per rule ID with its check text — the task's packs plus `BASE` and `COST` for a developer, only the rules the role verifies for a reviewer or qc (`references/rule-packs.md` §1).
6. **Scope**: the files; for UI work the states to sweep, every renderer of a changed shared component (`SWEEP-4`), `ui_seed`, `ui_flows`, the approved mockup path in `mockup_dir`.
7. **Inputs**: the spec / plan / UI-spec / threat-model sections, the notes of tasks it depends on, ledger warnings.
8. **Commands** from the profile (related tests, mapped guards, type-check, build — wrapped where heavy).
9. **Report** format (`references/rule-packs.md` §6 developer, §7 verifier) and the `DONE` / `BLOCKED` / verdict line.

## Phase 0 — Context check
1. **Paths** — the team writes nothing into the project repo; resolve these once per session (`references/team-paths.md`) and put their absolute values in every brief: `TEAM_BIN` (plugin scripts), `TEAM_STATE` (this project's state outside the repo), `TEAM_WS` (`$TEAM_STATE/workspace`), `TEAM_TOOLS` (shared QA tools). Files left in the repo by older versions are moved out first (`team-paths.md` §3).
2. `$TEAM_STATE/project-profile.md` missing, older than ~30 days, or the stack changed → Phase 1; else skip it. Compare the profile with the current `ai-dev-team:project-profiling` template: every missing field (budget fields, `ui_seed`, `ui_flows`, `playwright_dir`, `mockup_dir`, …) is filled in by the step of that skill that defines it, before any brief. Commands that hold a versioned plugin path (`…/ai-dev-team/<version>/skills/project-profiling/references/…`) are rewritten to the literal `$TEAM_BIN/…`.
3. `$TEAM_WS/`:
   - absent → fresh run.
   - present with unfinished tasks on the board (`in progress`, `review`, `fix`) and the user says continue/resume, or asks something that fits the same feature → **resume** (below).
   - present, all tasks `done`, and the request is new → move it to `$TEAM_STATE/workspace_<YYYYMMDD-HHMM>/` and start fresh. If unfinished tasks remain and the request is unrelated, ask the user before archiving them.
   - a follow-up on finished work ("only redo the design", "improve X") → rerun only the affected phase or task.
4. **Resume**: read the task board's Status and Rounds columns. For each unfinished task read `$TEAM_WS/04_dev_T{id}.md` and `git diff`, then brief a fresh developer with "continue T{id} from these notes" (or a fresh reviewer/qc for a pending verdict). Round counts come from the board, never restart at zero. A previous Phase 5 `runId` in `$TEAM_WS/run_meta.json` → resume it with `resumeFromRunId`.

## Phase 1 — Profile (leader)
Follow `ai-dev-team:project-profiling`: detect the stack, verify the commands, record conventions, UI presence and the budget. The profile goes to `$TEAM_STATE/project-profile.md`; nothing is written into the repo. Run long verification commands in the background through the wrapper and keep only trimmed output in context. A greenfield repo still gets the budget; its commands are profiled again right after the scaffold task.

## Phase 2 — Spec (leader with the user)
1. **With superpowers**: run `superpowers:brainstorming` with the user's request (it explores context, asks one question at a time, gets approval and saves the spec — tell it to save to `$TEAM_WS/01_spec.md`, its mockups and visual-companion files to `$TEAM_WS/mockups/` (never `.superpowers/` in the repo), and not to commit, since the team writes nothing into the repo). **Without**: write the spec with `ai-dev-team:spec-writing` and ask open questions with AskUserQuestion (max 4 at a time, proposed defaults first).
2. Make sure the spec — wherever it was saved — has the header fields of `ai-dev-team:spec-writing`: `has_ui`, `security_sensitive`, acceptance criteria numbered `AC-1…`, open questions resolved. Copy or link it as `$TEAM_WS/01_spec.md`.
3. Product decisions stay with the user: entity lifecycle (`ai-dev-team:technical-design` → `references/record-lifecycle.md`), public-API changes, data deletion, AI-crawler policy — ask with a proposed default.
   **Access trade-offs too**: anything that lets data stay reachable after access is removed (cache lifetime of signed or public URLs after revoke, trash or deactivate; tokens or sessions valid after logout; stale permissions) or weakens privacy is never accepted by the leader or a reviewer. Present it to the user with the exposure window and the alternatives, and record the answer in the spec. This holds when it first shows up as a reviewer finding during the build.
4. **Mobile platform choice.** When the request needs an iOS/Android app and the profile has `mobile_platform: none`, ask with one AskUserQuestion (header `Mobile`): `Flutter (Recommended)` — one Dart codebase, native performance; `Capacitor (wrap the PWA)` — fastest, WebView limits; `Native apps` — Swift/SwiftUI + Kotlin/Compose, two codebases, highest cost. Same when a developer returns `needs-user-decision: mobile platform`. Details: `ai-dev-team:pwa-headless-ui` → `references/mobile-options.md`.

## Phase 3 — Plan (leader + agents in parallel)
1. Spawn in one message, when the spec calls for them:
   - `has_ui` → `developer` in **UI design** mode → `$TEAM_WS/02_ui-spec.md` and the mockup HTML, pack `DESIGN` (`ai-dev-team:ui-ux-design` → `references/design-gate.md`). For a new product, template or app, confirm the screen inventory with the user before the mockups are drawn. Mockups come in two stages (`design-gate.md` §3): stage 1 — three representative pages per option; design QA by a fresh `reviewer` on `sonnet`, open the passing HTML for the user (`xdg-open` / `open`, with its path), ask which option to build; stage 2 — the chosen option with every inventory page and preset, design QA again. No build task of that UI starts before stage 2 passes.
   - `security_sensitive` → `reviewer` in **threat model** mode → `$TEAM_WS/02_threat-model.md` with `SEC-n`.
2. Meanwhile write the plan: **with superpowers** `superpowers:writing-plans`, saved to `$TEAM_WS/02_plan.md`, no commit (stop when it offers an execution mode — the build loop below executes the plan; do not hand over to `subagent-driven-development` or `executing-plans`); **without**, `ai-dev-team:technical-design`. Either way the plan meets `technical-design`: contracts between modules, decisions with reasons, default stack and latest-stable toolchain for greenfield, 3–8 tasks sized for throughput.
3. When the UI spec and threat model are back, write `$TEAM_WS/02_tasks.md` in the task-board format of `ai-dev-team:technical-design` (ID, title, owner `be`/`fe`, depends, files, tags `ui`/`pwa`/`mobile`/`security`, `Rules` per `references/rule-packs.md` §5 incl. `AC-n`/`SEC-n`, verify command, Status, Rounds). Contradictions between spec, UI spec and threat model go to the user.

**User gate:** show a short plan summary (task count, key decisions, risks), and, when no earlier question set it, the Fable policy in the same AskUserQuestion (Phase 4, Model per role). Wait for approval when: greenfield, data migration, public API change, or > 8 tasks. Otherwise proceed and say the user can stop you.
A reply that changes scope is not approval: update the spec and board, show the user only what changed, and wait again whenever the gate applies. A scope change while tasks are running: tell the affected agents to stop at a safe point, update the spec, confirm the new scope with the user, then send the revision — one revision per confirmed change, not one per message.

## Phase 4 — Build loop
Topology is **hub-and-spoke**: agents talk only to the leader. Handover lives in files (task notes, the board, the rulings ledger), never only in an agent's memory. Each agent's first message lists its tools — one missing a tool it needs is restarted or that step is done by the leader.

For each task in dependency order (update Status and Rounds on the board as you go):
1. **Build** → a fresh `developer`, told the task's side (`Owner`): "Implement T{id}" + task row, rule list, the relevant spec / plan / UI-spec / threat-model sections, notes of tasks it depends on, ledger warnings. Wait for `DONE` / `BLOCKED`, apply the DONE gate.
   Every new task gets a new developer, even when an earlier developer "knows the code": hand over through that task's notes. Only fix rounds of the same task go back to the same developer. The same holds for verifiers: every task gets its own reviewer and qc; a new task's review or QC is never sent to an agent that verified another task.
   **Fill the slots**: whenever a task starts or reaches `done`, walk the board and start every task that is ready — dependencies `done`, files disjoint from the running tasks, no shared built output, no shared test data or environment in use (a task that seeds, resets, migrates or deletes data on the demo / test database or site never runs while a qc or browser check is using that environment) — until `max_agents` agents are running (verifiers included). A ready task left waiting gets the reason in the board notes. Serial work by habit wastes the budget the profile allows.
   Tasks run concurrently, one developer each within `max_agents`, only when **isolated**: no dependency, no overlap in their files (shared components, styles, language files, tests, build config included), no shared built output, and no shared data or environment that one of them changes while the other checks it. Before starting two tasks together, compare their `files` cells on the board and write `parallel: T2 ∥ T3 — files disjoint` in the board notes; any shared path, or a task still in review or fix on files the new one touches, means they run one after the other. Two tasks of one app (frontend or backend) that touch the same module, entity or test directory are not isolated — run them in sequence, or each in its own git worktree (`isolation: "worktree"`, merged back by the leader).
2. **Verify in parallel** — one message: a fresh `reviewer` (model per **Model per role** below; "Review T{id}": code + security + design QA as the task's tags and packs require) and a fresh `qc` ("QC T{id}"; skipped on light-tier routes unless a criterion needs runtime proof). Brief each with the task row, the sections it needs, the task notes, and the packs it verifies with their must-read files. Reviewers do not run suites; qc does not rerun the developer's tests.
3. **Fix**: only blocker/major/critical/high findings, `QC_FAIL` defects and rule-check `fail`s open a fix round. Wait for both the reviewer and qc verdicts, then merge everything into **one** fix request to the same developer (`SendMessage`; a fresh one with the notes if it is gone) — round 1 carries every such issue from both verifiers, so later rounds are only for what the re-checks still find. Minor/low findings ride along in a round that is opening anyway. When none opens and they are still to be fixed (the project's own rules may require fixing every finding), they get one **quick pass**: the same developer if it is still alive, or a fresh one on `sonnet` with only those findings and the files; no sweep beyond the states the fix touches, related tests only, re-checked by the reviewer on the diff alone, no qc. A quick pass is not counted as a round. Otherwise they go to the Phase 6 report. Re-verification goes only to the agents that raised issues, via `SendMessage`. Increment Rounds; **max 3**. Still failing after round 3 → **escalation**: one fresh `developer` — on `fable` when the run's Fable policy allows it (`auto`, or `ask` and the user said yes), otherwise on the proposed model — briefed from the notes and all rounds' findings, to find the root cause and fix it; its review and QC follow as usual. Still failing → mark `blocked` and tell the user.
   Before opening a round on a finding about another task's files, or one from a run that started before that task's last round, check it against the current tree (one file run or a `git diff` look); a finding the tree no longer shows is closed, not sent. A finding the reviewer calls an "accepted trade-off" that falls under the Phase 2 access trade-offs goes to the user, not into the spec as accepted.
   `QC_BLOCKED` (environment, missing service, browser needs the user): fix the environment or ask the user; the task is never `done` while qc is blocked.
4. **Done** when coverage holds; record `unverified` rule IDs on the board and this task's `fail`s in the ledger. Retire the task's agents.

**Model per role** — the agent file sets the default; the leader passes `model` on the spawn where this table differs. High-risk task: tagged `security`; carries `ABUSE`, `LIFE`, `QUERY` or `SEC-n`; touches auth, permissions, payments, data deletion, schema or migrations, concurrency (locks, races, queues) or money/quantity calculations.

| Work | Model |
|---|---|
| developer — normal task, UI design mode | opus (default) |
| developer — light-tier task (small change, layout complaint), template / theme pack, site template or theme for a CMS or app (layout, styles, tokens — no business logic, data or security code) | `sonnet` |
| developer or reviewer — Fable cases below, per the run's Fable policy | `fable` |
| reviewer — high-risk task, threat model, full audit, Phase 5 dimensions and verifiers | opus (default) |
| reviewer — any other task review | `sonnet`; an `uncertain` on a correctness question → one opus re-check of that question only |
| qc — per task and sign-off | sonnet (default) |

Haiku is not used: every role judges code, screenshots or rules.

**Project agents**: when the project ships its own implementer agents for an area (`.claude/agents/`, e.g. a backend agent that knows its framework rules), the leader may build that area's tasks with them instead of `developer`, on the model their file sets unless this table needs higher. The same Brief skeleton, rule list, notes file, `## Rule compliance` table, reviews, qc and gates apply; the brief names the plugin's report format, since the project agent does not know it.

**Fable only by the user's policy** — it costs twice Opus and its turns are slower, so the leader never chooses it on its own. The cases where it fits:
1. A task still fails after 3 fix rounds (escalation, step 3).
2. A bug that is hard to reproduce: intermittent, a race, or only on a real environment.
3. A task that is high-risk **and** complex: spans several modules, involves concurrency or money, or migrates a lot of data.
4. A full security audit; the plan of a greenfield project or of a feature with 8 or more tasks.

**Fable policy, set once per run while the user is present.** AskUserQuestion blocks the session until the user answers, so the leader never waits on a Fable question mid-build. Instead it asks for a policy once, in the first AskUserQuestion it makes anyway (Phase 2 questions or the plan gate), header `Model`, listing the tasks that already meet case 3 or 4 and the cost:
- `Use Fable automatically, report it` — every case above runs on Fable without asking; each use is reported.
- `Ask each time` — the leader asks when a case arises; that task waits for the answer (a user away from the machine holds it up).
- `Never use Fable` — the proposed model runs in every case.

Write the answer in the board notes (`fable-policy: auto | ask | never (user, <time>)`); a resume keeps it, and it lasts until this run's workspace is archived. Routes that ask the user nothing (light tier) use `ask`. The policy covers only the four cases — every other spawn keeps its model from the table. The user can change it at any time ("stop using Fable", "use Fable from now on"): update the note, applied from the next spawn; agents already running finish on their model. Under `ask`, the options per case are `Use Fable` and `Keep <proposed model>`. The Phase 6 report lists every agent that ran on Fable: task, role, case and why.

**Progress to the user** (in their language, short): when a task starts or reaches `done`, one board line — `done 6/9 · running M2, T3 · waiting: sign-off · next: Phase 5`; when a task has run about 10 minutes without news, one line on what it is doing, what comes next and a rough time left from similar measured tasks. Waiting tasks are named with their reason (dependency, queue, user decision), so the user never has to ask what is left.

Replace any agent early when its context passes ~500k tokens: ask it to write its notes first, then brief the replacement from them.

**Test cost** (put in every developer brief): per task only the related tests of the changed files + mapped guards, type-check, build once at the end; per fix round only that round's files; a failure in a test the task did not touch → rerun that file once, then report it `not mine`. The full suite runs once at sign-off, or earlier only when a change touches shared infrastructure. When the profile records `tests: none`, say so in the brief: evidence is the reproduction steps and command output the task criteria need; the plan should contain a task that adds a test runner when the user agrees.

After the last task is confirmed: **one** `qc` in sign-off mode — full, or light when the run had only light-tier tasks (`references/resource-budget.md` §5). Phase 5 starts only after sign-off passed — never in parallel with it, since sign-off can still send work back.

## Phase 5 — Final review (Workflow)
On feature, greenfield and mobile routes it runs only when the board has **4 or more tasks**, any task is tagged `security`, or the spec is `security_sensitive` — per-task reviews cannot see how many tasks interact, but with 1–3 ordinary tasks the per-task reviews cover it. Skipped → say so in the Phase 6 report. The review-only route always runs it. Build `args.dimensions`: always `correctness`; `security` if `security_sensitive` or any `security` task; `ui` if `has_ui`. Pass `args.scope` (file list or `git diff` range), `args.mode` (`'feature'`, or `'review-only'` on the review-only route), `args.specPath` / `args.designPath` when they exist, `args.agentPrefix` (`'ai-dev-team:'` by default) and `args.maxAgents` (the profile's `max_agents`). Call Workflow with `scriptPath` = the absolute path of `references/final-review.workflow.js` in this skill's directory (or Read it and pass it as `script`). Every dimension and verifier is a `reviewer` agent; in feature mode the reviewers focus on cross-task interactions, since per-task review already covered each task. The result is `{ confirmed, uncertain, minor, missingDimensions }`.

Write the `runId` to `$TEAM_WS/run_meta.json`; wait for the completion notification, never predict results. `confirmed` → back to Phase 4 as a fix round, then resume only the affected dimension. Re-verification after these fixes is qc's (one `qc`, not the leader): the related tests of the fixed files and a sweep of the states they touch; the full suite again only when the fixes touched shared code (shared modules, schema, build config). The leader never runs suites or builds itself. `uncertain` → list for the user. Save the result to `$TEAM_WS/06_final_review.json`.

## Phase 6 — Report (to the user, in their language)
What was built, files changed, test/QC results with real numbers, review outcome (confirmed fixed / uncertain / minor), rule compliance (`unverified` IDs, rules that failed in two or more tasks), anything skipped or blocked and why. No commits unless the user asks; messages English, imperative, no AI attribution.

## Data passing
- Files in `$TEAM_WS/`: `01_spec.md`, `02_plan.md` (or a link to the superpowers plan), `02_ui-spec.md`, `02_threat-model.md`, `02_tasks.md`, `04_dev_T{id}.md`, `05_qc_report.md`, `qa-artifacts/`, `rule-violations.md`, `06_final_review.json`. Final deliverables are the code in the repo.
- Messages carry verdicts and short summaries; details live in files.

## Error handling
| Situation | Action |
|---|---|
| Agent fails once | Retry once with the same input. Fails again → continue without it and record the gap in the report. |
| Usage limit, auth expired, permission denied | Do not retry. Write `$TEAM_WS/gaps.md`, keep the board's Status/Rounds current, report to the user (with the reset time if known); the next "continue" resumes from Phase 0. |
| Agent unresponsive | `SendMessage` a status ping and re-send the instruction. Still stuck → a fresh agent of the same type briefed from the notes. |
| `QC_BLOCKED` | Fix the environment if the leader can (start a service the profile names), else ask the user; never mark the task `done`. |
| Repo has no tests / lint / type-check | Profile records `tests: none` etc.; rules that need them are `n-a` with that reason; offer the user a task that adds them. |
| Workflow agent returned null | Report missing dimensions; resume with `resumeFromRunId`. |
| Conflicting findings | Keep both with sources; ask the user only if it changes behavior. |
| 3 fix rounds exhausted | One escalation developer — on `fable` per the run's Fable policy (Phase 4 step 3). Still failing → mark `blocked`, stop dependent tasks, report with the root-cause analysis. |

## Test scenarios
Expected normal and error flows: `references/test-scenarios.md` (read when changing or evaluating this skill).
