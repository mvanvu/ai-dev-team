---
name: dev-team
description: "Orchestrates the AI software team — developer, reviewer, qc — through profile → spec → plan → build/review/QC → final review, with planning done by the leader (superpowers brainstorming and writing-plans when installed). Use for building features, fixing bugs, refactors, new web/mobile screens, PWA/Capacitor/Flutter apps, UI templates, or full reviews: 'build feature X', 'implement', 'add a screen', 'make it a PWA', 'build a mobile app', 'add a new template', 'fix this bug', 'review this branch', 'security review', 'start a new project'. Also for follow-ups: continue, resume, re-run, revise, 'only redo the design'. Skip for simple questions or one-line edits."
---

# Dev Team orchestrator

The main session is the **leader**. It profiles the repo, plans with the user, owns the task board, briefs the agents, merges their feedback and talks to the user (in the user's language). It never writes production code itself. All files the team writes are in English.

## Team

| Agent (`subagent_type`) | Model | Skills | Modes | Output |
|---|---|---|---|---|
| `developer` | opus | implementation; pwa-headless-ui for web/PWA/mobile; ui-ux-design for UI design | implement, UI design, fix, bug | code + tests, `_workspace/04_dev_T{id}.md`, `_workspace/02_ui-spec.md` |
| `reviewer` | opus | code-review-checklist; security-review-checklist; ui-ux-design (design QA) | review (code + security + design QA in one pass), threat model, final-review dimension, verify, full audit | verdicts, `_workspace/02_threat-model.md` |
| `qc` | sonnet | qa-verification | QC per task, sign-off | `_workspace/05_qc_report.md`, `_workspace/qa-artifacts/` |

The leader itself uses `project-profiling` (Phase 1), and for planning `superpowers:brainstorming` + `superpowers:writing-plans` when the `superpowers` plugin is installed in this session — otherwise `spec-writing` + `technical-design`. `technical-design` also holds the task-board format, default stack, toolchain and sizing rules the plan must meet either way.

### Agent and skill names
Installed as the `ai-dev-team` plugin, agents and skills carry the `ai-dev-team:` prefix: `subagent_type: "ai-dev-team:developer"`, skills `ai-dev-team:<skill>`. If the agent list shows un-prefixed names (files copied into a project's `.claude/`), use those and pass `agentPrefix: ''` to the Phase 5 workflow.

## Routing by request type

| Request | Phases |
|---|---|
| **Small change** — a few files, no contract/schema/public-API change, no new screen ("quick fix", typo-level bug, small tweak) | 0 → 1 if no profile → one-row board → 4 (developer, then reviewer; qc only when a criterion needs runtime proof) → 6 |
| Bug (non-trivial) | 0 → 1 → 2 (bug spec: repro, expected, `AC-n`) → 3 (board only, usually one or two rows) → 4 (developer reproduces first) → 6; add 5 if the fix touches security |
| New feature / screen | 0 → 1 → 2 → 3 → 4 → 5 → 6 |
| New project (greenfield) | 0 → 1 → 2 → 3 (stack proposal, **user approves**) → 4 (scaffold task first, then **rerun 1** to profile the new commands, then the rest) → 5 → 6 |
| Review only ("review this branch", "security review", "audit") | 0 → 1 → 5 (`mode: 'review-only'`) → 6 |
| UI design only | 0 → 1 → 2 → 3 (developer in UI design mode only) → 6 |
| New template / theme pack | 0 → 1 → 2 (short) → 3 (developer UI design: tokens + recipes) → 4 (no core component edits) → 6 |
| PWA / Capacitor setup, mobile app | 0 → 1 → 2 → **mobile platform choice** → 3 → 4 → 5 (include `security`) → 6 |
| Continue / resume / follow-up | Phase 0 decides |

When unsure whether a change is small, treat it as a bug route; when a "small change" grows past its limits during work, upgrade it to the bug route.

## Resource budget
The budget lives in the project profile (`max_agents`, `heavy_workers`, the `run-heavy` wrapper, `ui_widths`, `ui_themes` — written in Phase 1):
- **Max concurrent agents: `max_agents` (default 4)**, counting every background and Workflow agent, not the leader. When the cap is reached, queue the next spawn. Priority: fix rounds, then review/QC of in-flight tasks, then new tasks.
- Heavy commands (suites, builds, e2e, audits, browser launches) go through `.claude/team/run-heavy.sh`; it serializes them across agents, so the leader does not need to schedule browser or test work by hand. Missing wrapper → rerun Phase 1.
- `COST` applies to every task and `SWEEP` to every task that changes a web screen — `references/resource-budget.md`: each check runs once by the agent that owns it, full width × theme sweep in one run per build, no `sleep`/`pgrep` polling, one sign-off qc with one full-suite run. A brief never raises these limits unless the user asked — and then the user hears the cost first.

## Rule compliance
Every task carries its rules explicitly — procedure and formats in `references/rule-packs.md`:
- The task board's `Rules` column lists the packs per task (`BASE` and `COST` implied); a rule ID is pack + item number (`COMPACT-3`), plus the task's `AC-n` and `SEC-n`.
- **Brief**: every developer, reviewer and qc brief includes the task's rule packs with their must-read files (§2). Never brief with "follow the skill" alone.
- **DONE gate**: the notes hold a `## Rule compliance` table, one row per rule ID with evidence; spot-check self-attested rows. Missing rows → send back (not a fix round).
- **Verdict gate**: reviewer and qc verdicts carry a `## Rule check T{id}` table.
- **Coverage**: `done` when every observable rule ID has a verifier `pass`; rules nobody could observe are reported `unverified`.
- **Ledger**: verifier `fail`s go to `_workspace/rule-violations.md`; a rule that fails in two tasks becomes a warning line in every later brief.

## Phase 0 — Context check
1. `.claude/team/project-profile.md` missing, older than ~30 days, or the stack changed → Phase 1; else skip it.
2. `_workspace/`:
   - absent → fresh run.
   - present with unfinished tasks on the board (`in progress`, `review`, `fix`) and the user says continue/resume, or asks something that fits the same feature → **resume** (below).
   - present, all tasks `done`, and the request is new → move it to `_workspace_<YYYYMMDD-HHMM>/` and start fresh. If unfinished tasks remain and the request is unrelated, ask the user before archiving them.
   - a follow-up on finished work ("only redo the design", "improve X") → rerun only the affected phase or task.
3. **Resume**: read the task board's Status and Rounds columns. For each unfinished task read `_workspace/04_dev_T{id}.md` and `git diff`, then brief a fresh developer with "continue T{id} from these notes" (or a fresh reviewer/qc for a pending verdict). Round counts come from the board, never restart at zero. A previous Phase 5 `runId` in `_workspace/run_meta.json` → resume it with `resumeFromRunId`.

## Phase 1 — Profile (leader)
Follow `ai-dev-team:project-profiling`: detect the stack, verify the commands, record conventions, UI presence and the budget, and install the team scripts in `.claude/team/` from that skill's `references/` directory. Run long verification commands in the background through the wrapper and keep only trimmed output in context. A greenfield repo still gets the scripts and the budget; its commands are profiled again right after the scaffold task.

## Phase 2 — Spec (leader with the user)
1. **With superpowers**: run `superpowers:brainstorming` with the user's request (it explores context, asks one question at a time, gets approval and saves the spec). **Without**: write the spec with `ai-dev-team:spec-writing` and ask open questions with AskUserQuestion (max 4 at a time, proposed defaults first).
2. Make sure the spec — wherever it was saved — has the header fields of `ai-dev-team:spec-writing`: `has_ui`, `security_sensitive`, acceptance criteria numbered `AC-1…`, open questions resolved. Copy or link it as `_workspace/01_spec.md`.
3. Product decisions stay with the user: entity lifecycle (`ai-dev-team:technical-design` → `references/record-lifecycle.md`), public-API changes, data deletion, AI-crawler policy — ask with a proposed default.
4. **Mobile platform choice.** When the request needs an iOS/Android app and the profile has `mobile_platform: none`, ask with one AskUserQuestion (header `Mobile`): `Flutter (Recommended)` — one Dart codebase, native performance; `Capacitor (wrap the PWA)` — fastest, WebView limits; `Native apps` — Swift/SwiftUI + Kotlin/Compose, two codebases, highest cost. Same when a developer returns `needs-user-decision: mobile platform`. Details: `ai-dev-team:pwa-headless-ui` → `references/mobile-options.md`.

## Phase 3 — Plan (leader + agents in parallel)
1. Spawn in one message, when the spec calls for them:
   - `has_ui` → `developer` in **UI design** mode → `_workspace/02_ui-spec.md`.
   - `security_sensitive` → `reviewer` in **threat model** mode → `_workspace/02_threat-model.md` with `SEC-n`.
2. Meanwhile write the plan: **with superpowers** `superpowers:writing-plans` (stop when it offers an execution mode — the build loop below executes the plan; do not hand over to `subagent-driven-development` or `executing-plans`); **without**, `ai-dev-team:technical-design`. Either way the plan meets `technical-design`: contracts between modules, decisions with reasons, default stack and latest-stable toolchain for greenfield, 3–8 tasks sized for throughput.
3. When the UI spec and threat model are back, write `_workspace/02_tasks.md` in the task-board format of `ai-dev-team:technical-design` (ID, title, depends, files, tags `ui`/`pwa`/`mobile`/`security`, `Rules` per `references/rule-packs.md` §5 incl. `AC-n`/`SEC-n`, verify command, Status, Rounds). Contradictions between spec, UI spec and threat model go to the user.

**User gate:** show a short plan summary (task count, key decisions, risks). Wait for approval when: greenfield, data migration, public API change, or > 8 tasks. Otherwise proceed and say the user can stop you.

## Phase 4 — Build loop
Topology is **hub-and-spoke**: agents talk only to the leader. Handover lives in files (task notes, the board, the rulings ledger), never only in an agent's memory. Each agent's first message lists its tools — one missing a tool it needs is restarted or that step is done by the leader.

For each task in dependency order (update Status and Rounds on the board as you go):
1. **Build** → a fresh `developer`: "Implement T{id}" + task row, rule packs and must-read files, the relevant spec / plan / UI-spec / threat-model sections, notes of tasks it depends on, ledger warnings. Wait for `DONE` / `BLOCKED`, apply the DONE gate.
   Tasks run concurrently, one developer each within `max_agents`, only when **isolated**: no dependency, no overlap in their files (shared components, styles, language files, tests, build config included) and no shared built output. Two tasks of one frontend app are not isolated by default — run them one after the other, or each in its own git worktree (`isolation: "worktree"`, merged back by the leader).
2. **Verify in parallel** — one message: a fresh `reviewer` ("Review T{id}": code + security + design QA as the task's tags and packs require) and a fresh `qc` ("QC T{id}"; skipped on the small-change route unless a criterion needs runtime proof). Brief each with the task row, the sections it needs, the task notes, and the packs it verifies with their must-read files. Reviewers do not run suites; qc does not rerun the developer's tests.
3. **Fix**: merge blocker/major/critical/high findings, `QC_FAIL` defects and rule-check `fail`s into **one** fix request to the same developer (`SendMessage`; a fresh one with the notes if it is gone). Re-verification goes only to the agents that raised issues, via `SendMessage`. Increment Rounds; **max 3**, then mark `blocked` and tell the user.
   `QC_BLOCKED` (environment, missing service, browser needs the user): fix the environment or ask the user; the task is never `done` while qc is blocked.
4. **Done** when coverage holds; record `unverified` rule IDs on the board and this task's `fail`s in the ledger. Retire the task's agents.

Replace any agent early when its context passes ~500k tokens: ask it to write its notes first, then brief the replacement from them.

**Test cost** (put in every developer brief): per task only the related tests of the changed files + mapped guards, type-check, build once at the end; per fix round only that round's files; a failure in a test the task did not touch → rerun that file once, then report it `not mine`. The full suite runs once at sign-off, or earlier only when a change touches shared infrastructure. When the profile records `tests: none`, say so in the brief: evidence is the reproduction steps and command output the task criteria need; the plan should contain a task that adds a test runner when the user agrees.

After the last task: **one** `qc` in sign-off mode (`references/resource-budget.md` §5).

## Phase 5 — Final review (Workflow)
It runs on every route that lists it, whatever the task count — per-task reviews cannot see how tasks interact. Build `args.dimensions`: always `correctness`; `security` if `security_sensitive` or any `security` task; `ui` if `has_ui`. Pass `args.scope` (file list or `git diff` range), `args.mode` (`'feature'`, or `'review-only'` on the review-only route), `args.specPath` / `args.designPath` when they exist, `args.agentPrefix` (`'ai-dev-team:'` by default) and `args.maxAgents` (the profile's `max_agents`). Call Workflow with `scriptPath` = the absolute path of `references/final-review.workflow.js` in this skill's directory (or Read it and pass it as `script`). Every dimension and verifier is a `reviewer` agent; in feature mode the reviewers focus on cross-task interactions, since per-task review already covered each task. The result is `{ confirmed, uncertain, minor, missingDimensions }`.

Write the `runId` to `_workspace/run_meta.json`; wait for the completion notification, never predict results. `confirmed` → back to Phase 4 as a fix round, then resume only the affected dimension. `uncertain` → list for the user. Save the result to `_workspace/06_final_review.json`.

## Phase 6 — Report (to the user, in their language)
What was built, files changed, test/QC results with real numbers, review outcome (confirmed fixed / uncertain / minor), rule compliance (`unverified` IDs, rules that failed in two or more tasks), anything skipped or blocked and why. No commits unless the user asks; messages English, imperative, no AI attribution.

## Data passing
- Files in `_workspace/`: `01_spec.md`, `02_plan.md` (or a link to the superpowers plan), `02_ui-spec.md`, `02_threat-model.md`, `02_tasks.md`, `04_dev_T{id}.md`, `05_qc_report.md`, `qa-artifacts/`, `rule-violations.md`, `06_final_review.json`. Final deliverables are the code in the repo.
- Messages carry verdicts and short summaries; details live in files.

## Error handling
| Situation | Action |
|---|---|
| Agent fails once | Retry once with the same input. Fails again → continue without it and record the gap in the report. |
| Usage limit, auth expired, permission denied | Do not retry. Write `_workspace/gaps.md`, keep the board's Status/Rounds current, report to the user (with the reset time if known); the next "continue" resumes from Phase 0. |
| Agent unresponsive | `SendMessage` a status ping and re-send the instruction. Still stuck → a fresh agent of the same type briefed from the notes. |
| `QC_BLOCKED` | Fix the environment if the leader can (start a service the profile names), else ask the user; never mark the task `done`. |
| Repo has no tests / lint / type-check | Profile records `tests: none` etc.; rules that need them are `n-a` with that reason; offer the user a task that adds them. |
| Workflow agent returned null | Report missing dimensions; resume with `resumeFromRunId`. |
| Conflicting findings | Keep both with sources; ask the user only if it changes behavior. |
| 3 fix rounds exhausted | Mark `blocked`, stop dependent tasks, report with the developer's root-cause analysis. |

## Test scenarios
Expected normal and error flows: `references/test-scenarios.md` (read when changing or evaluating this skill).
