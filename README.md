# ai-dev-team — AI software development team for Claude Code

A Claude Code plugin that adds an 8-agent software team and an orchestrator skill. It takes work from a raw request to reviewed, tested code: spec → design → build/review/QA loop → verified final review. It works with any stack, detected automatically, and includes a specialist for mobile-first PWAs (Vue 3 / React + TypeScript, headless core components, swappable templates) and mobile apps — the user picks Flutter (recommended), Capacitor wrapping the PWA, or native Swift/Kotlin.

## Agents

| Agent | Model | Role |
|---|---|---|
| `repo-scout` | sonnet | Detects stack, verifies test/lint/build commands, writes the project profile |
| `architect` | opus | Spec with testable acceptance criteria, technical design, API contracts, task breakdown, stack proposals |
| `ui-ux-designer` | opus | Web/mobile UI specs, design tokens, accessibility, design QA |
| `developer` | opus | Backend / non-UI implementation with TDD |
| `pwa-frontend-engineer` | opus | Vue 3 / React TS PWA, headless core components + template packs; mobile app via Flutter (recommended), Capacitor or native |
| `code-reviewer` | opus | Read-only code review |
| `security-auditor` | opus | Threat modeling, OWASP / MASVS review, dependency audit, full codebase audit (read-only) |
| `qa-engineer` | sonnet | Runs tests, checks acceptance criteria and cross-module contracts; browser checks on the lightest engine that fits — Lightpanda (headless), Playwright Chromium headless shell / WebKit (visual, PWA), Claude in Chrome (interactive, last fallback) |

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
- `_workspace/`: specs, designs, task board, review and QA reports. Add `_workspace/` and `_workspace_*/` to the project's `.gitignore`.

The final review phase uses the Workflow tool. Invoking the `dev-team` skill counts as consent; it stays small (≤ 3 reviewers + verifiers) unless you ask for a thorough review.

### Resource budget
Parallel agents are cheap; the test runners and builds they start are not. The profile sets the budget, and you can edit it:
- `max_agents` (default 4): agents running at once, including the final-review workflow; extra work queues.
- `heavy_workers` (default CPU threads ÷ 4): worker cap written into every heavy test/build command.
- Heavy commands go through `.claude/team/run-heavy.sh`, which lets only one run at a time on the machine (`flock`, with a `mkdir` lock fallback on macOS) under `nice`. `AI_DEV_TEAM_LOCK_WAIT` sets the maximum wait in seconds (default 1800).

Reviewers read the implementer's test output instead of rerunning it, per-task QA runs in parallel with review, and the full suite runs once at sign-off.

## Conventions

- All files the team writes (code, comments, specs, commit messages) are in English. Replies to the user follow the user's language.
- Phone screens (mobile web and app) waste no space and never overflow: adjacent buttons and short fields share a row when they fit, icon/text rows leave no dead space, every text element has a truncate / clamp / wrap rule checked with worst-case strings (`skills/pwa-headless-ui/references/compact-layout.md`).
- Query count never grows with row count: no N+1 queries or per-row requests, proven by query-count tests (`skills/code-review-checklist/references/query-performance.md`).
- Rules are enforced per task: the task board lists the rule packs each task must follow, the implementer reports one row of evidence per rule, reviewers and QA re-check them, and the leader only closes a task when every rule is confirmed (`skills/dev-team/references/rule-packs.md`).
- No commits unless you ask; commit messages are imperative English with no AI attribution.

## Optional companions

The plugin installs nothing besides itself. When one of these is already installed in the session, the agent uses it; when it is not, the agent works from the plugin's own skills.

| Companion | Used by | For |
|---|---|---|
| `superpowers` | developer | `systematic-debugging` on hard bugs |
| `ui-ux-pro-max` | ui-ux-designer | palettes, font pairings, stack-specific UX data |

### Third-party material
The full-audit procedure and attack-class catalog in `skills/security-review-checklist/references/` are condensed and adapted from Cloudflare's [`security-audit`](https://github.com/cloudflare/security-audit-skill) skill (MIT) — see `THIRD-PARTY-NOTICES.md`.

## Structure

```
.claude-plugin/plugin.json       plugin manifest
.claude-plugin/marketplace.json  single-plugin marketplace (mvanvu)
.claude-plugin/icon.png          plugin icon (source: scripts/icon-source.svg)
agents/                          8 agent definitions
skills/dev-team/                 orchestrator
skills/<role-skill>/             per-role procedures (some have references/, e.g. project-profiling/references/run-heavy.sh)
scripts/check-plugin.py          repo consistency check (cross-references, rule packs, version)
```

Validate after changes: `python3 scripts/check-plugin.py`, `claude plugin validate .` and `claude --plugin-dir . plugin details ai-dev-team`.

## License

MIT — see [LICENSE](LICENSE).
