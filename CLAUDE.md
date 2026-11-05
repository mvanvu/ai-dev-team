# CLAUDE.md

This repository is the source of the `ai-dev-team` Claude Code plugin (marketplace `mvanvu`): 9 agents in `agents/`, skills in `skills/`, orchestrator `skills/dev-team/`. See README.md.

## Working on the plugin

- All files are written in English; replies to the user are in Vietnamese.
- Agents and skills are namespaced as `ai-dev-team:<name>` at runtime. When adding a new agent or skill, reference it with the prefix wherever it is invoked (`subagent_type`, workflow `agentType`, "Follow the `ai-dev-team:<skill>` skill").
- New agent → also update the team table, routing and build loop in `skills/dev-team/SKILL.md`, the README agent table, and the change log below.
- After any change run `claude plugin validate .` and `claude --plugin-dir . plugin details ai-dev-team`. Bump `version` in `.claude-plugin/plugin.json` before releasing.
- Use `harness:harness` to extend the team structure and `harness:evolve` to fold run feedback back into agents and skills.

## Change log
| Date | Change | Target | Reason |
| --- | --- | --- | --- |
| 2026-11-05 | Initial Harness v2 setup | all | - |
| 2026-11-05 | Added ui-ux-designer and security-auditor agents | agents, dev-team | User requested security and web/mobile design roles |
| 2026-11-05 | Added pwa-frontend-engineer agent + pwa-headless-ui skill; frontend tasks now owned by it, developer scoped to non-UI | agents, skills, dev-team, technical-design | User requested a Vue/React TS mobile-first PWA specialist with headless core components, swappable templates and Capacitor wrapping |
| 2026-11-05 | Converted to plugin layout (`ai-dev-team` v1.0.0, marketplace `mvanvu`); namespaced agent/skill invocations | all | Distribute the team as an installable plugin |
| 2026-11-05 | v1.1.0: native-feel interaction stack for pwa-frontend-engineer (Motion, View Transitions, VueUse, Sonner, TanStack Virtual/Query, Capacitor Haptics), motion tokens in the template contract, designer specs motion/gestures | pwa-frontend-engineer, ui-ux-designer, pwa-headless-ui | User requested PWA interactions as close to native as possible |
