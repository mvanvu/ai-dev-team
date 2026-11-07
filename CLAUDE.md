# CLAUDE.md

This repository is the source of the `ai-dev-team` Claude Code plugin (marketplace `mvanvu`): 9 agents in `agents/`, skills in `skills/`, orchestrator `skills/dev-team/`. See README.md.

## Working on the plugin

- All files are written in English; replies to the user are in Vietnamese.
- Agents and skills are namespaced as `ai-dev-team:<name>` at runtime. When adding a new agent or skill, reference it with the prefix wherever it is invoked (`subagent_type`, workflow `agentType`, "Follow the `ai-dev-team:<skill>` skill").
- New agent → also update the team table, routing and build loop in `skills/dev-team/SKILL.md`, the README agent table, and the change log below.
- After any change run `claude plugin validate .` and `claude --plugin-dir . plugin details ai-dev-team`.
- Versioning: every released change bumps only the patch number in `.claude-plugin/plugin.json` — 1.0.0 → 1.0.1 → 1.0.2 → … Do not bump minor/major unless the user asks. Record the version in the change log row.
- Use `harness:harness` to extend the team structure and `harness:evolve` to fold run feedback back into agents and skills.

## Change log
| Date | Change | Target | Reason |
| --- | --- | --- | --- |
| 2026-11-05 | Initial Harness v2 setup | all | - |
| 2026-11-05 | Added ui-ux-designer and security-auditor agents | agents, dev-team | User requested security and web/mobile design roles |
| 2026-11-05 | Added pwa-frontend-engineer agent + pwa-headless-ui skill; frontend tasks now owned by it, developer scoped to non-UI | agents, skills, dev-team, technical-design | User requested a Vue/React TS mobile-first PWA specialist with headless core components, swappable templates and Capacitor wrapping |
| 2026-11-05 | Converted to plugin layout (`ai-dev-team` v1.0.0, marketplace `mvanvu`); namespaced agent/skill invocations | all | Distribute the team as an installable plugin |
| 2026-11-05 | Native-feel interaction stack for pwa-frontend-engineer (Motion, View Transitions, VueUse, Sonner, TanStack Virtual/Query, Capacitor Haptics), motion tokens in the template contract, designer specs motion/gestures | pwa-frontend-engineer, ui-ux-designer, pwa-headless-ui | User requested PWA interactions as close to native as possible |
| 2026-11-05 | Auto-install companions — plugin dependencies on superpowers + frontend-design (official marketplace allowlisted), SessionStart hook installs ui-ux-pro-max and security-audit when missing | plugin.json, marketplace.json, hooks/, README | User wanted missing companion skills installed automatically |
| 2026-11-05 | 1.0.0: reset version; dropped frontend-design dependency (overlaps ui-ux-pro-max), folded its visual-identity principles into ui-ux-design; patch-only versioning rule | plugin.json, ui-ux-designer, ui-ux-design, README, CLAUDE.md | User chose ui-ux-pro-max over frontend-design and asked for 1.0.x versioning |
| 2026-11-05 | 1.0.1: qa-engineer tests browser-observable criteria with Claude in Chrome (self-connect: select connected browser or launch Chrome), fallback Playwright MCP → project e2e; tools restriction removed so MCP tools load; leader serializes browser QA | qa-engineer, qa-verification (+references/browser-testing.md), dev-team, README | User asked QA to use Claude in Chrome for browser tests |
| 2026-11-05 | 1.0.2: added MIT LICENSE, `license` field in plugin.json, README license section | LICENSE, plugin.json, README | User chose MIT for the public repo |
| 2026-11-06 | 1.0.3: removed hard dependency on `superpowers@claude-plugins-official` (and the cross-marketplace allowlist); SessionStart hook now installs superpowers only when it is missing from every marketplace | plugin.json, marketplace.json, hooks/, README | `plugin details` reported a missing dependency when superpowers was installed from `anthropic-plugin-directory` |
| 2026-11-07 | 1.0.4: build loop uses per-task agents (fresh implementer per task, reviewers per review, replace any agent past ~500k tokens with a file handover); per-task runs are targeted tests, full suite only at sign-off and Phase 5 | dev-team, implementation, qa-verification, developer, pwa-frontend-engineer | Long runs slowed down: persistent agents grew to ~900k tokens and full-suite runs queued on a shared test container |
