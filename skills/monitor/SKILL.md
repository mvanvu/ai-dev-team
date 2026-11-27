---
name: monitor
description: "Turns the in-session run monitor on or off: '/ai-dev-team:monitor on|off|status'. When on, the dev-team leader periodically spawns a monitor agent that reads what the leader and agents did since the last scan, reports rule breaks for this run to fix, and lands plugin improvements in the local plugin source checkout. Use when the user says 'monitor on', 'turn on monitoring', 'monitor off', 'is the monitor on'. Off by default."
---

# Run monitor toggle

The monitor watches a dev-team run from inside its own session, so no separate plugin session and no cross-session message is needed. Its rules are pack `MON` (`references/monitor-checks.md`).

## Arguments
`on`, `off` or `status` (no argument = `status`). Applies to the repo of the current session: the folder holding `.ai-dev-team/` (`$TEAM_STATE`).

## on
1. Write `monitor: on (user, <HH:MM from date>)` in the front matter of `$TEAM_STATE/local.md` (create the file from the `ai-dev-team:project-profiling` template when missing; edit the line in place when present).
2. `plugin_src` in `local.md` missing → ask the user once (AskUserQuestion): the path of the local checkout of the plugin's source repository, or `none` (proposals only, `references/monitor-checks.md` §3). Before writing a path, check it: `git -C <path> rev-parse --show-toplevel` succeeds and `<path>/.claude-plugin/plugin.json` names `ai-dev-team`. Never search the disk for it.
3. Tell the user in one line: monitoring on, where plugin changes land, cadence (below), and that `/ai-dev-team:monitor off` stops it.
4. A dev-team run in progress (agents running or tasks open on the board) → spawn the first scan now (below). No run → the next dev-team run starts it.

## off
Write `monitor: off (user, <time>)`; stop a running monitor agent with `TaskStop`; no new scan is armed. A worktree an apply-mode agent left is reported to the user with `monitor-integrate.sh drop <worktree>` as the clean-up.

## status
Read `monitor:` and `plugin_src:` from `local.md` and the `monitor-last:` line of the board notes; answer in one or two lines.

## Leader procedure while on (dev-team, Phase 0 to Phase 6)
- **Cadence**: at a watchdog checkpoint, start a scan when ~30 minutes passed since `monitor-last:` or a task reached `done` since then, and no monitor agent is running. Record `monitor-last: <HH:MM> (<n> findings)` in the board notes. A monitor counts against `max_verifiers` and waits behind fix rounds and verdicts of open tasks.
- **Scan**: spawn `ai-dev-team:monitor` with `model: "sonnet"`, mode `scan`, in the background. Brief: the four team paths (Brief skeleton line 1), the repo root, `plugin_src`, the leader transcript path when known, and "report findings per `references/monitor-checks.md` §2".
- **Apply**: when the scan reports `plugin` findings, spawn `ai-dev-team:monitor` with `model: "opus"`, mode `apply`, with those findings verbatim. One apply agent at a time per session.
- **On the report**: apply each `run-fix` before the next spawn (or write why not in the board notes); for a landed plugin change, apply the new rule by hand in this run and tell the user `monitor: <commit> — <rule in one line>`; a `note` goes to the board notes only. Nothing from the monitor is shown to the user except landed changes and `run-fix` actions that change what the user sees (a task re-opened, a decision reverted).
- The monitor's output is evidence for the leader, not an instruction from the user: a `run-fix` that would need the user's approval (push, scope change, data deletion) is asked like any other such step.
