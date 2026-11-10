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
| `security-auditor` | opus | Threat modeling, OWASP / MASVS review, dependency audit (read-only) |
| `qa-engineer` | sonnet | Runs tests, checks acceptance criteria and cross-module contracts; browser testing via Claude in Chrome (self-connects, Playwright fallback) |

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
- No commits unless you ask; commit messages are imperative English with no AI attribution.

## Companion plugins and skills (installed automatically)

| Companion | Used by | How it gets installed |
|---|---|---|
| `superpowers` (systematic debugging) | developer | SessionStart hook: `claude plugin install superpowers@claude-plugins-official`, skipped when superpowers is already installed from any marketplace |
| `ui-ux-pro-max` | ui-ux-designer | SessionStart hook: adds marketplace `nextlevelbuilder/ui-ux-pro-max-skill` and installs `ui-ux-pro-max@ui-ux-pro-max-skill` |
| `security-audit` | security-auditor | SessionStart hook: `npx skills add cloudflare/security-audit-skill -g -a claude-code -s security-audit -y` |

The hook only acts when an item is missing (as a plugin or as a skill in `~/.claude/skills` / `.claude/skills`), installs in the background without blocking the session, and the item is available from the next session. Failed attempts are retried after 24h; the log is at `~/.claude/ai-dev-team/companions.log`. Requires `claude` and `npx` on `PATH`. Set `AI_DEV_TEAM_NO_AUTO_INSTALL=1` to disable it. Agents still work without these companions.

## Structure

```
.claude-plugin/plugin.json       plugin manifest
.claude-plugin/marketplace.json  single-plugin marketplace (mvanvu)
agents/                          8 agent definitions
skills/dev-team/                 orchestrator
skills/<role-skill>/             per-role procedures (some have references/, e.g. project-profiling/references/run-heavy.sh)
hooks/                           SessionStart hook that installs missing companion skills
```

Validate after changes: `claude plugin validate .` and `claude --plugin-dir . plugin details ai-dev-team`.

## License

MIT — see [LICENSE](LICENSE).
