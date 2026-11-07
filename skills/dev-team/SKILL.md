---
name: dev-team
description: "Orchestrates the AI software team (repo-scout, requirements-analyst, architect, ui-ux-designer, developer, pwa-frontend-engineer, code-reviewer, security-auditor, qa-engineer) through spec → design → build/review/QA → final review. Use for building features, fixing non-trivial bugs, refactors, new web/mobile screens, PWA/Capacitor apps, UI templates, or full reviews: 'build feature X', 'implement', 'add a screen', 'make it a PWA', 'add a new template', 'fix this bug', 'review this branch', 'security review', 'start a new project'. Also use for follow-ups: re-run, update, revise, continue, 'only redo the design', 'improve previous result'. Skip for simple questions or one-line edits."
---

# Dev Team orchestrator

The main session is the **leader**. It never writes production code itself; it routes work, owns the task board, relays feedback between agents, and talks to the user (in the user's language). All files the team writes are in English.

## Execution mode: mixed

| Phase | Mode | Why |
|---|---|---|
| 0 Context check | leader | — |
| 1 Profile | subagent | one-shot fact gathering |
| 2 Spec | subagent | one-shot; leader handles user Q&A |
| 3 Design | subagents in parallel | architect, designer, security are independent given the spec |
| 4 Build loop | per-task agents | an implementer keeps context across one task's review/QA rounds, then is replaced |
| 5 Final review | workflow | fixed fan-out over dimensions + adversarial verification |
| 6 Report | leader | — |

Invoking this skill counts as consent for the Phase 5 Workflow. Keep it small by default (≤ 3 review agents + verifiers); scale up only when the user asks for a "thorough" / "full" review.

## Team

| Agent (`subagent_type`) | Model | Skill | Output |
|---|---|---|---|
| `repo-scout` | sonnet | project-profiling | `.claude/team/project-profile.md` |
| `requirements-analyst` | opus | spec-writing | `_workspace/01_analyst_spec.md` |
| `architect` | opus | technical-design | `_workspace/02_architect_design.md`, `02_architect_tasks.md` |
| `ui-ux-designer` | opus | ui-ux-design | `_workspace/02_designer_ui-spec.md` |
| `security-auditor` | opus | security-review-checklist | `_workspace/02_security_threat-model.md`, review verdicts |
| `developer` | opus | implementation | backend / non-UI code + `_workspace/04_developer_T{id}.md` |
| `pwa-frontend-engineer` | opus | pwa-headless-ui (+ implementation) | frontend code (Vue 3 / React TS, core components, templates, PWA, Capacitor) + `_workspace/04_pwa_T{id}.md` |
| `code-reviewer` | opus | code-review-checklist | review verdicts |
| `qa-engineer` | sonnet | qa-verification | `_workspace/05_qa_report.md` |

### Agent and skill names
This team ships as the `ai-dev-team` plugin, so Claude Code exposes every agent and skill with the `ai-dev-team:` prefix: call agents as `subagent_type: "ai-dev-team:<agent>"` (e.g. `ai-dev-team:developer`) and skills as `ai-dev-team:<skill>`. The tables use short names for readability. If the agent list shows the un-prefixed names (files copied into a project's `.claude/` instead of installed as a plugin), use those and pass `agentPrefix: ''` to the Phase 5 workflow.

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
1. `Agent(subagent_type: "ai-dev-team:requirements-analyst")` with the user's request verbatim.
2. If it returns open questions, ask the user (AskUserQuestion, max 4 at a time, include proposed defaults). Re-invoke the analyst with the answers.
3. Read `has_ui` and `security_sensitive` from the spec header.

## Phase 3 — Design (parallel subagents, one message)
- Always: `architect`.
- If `has_ui`: `ui-ux-designer`.
- If `security_sensitive`: `security-auditor` (threat model mode).
When all return and the designer or security agent ran, re-invoke `architect` once to reconcile the UI spec + threat model into the task board.

**User gate:** show a short design summary (task count, key decisions, risks). Wait for approval when: greenfield, data migration, public API change, or > 8 tasks. Otherwise proceed and mention the user can stop you.

## Phase 4 — Build loop (persistent agents)
Start agents per task, not per run: `code-reviewer`, `qa-engineer`, and the implementers the task board needs — `developer` for tasks with Owner `developer`, `pwa-frontend-engineer` for tasks with Owner `pwa-frontend-engineer`; plus `security-auditor` if any task is tagged `security`, `ui-ux-designer` if any task is tagged `ui`. Keep each agent's ID/name from the Agent result and continue it with `SendMessage` for the review, QA and fix rounds of **the same task**, so it keeps that task's context.

**Agent lifetime.** Context grows with every task, and a long-lived agent gets slower and costlier on every turn. So:
- An implementer handles one task (or a small group of tasks that share files) and is then retired. The next task gets a fresh agent of the same type, briefed with the task row, the design/UI-spec sections, the previous task notes it depends on, and the ledger of rulings.
- Reviewers are never shared across tasks. For each task the leader spawns a **new** `code-reviewer` agent and, when the task needs one, a **new** `security-auditor` agent (and a `ui-ux-designer` for design QA), all in one message so they run in parallel. Reviews of different tasks also run in parallel, each with its own agents. Re-verifying a fix round of the same task goes back to that task's reviewers (`SendMessage`), which keeps their findings in context; a new task always gets new reviewers.
- Replace any agent early when its context passes ~500k tokens, even mid-task: ask it to write its notes file first, then brief the replacement from that file.
- The handover lives in files (`_workspace/04_*_T{id}.md`, the task board, a rulings ledger), never only in an agent's memory. Each agent's first message lists its available tools — if one is missing a tool it needs, restart it without the restriction or do that step yourself.

Topology is **hub-and-spoke**: agents only talk to the leader. This keeps one source of truth and avoids conflicting instructions.

For each task in dependency order (the leader updates the Status column of `_workspace/02_architect_tasks.md`):
1. → the task's Owner (`developer` or `pwa-frontend-engineer`): "Implement T{id}". Wait for `DONE` / `BLOCKED`. Backend and frontend tasks with no dependency between them may run concurrently, one per implementer.
2. Spawn this task's own reviewers in **one message** so they run in parallel: a new `code-reviewer`, plus a new `security-auditor` if the task is tagged `security` or any finding is tagged `→ security`, plus `ui-ux-designer` for design QA if tagged `ui`. Brief each with the commit range, the task row, the relevant spec/design sections and the task notes.
3. Any blocker/major/critical/high → forward the merged findings to the task's Owner → back to the same task's reviewers that raised issues (via `SendMessage`), not new ones. **Max 3 rounds**; then mark `blocked` and report to the user.
4. → qa-engineer: "QA T{id}". Tasks tagged `ui` or `pwa` include browser testing (Claude in Chrome, Playwright fallback). The browser is a shared resource: run browser QA for one task at a time. If QA reports that the browser needs the user (extension not installed/signed in, dialog to dismiss), relay it to the user. `QA_FAIL` → Owner fixes → QA again (counts toward the 3 rounds).
**Test cost.** Per task, run only the tests related to the change (the task's own tests, the suites for the touched modules, and the fast guards). The full suite runs at feature sign-off and in Phase 5, or earlier only when a change touches shared infrastructure. When the project's test runner is a shared, serial resource (one database, one container), say so in the brief and keep runs targeted so agents do not queue behind each other.
5. Mark `done`. Independent tasks (no shared files, no dependency) may run with a second developer instance using `isolation: "worktree"`, only when there are ≥ 4 independent tasks.

After the last task: qa-engineer runs feature sign-off.

## Phase 5 — Final review (Workflow)
Build `args.dimensions` from the flags: always `correctness` (code-reviewer); `security` if `security_sensitive` or any `security` task; `ui` if `has_ui`. Pass `args.scope` (file list or `git diff` range), spec/design paths, and `args.agentPrefix` (`'ai-dev-team:'` by default). Then call Workflow with this script:

```javascript
export const meta = {
  name: 'dev-team-final-review',
  description: 'Review the feature per dimension, then adversarially verify serious findings',
  phases: [{ title: 'Review' }, { title: 'Verify' }],
}

const FINDINGS = { type: 'object', required: ['findings'], properties: {
  findings: { type: 'array', items: { type: 'object',
    required: ['title', 'file', 'severity', 'scenario', 'fix'], properties: {
      title: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' },
      severity: { type: 'string', enum: ['critical', 'high', 'blocker', 'major', 'medium', 'minor', 'low'] },
      scenario: { type: 'string' }, fix: { type: 'string' } } } } } }
const VERDICT = { type: 'object', required: ['status', 'reason'], properties: {
  status: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
  reason: { type: 'string' } } }

// Plugin agents are namespaced; the leader passes the prefix it sees in the agent list.
const P = args.agentPrefix ?? 'ai-dev-team:'
const AGENT = { correctness: `${P}code-reviewer`, security: `${P}security-auditor`, ui: `${P}ui-ux-designer` }
const SKILL = { correctness: `${P}code-review-checklist`, security: `${P}security-review-checklist`, ui: `${P}ui-ux-design (Design QA section)` }
const SERIOUS = ['critical', 'high', 'blocker', 'major']
const ctx = `Scope: ${args.scope}\nSpec: ${args.specPath}\nDesign: ${args.designPath}`

const results = await pipeline(
  args.dimensions,
  d => agent(
    `Final ${d} review of the feature. Follow the ${SKILL[d]} skill.\n${ctx}\nReturn findings JSON only; empty array if none.`,
    { agentType: AGENT[d], label: `review:${d}`, phase: 'Review', schema: FINDINGS })
    .then(r => (r ? r.findings.map(f => ({ ...f, dimension: d })) : null)),
  findings => findings === null ? null : parallel(findings.map(f => () =>
    SERIOUS.includes(f.severity)
      ? agent(
          `Adversarially verify this finding. Try to refute it by reading the code, callers, guards and tests. confirmed = reachable failure; refuted = prevented; uncertain = cannot decide.\n${JSON.stringify(f)}\n${ctx}`,
          { agentType: AGENT[f.dimension], label: `verify:${f.file}`, phase: 'Verify', schema: VERDICT, effort: 'high' })
          .then(v => ({ ...f, verdict: v ?? { status: 'uncertain', reason: 'verifier failed' } }))
      : Promise.resolve({ ...f, verdict: { status: 'unverified', reason: 'minor severity' } })))
)

const missing = results.filter(r => r === null).length
if (missing) log(`${missing} review dimension(s) failed and are missing from the result`)
const all = results.filter(Boolean).flat().filter(Boolean)
const confirmed = all.filter(f => f.verdict.status === 'confirmed')
const uncertain = all.filter(f => f.verdict.status === 'uncertain')
const minor = all.filter(f => f.verdict.status === 'unverified')
log(`${all.length} findings: ${confirmed.length} confirmed, ${uncertain.length} uncertain, ${minor.length} minor`)
return { confirmed, uncertain, minor, missingDimensions: missing }
```

Write the returned `runId` to `_workspace/run_meta.json`. Wait for the completion notification; never predict results. Then:
- `confirmed` → back to Phase 4 for fixes (counts as a new round), then re-run only the affected dimension (resume the workflow).
- `uncertain` → list for the user with the reason.
- Save the full result to `_workspace/06_final_review.json`.

## Phase 6 — Report (to the user, in their language)
Summary of what was built, files changed, test/QA results with real numbers, review outcome (confirmed fixed / uncertain / minor), anything skipped or blocked and why. Do not commit unless the user asks; commit messages follow the developer rules (English, imperative, no AI attribution).

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

### Normal flow
1. User: "Add password reset by email." Profile exists (Symfony + React).
2. Analyst returns spec with `has_ui=true`, `security_sensitive=true`, 1 open question (token TTL; default 30 min) → user accepts default.
3. Design phase runs architect + designer + security in parallel; architect reconciles → 5 tasks (2 tagged security, 1 tagged ui).
4. Build loop: T2 gets a `high` finding (token not single-use) → developer fixes → security re-review `SECURE` → QA_PASS.
5. Final review workflow: 3 dimensions, 1 minor finding. Report lists 5 tasks done, all ACs pass.

### Normal flow — new template pack
1. User: "Add a 'corporate' template." Profile: Vue 3 + reka-ui, PWA, Capacitor.
2. Designer specs tokens + per-component recipe changes; pwa-frontend-engineer copies `src/templates/default/` → `corporate/`, edits only tokens/recipes/shells.
3. Code-reviewer confirms `git diff` touches no file under `src/ui/core/` or `src/features/`; type-check proves the contract is complete; QA runs component tests against both templates.

### Error flow
1. During Phase 5 the `ui` dimension agent fails twice → returns null.
2. Workflow logs "1 review dimension(s) failed"; result has `missingDimensions: 1`.
3. Leader reports the missing UI review in Phase 6 and offers to resume it via `resumeFromRunId`.
