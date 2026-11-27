# Monitor checks (pack `MON`)

How the in-session monitor watches a dev-team run and turns what it sees into fixes for this run and changes to the plugin. Used by the `ai-dev-team:monitor` agent and by the leader when monitoring is on.

## Contents
1. Scan
2. Findings
3. Plugin changes
4. Checks

## 1. Scan
- Input: `$TEAM_BIN/monitor-scan.py <repo>` — the leader's and agents' transcript lines since the last scan, plus `## Flags`. Read also the board (`$TEAM_WS/02_tasks.md`, notes included), `$TEAM_WS/decisions.md` entries added since the last scan, and `$TEAM_STATE/user-rules.md`.
- Judge against the rules of the plugin source when `plugin_src` is set (that is the text a change edits), else of the installed plugin (`$TEAM_BIN/../../`): `dev-team/SKILL.md`, `dev-team/references/rule-packs.md` (§3 `BASE`, §8 verdict gate), `dev-team/references/resource-budget.md` and the packs the board's `Rules` column names. Open a reference only for the behaviour a line shows; never read the whole plugin.
- Look for: a rule the leader or an agent broke; a stall (an agent silent past the watchdog limit, a ready task left waiting without a reason, a question that blocks nothing); a wasted cost (whole suites per task, repeated builds, one-command turns, opus where the table gives sonnet); a decision taken that belongs to the user; and a gap — a behaviour that went wrong although every rule was followed.
- One flag in `## Flags` is a lead, not a finding: open the lines around it and confirm.

## 2. Findings
Each finding in the report: the transcript time and actor, what happened (quoted line), the rule it breaks (rule ID or `SKILL.md` section) or `gap`, and its class:
- `run-fix` — the leader corrects this run now (re-open a task, re-brief an agent, revert a decision taken alone); the action is written as one instruction the leader can follow.
- `plugin` — a rule is missing, unclear or not enforced, so the same thing will happen in other runs. Only a `plugin` finding becomes a plugin change, and only after the apply mode confirms it (§3).
- `note` — worth knowing, no action.

## 3. Plugin changes
Apply mode (opus) takes the scan's `plugin` findings and, for each one it still confirms on the transcript:
- Reads the plugin source's `CLAUDE.md` and follows its rules for working on the plugin: files in English, one numbered check per new rule in one reference file, rule IDs only appended, packs registered in `rule-packs.md`, references by pointer instead of restating text.
- Names no project, product, repository, customer, tool target or file name of the watched run anywhere — rules, examples, change log; it describes what happened in generic terms ("a monitored run", "a client API task").
- Prefers enforcing (a guard hook pattern, a `rule-checks.sh` check, a verdict-gate item) over another sentence when the rule already existed and was broken anyway.
- Works only in its own worktree: `$TEAM_BIN/monitor-integrate.sh start <plugin_src>` prints the path; edit files there with the Edit tool; add one change log row at the end of the table in `CLAUDE.md` (date, the working version — the version in `.claude-plugin/plugin.json` plus one patch when that version is already pushed, else the same — change, target, reason); never bump `plugin.json` and never push.
- Lands it with `$TEAM_BIN/monitor-integrate.sh land <worktree> "<imperative English message>"` (runs the three plugin checks under the machine-wide lock); exit 3 → fix the checks and run `land` again; exit 4 or 5 → report the branch or worktree it left, do not retry by hand.
- Without `plugin_src` (`none`), writes the proposed change instead to `~/.local/state/ai-dev-team/proposals/<YYYYMMDD-HHMM>.md` (finding, proposed text, target file) for a later plugin session.

## 4. Checks
1. The monitor reads the run only through `monitor-scan.py` and the team files; it never edits project files, briefs agents, messages the user or another session, or stops processes — it reports to the leader only.
2. A scan reads only what is new since the last scan (the cursor of `monitor-scan.py`); a full re-read happens only when the cursor is missing.
3. Every finding quotes the transcript line it rests on and names a rule ID, a `SKILL.md` section or `gap`.
4. A `plugin` finding becomes a plugin change only after the apply-mode agent confirmed it on the transcript.
5. Plugin changes are made only in a `monitor-integrate.sh` worktree, landed only by `monitor-integrate.sh land`, never bump the version and never push.
6. Plugin text names no project, product, repository or file of the watched run.
7. The leader applies every `run-fix` finding in this run, or writes in the board notes why not, before its next spawn.
8. After a landed plugin change, the leader applies the new rule by hand in this run (the session runs the installed plugin, which a local commit does not change) and tells the user in one line: the commit and the rule.
9. The monitor is spawned only while `monitor: on` is in `$TEAM_STATE/local.md`; `off` stops a running monitor and arms no new scan.
