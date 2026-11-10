# ai-dev-team — AI software development team for Claude Code

A Claude Code plugin that adds a 3-agent software team and an orchestrator skill. It takes work from a raw request to reviewed, tested code: profile → spec → plan → build / review / QC loop → verified final review. It works with any stack, detected automatically, and carries rules for mobile-first PWAs (Vue 3 / React + TypeScript, headless core components, swappable templates) and mobile apps — the user picks Flutter (recommended), Capacitor wrapping the PWA, or native Swift/Kotlin.

## Team

| Who | Model | Role |
|---|---|---|
| leader (the `dev-team` skill, in the main session) | session model | Profiles the repo, plans with the user (with `superpowers` brainstorming + writing-plans when installed), owns the task board, briefs agents, merges feedback, reports |
| `developer` | opus | Builds every task — backend, web frontend, PWA, Flutter / Capacitor / native — test-first; writes the UI spec before screens are built; applies fixes |
| `reviewer` | opus | One read-only pass per task over code quality, security and UI conformance (design QA); threat models, full audits, final-review dimensions and adversarial verification |
| `qc` | sonnet | Acceptance criteria and cross-module contracts with evidence; browser checks on the lightest engine that fits (Lightpanda, Playwright headless shell / WebKit, Claude in Chrome as last fallback), Flutter widget/golden tests; feature sign-off |

All agents and skills are namespaced by the plugin, e.g. `ai-dev-team:developer`, `ai-dev-team:dev-team`.

## Install

From a local clone:
```bash
claude --plugin-dir /path/to/ai-team            # try it for one session without installing
```
```
/plugin marketplace add mvanvu/ai-dev-team        # or a local clone path
/plugin install ai-dev-team@mvanvu
```

To have a project prompt teammates to install it, add to that project's `.claude/settings.json`:
```json
{
  "extraKnownMarketplaces": {
    "mvanvu": { "source": { "source": "git", "url": "https://github.com/mvanvu/ai-dev-team.git" } }
  },
  "enabledPlugins": { "ai-dev-team@mvanvu": true }
}
```

## Usage

Describe the work in a project. The `ai-dev-team:dev-team` skill triggers on requests like "build feature X", "fix this bug", "add a screen", "make it a PWA", "add a new template", "review this branch", "security review", or invoke it explicitly with `/ai-dev-team:dev-team <request>`.

The orchestrator writes to the target project:
- `.claude/team/project-profile.md`: detected stack, verified commands and the resource budget, kept across runs.
- `.claude/team/run-heavy.sh`: wrapper that runs heavy commands (tests, builds, audits) one at a time at low CPU priority.
- `.claude/team/rule-checks.sh` and `.claude/team/overflow-check.mjs`: scripts that decide the rules a machine can check (forbidden imports in feature code, list filters in web storage, AI attribution in commits, pre-release dependencies, text overflow on phone viewports).
- `_workspace/`: spec, plan, UI spec, threat model, task board, task notes, QC reports. Add `_workspace/` and `_workspace_*/` to the project's `.gitignore`.

The final review phase uses the Workflow tool. Invoking the `dev-team` skill counts as consent; it stays small (≤ 3 reviewers + verifiers) unless you ask for a thorough review.

### Resource budget
Parallel agents are cheap; the test runners and builds they start are not. The profile sets the budget, and you can edit it:
- `max_agents` (default 4): agents running at once, including the final-review workflow; extra work queues.
- `heavy_workers` (default CPU threads ÷ 4): worker cap written into every heavy test/build command.
- Heavy commands go through `.claude/team/run-heavy.sh`, which lets only one run at a time on the machine (`flock`, with a `mkdir` lock fallback on macOS) under `nice`. `AI_DEV_TEAM_LOCK_WAIT` sets the maximum wait in seconds (default 1800).

The reviewer reads the developer's test output instead of rerunning it, per-task QC runs in parallel with review, and the full suite runs once at sign-off. Developers run only the tests related to the files they changed (`vitest related`, mapped guards), once per task and once per fix round; tasks that share files or a built bundle never run at the same time on one working tree.

Heavy commands and UI checks follow two rule packs (`skills/dev-team/references/resource-budget.md`): `COST` for every task (each check once by the agent that owns it, browsers and runners queued by the wrapper, no `sleep`/`pgrep` polling, one sign-off qc with one full-suite run) and `SWEEP` for web screens (every changed screen at every width tier × every theme from the profile in one `overflow-check.mjs --sheet` run per build, one contact sheet per screen that the developer, reviewer and qc each look at, no second sweep of an unchanged build).

## Conventions

- All files the team writes (code, comments, specs, commit messages) are in English. Replies to the user follow the user's language.
- Phone screens (mobile web and app) waste no space and never overflow: adjacent buttons and short fields share a row when they fit, icon/text rows leave no dead space, every text element has a truncate / clamp / wrap rule checked with worst-case strings (`skills/pwa-headless-ui/references/compact-layout.md`).
- Default stack when the request names no technology: NestJS backend, PostgreSQL + Prisma, Redis for caching, Vue 3 + TypeScript frontend — proposed for approval, and only for parts the project does not already have (`skills/technical-design/SKILL.md`).
- Mobile lists support pull to refresh of the visible tab only, without triggering the browser reload or fighting tab swipes (`skills/pwa-headless-ui/references/pull-to-refresh.md`); app screens carry no redundant instruction text, and designs avoid the generated look (`skills/ui-ux-design/references/authentic-design.md`).
- Query count never grows with row count: no N+1 queries or per-row requests, proven by query-count tests (`skills/code-review-checklist/references/query-performance.md`).
- Rules are enforced per task: the task board lists the rule packs each task must follow, the developer reports one row of evidence per rule, the reviewer and qc re-check them, and the leader only closes a task when every rule is confirmed (`skills/dev-team/references/rule-packs.md`).
- No commits unless you ask; commit messages are imperative English with no AI attribution.

## Optional companions

The plugin installs nothing besides itself. When one of these is already installed in the session, the agent uses it; when it is not, the agent works from the plugin's own skills.

| Companion | Used by | For |
|---|---|---|
| `superpowers` | leader, developer | `brainstorming` (spec with the user) and `writing-plans` (plan) in planning; `systematic-debugging` on hard bugs |
| `ui-ux-pro-max` | developer (UI design) | palettes, font pairings, stack-specific UX data |

### Third-party material
The full-audit procedure and attack-class catalog in `skills/security-review-checklist/references/` are condensed and adapted from Cloudflare's [`security-audit`](https://github.com/cloudflare/security-audit-skill) skill (MIT) — see `THIRD-PARTY-NOTICES.md`.

## Structure

```
.claude-plugin/plugin.json       plugin manifest
.claude-plugin/marketplace.json  single-plugin marketplace (mvanvu)
.claude-plugin/icon.png          plugin icon (source: scripts/icon-source.svg)
agents/                          3 agent definitions (developer, reviewer, qc)
skills/dev-team/                 orchestrator
skills/<role-skill>/             per-role procedures (some have references/, e.g. project-profiling/references/run-heavy.sh)
scripts/check-plugin.py          repo consistency check (cross-references, rule packs, version)
```

Validate after changes: `python3 scripts/check-plugin.py`, `claude plugin validate .` and `claude --plugin-dir . plugin details ai-dev-team`.

## License

MIT — see [LICENSE](LICENSE).
