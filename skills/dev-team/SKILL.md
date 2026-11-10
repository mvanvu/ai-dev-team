---
name: dev-team
description: "Orchestrates the AI software team (repo-scout, architect, ui-ux-designer, developer, pwa-frontend-engineer, code-reviewer, security-auditor, qa-engineer) through spec → design → build/review/QA → final review. Use for building features, fixing non-trivial bugs, refactors, new web/mobile screens, PWA/Capacitor apps, UI templates, or full reviews: 'build feature X', 'implement', 'add a screen', 'make it a PWA', 'build a mobile app', 'add a new template', 'fix this bug', 'review this branch', 'security review', 'start a new project'. Also use for follow-ups: re-run, update, revise, continue, 'only redo the design', 'improve previous result'. Skip for simple questions or one-line edits."
---

# Dev Team orchestrator

The main session is the **leader**. It never writes production code itself; it routes work, owns the task board, relays feedback between agents, and talks to the user (in the user's language). All files the team writes are in English.

## Execution mode: mixed

| Phase | Mode | Why |
|---|---|---|
| 0 Context check | leader | — |
| 1 Profile | subagent | one-shot fact gathering |
| 2 Spec | architect (spec mode) | leader handles user Q&A; the same architect continues into design |
| 3 Design | subagents in parallel | architect, designer, security are independent given the spec |
| 4 Build loop | per-task agents, capped by the resource budget | an implementer keeps context across one task's review/QA rounds, then is replaced |
| 5 Final review | workflow | fixed fan-out over dimensions + adversarial verification |
| 6 Report | leader | — |

Invoking this skill counts as consent for the Phase 5 Workflow. Keep it small by default (≤ 3 review agents + verifiers); scale up only when the user asks for a "thorough" / "full" review.

## Team

| Agent (`subagent_type`) | Model | Skill | Output |
|---|---|---|---|
| `repo-scout` | sonnet | project-profiling | `.claude/team/project-profile.md` |
| `architect` | opus | spec-writing + technical-design | `_workspace/01_architect_spec.md`, `02_architect_design.md`, `02_architect_tasks.md` |
| `ui-ux-designer` | opus | ui-ux-design | `_workspace/02_designer_ui-spec.md` |
| `security-auditor` | opus | security-review-checklist | `_workspace/02_security_threat-model.md`, review verdicts |
| `developer` | opus | implementation | backend / non-UI code + `_workspace/04_developer_T{id}.md` |
| `pwa-frontend-engineer` | opus | pwa-headless-ui (+ implementation) | frontend code (Vue 3 / React TS, core components, templates, PWA) and mobile app (Flutter / Capacitor / native) + `_workspace/04_pwa_T{id}.md` |
| `code-reviewer` | opus | code-review-checklist | review verdicts |
| `qa-engineer` | sonnet | qa-verification | `_workspace/05_qa_report.md` |

### Agent and skill names
This team ships as the `ai-dev-team` plugin, so Claude Code exposes every agent and skill with the `ai-dev-team:` prefix: call agents as `subagent_type: "ai-dev-team:<agent>"` (e.g. `ai-dev-team:developer`) and skills as `ai-dev-team:<skill>`. The tables use short names for readability. If the agent list shows the un-prefixed names (files copied into a project's `.claude/` instead of installed as a plugin), use those and pass `agentPrefix: ''` to the Phase 5 workflow.

## Resource budget
Agents run remotely and cost almost no local CPU; the commands they run (tests, builds, e2e, audits, dev servers, browsers) do. Uncapped, several agents each start a test runner that defaults to one worker per CPU thread, and the machine stalls. The budget lives in the project profile (`max_agents`, `heavy_workers`, `run-heavy` wrapper — written by `repo-scout`):
- **Max concurrent agents: `max_agents` (default 4)**, counting every background agent and Workflow agent, not the leader. When the cap is reached, queue the next spawn until one finishes. Priority: fix rounds and QA/review of in-flight tasks before starting a new task — finishing work beats starting work.
- **Heavy commands go through `.claude/team/run-heavy.sh`**: one heavy command at a time on the machine, at low CPU priority, with runners capped at `heavy_workers` workers. Put this rule in every implementer, reviewer and QA brief. If the wrapper is missing, rerun Phase 1.
- **One agent with browser work at a time.** Browser runs (Playwright, Chromium, WebKit, e2e) are heavy commands too; a second agent that needs a browser waits while browser-free agents keep running.
- **Tests and browser checks per role, screenshots, waiting and sign-off** follow the `COST` pack (`references/resource-budget.md`): each check runs once by the role that owns it, every changed screen swept at every width tier × every theme in one `overflow-check.mjs --sheet` run per build (never one script or launch per screen), no `sleep`/`pgrep` polling, one sign-off QA agent with one full-suite run. A brief never raises these limits unless the user asked — and then the user hears the cost first.
- Light commands (a single test file, type-check of one package, `git diff`, lint of changed files) may run directly.
- Agents stop the dev servers, watchers and emulators they started before reporting.

## Rule compliance
Agents break rules they were never handed or never had to prove. So every task carries its rules explicitly — full procedure and formats in `references/rule-packs.md`:
- The task board's `Rules` column (filled by the architect) lists the rule packs for each task; `BASE` and `COST` apply to all. A pack is a numbered checklist in one reference file, and a rule ID is pack + item number (`COMPACT-3`).
- **Brief**: every implementer, reviewer and QA brief includes the task's rule packs and their must-read files, resolved from `references/rule-packs.md` §2. Never brief an agent with "follow the skill" alone.
- **DONE gate**: accept `DONE` only when the task notes hold a `## Rule compliance` table with one row per rule ID — `pass` with openable evidence or `n-a` with a reason. Otherwise return it with the missing rows (not a fix round).
- **Verdict gate**: every review, design-QA and QA verdict carries a `## Rule check T{id}` table for the packs that role verifies; ask for it when missing.
- **Coverage**: a task is `done` only when each rule ID is confirmed `pass` by at least one verifier; rules nobody could observe are reported as `unverified`.
- **Ledger**: verifier `fail`s go to `_workspace/rule-violations.md`; a rule that fails in two tasks is added as a warning line to every later brief.

## Routing by request type

| Request | Phases |
|---|---|
| New feature / screen | 0 → 1 → 2 → 3 → 4 → 5 → 6 |
| New project (greenfield) | 0 → 1 → 2 → 3 (architect proposes stack, **user approves**) → 4 → 5 → 6 |
| Non-trivial bug | 0 → 1 → 2 (bug spec) → 4 (developer reproduces first) → 6; add 5 if the fix touches security |
| Review only ("review this branch", "security review") | 0 → 1 → 5 → 6 |
| UI design only | 0 → 1 → 2 → 3 (designer only) → 6 |
| New template / theme pack | 0 → 1 → 3 (designer: tokens + recipes spec) → 4 (pwa-frontend-engineer only, no core component edits allowed) → 6 |
| PWA / Capacitor setup | 0 → 1 → 2 → 3 → 4 (pwa-frontend-engineer) → 5 (include `security`) → 6 |
| Mobile app (new, or added to a web-only project) | 0 → 1 → 2 → **mobile platform choice** → 3 → 4 (pwa-frontend-engineer) → 5 (include `security`) → 6 |
| Follow-up / partial rerun | 0 decides which phase to resume |

## Phase 0 — Context check
1. `.claude/team/project-profile.md` missing, or older than ~30 days, or the stack changed → run Phase 1; else skip it.
2. `_workspace/`:
   - absent → fresh run.
   - present and the request refines previous work → rerun only the affected phase/agent (re-invoke the same agent type with "read your previous output and apply this feedback").
   - present and the request is a new feature → move it to `_workspace_<YYYYMMDD-HHMM>/`, start fresh.
3. If `_workspace/run_meta.json` holds a previous Phase 5 `runId` and only part of the review needs redoing, resume with `resumeFromRunId`.

## Phase 1 — Profile (subagent)
`Agent(subagent_type: "ai-dev-team:repo-scout")`. If the result is `status: greenfield`, tell the user and continue — the architect will propose a stack.

## Phase 2 — Spec (subagent)
1. `Agent(subagent_type: "ai-dev-team:architect")` in spec mode with the user's request verbatim: "Write the spec". Keep its ID — the same agent continues into Phase 3.
2. If it returns open questions, ask the user (AskUserQuestion, max 4 at a time, include proposed defaults).
3. Read `has_ui` and `security_sensitive` from the spec header.
4. **Mobile platform choice.** If the request needs an iOS/Android app and the project profile has `mobile_platform: none`, ask the user with one AskUserQuestion (header `Mobile`) offering, in this order: `Flutter (Recommended)` — one Dart codebase, native performance; `Capacitor (wrap the PWA)` — current setup, fastest, WebView limits; `Native apps` — Swift/SwiftUI + Kotlin/Compose, two codebases, highest cost. Pass the answer to the architect as a decision. Do the same when an implementer returns `needs-user-decision: mobile platform`. Details: `ai-dev-team:pwa-headless-ui` → `references/mobile-options.md`.

## Phase 3 — Design (parallel subagents, one message)
- Always: the Phase 2 `architect` via `SendMessage`: "Design" + the user's answers (it updates the spec first).
- If `has_ui`: `ui-ux-designer`.
- If `security_sensitive`: `security-auditor` (threat model mode).
The designer and security agent read the spec; when the user's answers change it materially, start them after the architect has updated the spec. When all return and the designer or security agent ran, send the same `architect` one reconcile message to fold the UI spec + threat model into the task board.

**User gate:** show a short design summary (task count, key decisions, risks). Wait for approval when: greenfield, data migration, public API change, or > 8 tasks. Otherwise proceed and mention the user can stop you.

## Phase 4 — Build loop (persistent agents)
Start agents per task, not per run: `code-reviewer`, `qa-engineer`, and the implementers the task board needs — `developer` for tasks with Owner `developer`, `pwa-frontend-engineer` for tasks with Owner `pwa-frontend-engineer`; plus `security-auditor` if any task is tagged `security`, `ui-ux-designer` if any task is tagged `ui`. Keep each agent's ID/name from the Agent result and continue it with `SendMessage` for the review, QA and fix rounds of **the same task**, so it keeps that task's context.

**Agent lifetime.** Context grows with every task, and a long-lived agent gets slower and costlier on every turn. So:
- An implementer handles one task (or a small group of tasks that share files) and is then retired. The next task gets a fresh agent of the same type, briefed with the task row, its rule packs and must-read files, the design/UI-spec sections, the previous task notes it depends on, the ledger of rulings, and any repeated-violation warnings from `_workspace/rule-violations.md`.
- Reviewers are never shared across tasks. For each task the leader spawns a **new** `code-reviewer` agent and, when the task needs one, a **new** `security-auditor` agent (and a `ui-ux-designer` for design QA), all in one message so they run in parallel. Reviews of different tasks also run in parallel, each with its own agents. Re-verifying a fix round of the same task goes back to that task's reviewers (`SendMessage`), which keeps their findings in context; a new task always gets new reviewers.
- Replace any agent early when its context passes ~500k tokens, even mid-task: ask it to write its notes file first, then brief the replacement from that file.
- The handover lives in files (`_workspace/04_*_T{id}.md`, the task board, a rulings ledger), never only in an agent's memory. Each agent's first message lists its available tools — if one is missing a tool it needs, restart it without the restriction or do that step yourself.

Topology is **hub-and-spoke**: agents only talk to the leader. This keeps one source of truth and avoids conflicting instructions.

For each task in dependency order (the leader updates the Status column of `_workspace/02_architect_tasks.md`):
1. → the task's Owner (`developer` or `pwa-frontend-engineer`): "Implement T{id}" + the task's rule packs and must-read files. Wait for `DONE` / `BLOCKED`, then apply the DONE gate (`## Rule compliance` table complete, with evidence) before starting review. Tasks may run concurrently, one per implementer, within `max_agents`, only when they are **isolated**: no dependency, no overlap in their `Files` (including shared components, stylesheets, language files, test files and build/config files), and they do not both write tracked build output (bundles, hashed assets, generated manifests). Two tasks of the same frontend app are not isolated by default — they share components, styles and the built bundle — so they run one after the other, or each in its own git worktree (`isolation: "worktree"`, merged back by the leader). Never run several implementers on one working tree when they can touch the same files: each one's tests then fail on the other's half-saved edits, and the reruns cost more than the parallelism saves.
2. **Review and QA in parallel.** Spawn in **one message**: a new `code-reviewer`, plus a new `security-auditor` if the task is tagged `security`, plus `ui-ux-designer` for design QA if tagged `ui`, plus `qa-engineer` ("QA T{id}") — all on the same commit range. Brief each with the task row, the relevant spec/design sections, the task notes, and the rule packs that role verifies with their must-read files; each returns a `## Rule check T{id}` table with its verdict. If that exceeds `max_agents`, start `code-reviewer` and `qa-engineer` first and queue the rest.
   - Reviewers do not run test suites, lint or builds: the implementer's notes carry that output. A reviewer may run one specific test via the wrapper to prove a finding.
   - QA does not rerun the implementer's tests: it checks acceptance criteria and contracts, adds missing integration/e2e tests and runs those, and does browser testing for tasks tagged `ui`, `pwa` or `mobile`. Only one agent does browser work at a time (`COST`, `references/resource-budget.md` §6); Lightpanda-only checks are light and may overlap. QA runs once per task, here — never batched again before sign-off. If QA reports that the browser needs the user (extension not installed/signed in, dialog to dismiss), relay it to the user.
   - A `code-reviewer` finding tagged `→ security` on an untagged task → spawn a `security-auditor` for that task then.
3. Merge all blocker/major/critical/high findings, `QA_FAIL` defects and rule-check `fail`s (by rule ID) into **one** fix request to the task's Owner. After the fix, send re-verification only to the reviewers/QA that raised issues (via `SendMessage`), in parallel. **Max 3 rounds**; then mark `blocked` and report to the user.
4. Mark `done` once coverage holds — every rule ID `pass` from at least one verifier; record `unverified` rule IDs next to the task and append this task's `fail`s to `_workspace/rule-violations.md`. 

**Test cost.** Put these rules in every implementer brief:
- Per task: only the tests related to the changed files (the profile's `test (related)` command, e.g. `vitest related --run <files>`, plus the guard tests mapped to the touched areas), type-check, and the build once at the end when the task needs it. Never the whole suite, never every guard suite.
- Per fix round: only the tests for the files changed in that round.
- A failure in a test the task did not touch and whose source the task did not change is not the implementer's to chase: rerun that one file once; if it still fails, note it and report it — no repeated full runs, no flakiness hunts.
- The full suite runs once at feature sign-off (QA), or earlier only when a change touches shared infrastructure. When the project's test runner is a shared, serial resource (one database, one container), say so in the brief.
- Browser checks for a task run once after its final build (the implementer's full sweep, then QA's own sweep and criteria), not after every test run — `COST` (`references/resource-budget.md`).

After the last task: **one** qa-engineer runs feature sign-off (full suite once, cross-task flows, one overflow run; per-screen visuals are cited from per-task artifacts) — `references/resource-budget.md` §5.

## Phase 5 — Final review (Workflow)
Build `args.dimensions` from the flags: always `correctness` (code-reviewer); `security` if `security_sensitive` or any `security` task; `ui` if `has_ui`. Pass `args.scope` (file list or `git diff` range), spec/design paths, `args.agentPrefix` (`'ai-dev-team:'` by default) and `args.maxAgents` (the profile's `max_agents`; the workflow never runs more agents than that at once). Then call Workflow with `scriptPath` set to the absolute path of `references/final-review.workflow.js` in this skill's base directory (if the path cannot be passed, Read that file and pass its content as `script`). The script reviews each dimension, adversarially verifies serious findings, caps concurrency at `maxAgents`, and returns `{ confirmed, uncertain, minor, missingDimensions }`.

Write the returned `runId` to `_workspace/run_meta.json`. Wait for the completion notification; never predict results. Then:
- `confirmed` → back to Phase 4 for fixes (counts as a new round), then re-run only the affected dimension (resume the workflow).
- `uncertain` → list for the user with the reason.
- Save the full result to `_workspace/06_final_review.json`.

## Phase 6 — Report (to the user, in their language)
Summary of what was built, files changed, test/QA results with real numbers, review outcome (confirmed fixed / uncertain / minor), rule compliance (rule IDs left `unverified`, rules that failed in two or more tasks), anything skipped or blocked and why. Do not commit unless the user asks; commit messages follow the developer rules (English, imperative, no AI attribution).

## Data passing
- Files in `_workspace/` named `{phase}_{agent}_{artifact}.{ext}`; final deliverables are the code in the repo. Keep `_workspace/` for audit.
- Messages carry only verdicts and short summaries; details live in files.

## Error handling
| Situation | Action |
|---|---|
| Agent fails once | Retry once with the same input. Fails again → continue without it and record the gap in the report. |
| Usage limit, auth expired, permission denied | Do not retry. Open partial outputs to see real progress, write `_workspace/gaps.md`, report to the user (include limit reset time if known). |
| Persistent agent unresponsive | `SendMessage` a status ping and re-send the instruction. Still stuck → start a fresh agent of the same type with the task context and previous outputs. |
| Stalled agent left gaps | Fill only facts you verified yourself; never invent the agent's judgments. |
| Workflow agent returned null | Handled by `.filter(Boolean)`; report missing dimensions. Diagnose via the run journal, then resume with `resumeFromRunId`. |
| Conflicting findings between agents | Keep both with sources; ask the user only if it changes behavior. |
| 3 fix rounds exhausted | Mark task `blocked`, stop dependent tasks, report with the developer's root-cause analysis. |

## Test scenarios
Expected normal and error flows are in `references/test-scenarios.md` (read when changing or evaluating this skill).
