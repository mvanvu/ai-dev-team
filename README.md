# ai-dev-team — AI software development team for Claude Code

A Claude Code plugin that adds a 3-agent software team (plus an optional run monitor) and an orchestrator skill. It takes work from a raw request to reviewed, tested code: profile → spec → plan → build / review / QC loop → verified final review. It works with any stack, detected automatically, and carries rules for mobile-first PWAs (Vue 3 / React + TypeScript, headless core components, swappable templates) and mobile apps — the user picks Flutter (recommended), Capacitor wrapping the PWA, or native Swift/Kotlin.

## Team

| Who | Model | Role |
|---|---|---|
| leader (the `dev-team` skill, in the main session) | session model | Profiles the repo, plans with the user (with `superpowers` brainstorming + writing-plans when installed), owns the task board, briefs agents, merges feedback, reports |
| `developer` | opus (sonnet for small changes and layout fixes; fable only under the Fable policy you pick once per run (auto with a report / ask each time / never) — for an escalation after 3 failed fix rounds, hard-to-reproduce bugs, complex high-risk tasks, audits and large plans) | Builds every task test-first — one side per task: server (schema, APIs with contract tests, jobs, infra) or client (web, PWA, Flutter / Capacitor / native, against the server contract of a finished task); writes the UI spec before screens are built; applies fixes |
| `reviewer` | opus (sonnet for low-risk task reviews) | One read-only pass per task over code quality, security and UI conformance (design QA); threat models, full audits, final-review dimensions and adversarial verification |
| `qc` | sonnet | Acceptance criteria and cross-module contracts with evidence; browser checks on the lightest engine that fits (Lightpanda, Playwright headless shell / WebKit, Claude in Chrome as last fallback), Flutter widget/golden tests; feature sign-off |
| `monitor` | sonnet scan, opus apply | Off by default; `/ai-dev-team:monitor on` in a project session turns it on. Every ~30 minutes or after a task, it reads what the leader and agents did since its last scan, reports rule breaks the leader fixes in this run, and lands plugin improvements in your local plugin checkout (`plugin_src`: own worktree, machine-wide lock, plugin checks, no version bump, no push) — no separate monitoring session or cross-session message needed |

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

The team keeps its state in one repo folder, `.ai-dev-team/`, so specs, plans and decisions travel with the repo to every machine (details: `skills/dev-team/references/team-paths.md`):
- `.ai-dev-team/project-profile.md`: detected stack, verified commands and the resource budget, kept across runs.
- `.ai-dev-team/workspace/`: spec, plan, UI spec, threat model, task board, task notes, QC reports and mockups of the current run; finished runs are archived beside it. Commit it with the work; screenshots, contact sheets and recordings are ignored by `.ai-dev-team/.gitignore`.
- `~/.local/state/ai-dev-team/qa-tools/`: a Playwright install shared by all projects on this machine, used only when a project has none.
- Scripts run straight from the installed plugin (`skills/project-profiling/references/`), so a plugin update takes effect without touching any repo: `run-heavy.sh` runs heavy commands (tests, builds, audits) a few at a time at low CPU priority; `rule-checks.sh` and `overflow-check.mjs` decide the rules a machine can check (`rule-checks.sh task-base` / `task-diff` give each task its own diff); `device-preview.mjs` puts the app on your phone with a QR code; `golden-diff.py` compares changed golden images with their base in contact sheets; `plugin-src.sh` finds the plugin source and compares versions; `monitor-scan.py` and `monitor-integrate.sh` serve the run monitor; `overflow-check.mjs --touch 44 --empty 24 --scrollbars` also catches small tap targets, wasted space (empty bands, spacer blocks) and default browser scrollbars.
- Each run's Phase 0 compares the installed plugin version with your local plugin source and its upstream (or the public repository's `plugin.json`) and, when an update is available and no agent runs, downloads it itself (`plugin-src.sh update`) and tells you to run `/reload-plugins` or restart, since the running session keeps the loaded version until then. It also asks once per machine whether to turn on Claude Code's own auto-update for the plugin's marketplace (third-party marketplaces have it off, and a plugin cannot turn it on at install); you can also turn it on yourself in `/plugin` → Marketplaces. Writing `off` in `~/.local/state/ai-dev-team/plugin-update` stops both.

The only hook is the **leader guard** (`hooks/leader-guard.py`): during a dev-team run it stops the main session from editing project files itself (also in another git repository the run changes) or staging whole folders or the whole `git status` list, or spawning a team agent without an explicit `model`, or changing its shell directory with `cd` outside a subshell, or adding a board or decision note line whose time is ahead of the clock (note times come from `date`) (it finds the run from the paths a call names when the session started in a folder that was later renamed), so code always goes through a developer and a review; for everyone, agents included, it blocks commands that discard work on the shared tree (`git checkout --`, `restore`, `stash`, `--autostash`, `reset --hard`), kill processes by name or detach them (`nohup`, a trailing `&`, `( … & )`, `setsid`, `disown`) or wait on them in a `sleep` loop, it refuses the end of a leader turn while the session's background agents run and no watchdog checkpoint is armed, and it stops agents from editing files through a `python3 -` heredoc that re-types text (`COST-8`) or from adding a third browser script to one task's `qa-artifacts/` folder within 90 minutes, and it blocks shell writes into `.ai-dev-team/` that would still run a backtick as a command, and the monitor agent's writes to project files; `leader_guard: off` in `.ai-dev-team/local.md` turns it off.

Projects used with an older version get their `.claude/team/`, `_workspace/` or `~/.local/state/ai-dev-team/projects/<project>/` moved into `.ai-dev-team/` on the next run.

### How a run works
- **Phase 0–1**: the leader checks the team folder, fills missing profile fields, starts the app stack in the background (`app_start`) and profiles the repo. A stopped stack never holds a task back: work that needs no running app starts at once.
- **Phase 2–3**: spec and plan with you (superpowers brainstorming / writing-plans when installed). Ambiguous words are asked as concrete options; a rewrite in another stack first lists every behaviour of the old one.
- **Phase 4**: the build loop. Each task gets a fresh developer, its own reviewer and qc (in parallel), on the model the role table names; a task is `done` only with its own `QC_PASS` — the leader never folds a task's qc into later tasks. Ready tasks that touch disjoint files and environments run side by side; shared integration points (router, manifest, language files, shared stylesheets) get one setup task or are merged by the leader. A verdict gate re-checks every review: severity against fixed anchors, the whole diff read, every UI image opened. Before reporting done, the developer runs the project's fast `guard` command; a defect class that repeats becomes an automated check.
- **Phase 5**: the final review runs when a feature has 4 or more tasks or anything security-related (always for review-only requests). It uses the Workflow tool while you are present (≤ 3 reviewers + verifiers unless you ask for more) and plain agents when you are away, so no permission prompt can stall it.
- **Routes**: small changes and layout complaints take a light tier (one developer, one reviewer, no final review) — never for auth, permissions, payments, deletion or schema; bugs are reproduced first; an interrupted run resumes from the board.

### Talking to the leader
- Every progress message opens with one board line (`done · running · waiting with reasons`), and a short update comes about every 5 minutes while agents run; nothing waits without a written reason.
- Questions block only when nothing else can run. Otherwise the leader asks in plain text and keeps working. A tool call cut off by your new message is treated as an interruption, not a refusal.
- Say you are leaving and the leader asks everything up front, settles the UI design first, then decides with the recommended options and logs them in `decisions.md`; commits, pushes and changes to other repositories wait for you.
- A new decision that makes running or queued tasks obsolete cancels or trims them. Small requests in the same area arriving together become one task. A queued task that blocks what you are trying gets offered to move up.
- After about 5 finished tasks without commits, the leader asks once whether to commit locally, one commit per task (never a push without you).

### UI design
Designs are settled with cheap steps before any mockup is coded (`skills/ui-ux-design/references/design-gate.md`):
1. **References first**: a gallery of real screenshots the designer studies, or your own references — the leader asks how to use them (mood only, follow one, or listed elements) and never splices two together or copies one.
2. **Overview boards**: three static boards (palette, type, one phone frame, one card, the main button), built in parallel in minutes and different in shape language and layout, not only colour; a 3×3 calibration matrix pins vague words like "modern" or "old" to a position.
3. **HTML mockup** of the approved direction only, with a page comparing it to the references; tone and colour changes are token edits, not a new round.
4. After two rejected rounds nothing new is drawn until a rejection review, the matrix and the references are done; after three, a fresh designer studies market-grade examples of the product type and designs from that study — you approve the result, you never have to pick among templates.

Mockups pass design QA (every screen × width × theme opened) before you see them; approved ones are kept in the repo. Designs favour ease of use over looks and avoid the generated look.

### Research, reuse and phone preview
- Before planning a new feature or product, the leader asks whether to research it first. On a yes, short time-boxed agents look at what the project already has and at comparable products and practices on the web, and you pick from 3–5 sourced options (core / expected / optional) before the spec questions (`skills/dev-team/references/request-research.md`).
- The project keeps a capability index (`.ai-dev-team/capabilities.md`); developers reuse what exists before building anything new, and reviewers flag duplicates.
- Say "QR code" (or accept the offer after a mobile task) to open the app on your phone over the local Wi-Fi: a web build or dev server in the phone's browser, Android wireless debugging paired by QR for `flutter run` / Capacitor with hot reload, or a QR to download the APK. Nothing extra is installed on the phone.

### Run monitor
Off by default. In a project session, `/ai-dev-team:monitor on` turns it on, `off` stops it and `status` (or no argument) shows it; the setting is the `monitor:` line in `.ai-dev-team/local.md`.
- The first `on` finds `plugin_src` (your local checkout of this plugin's source) by itself: an earlier choice in `local.md`, the one remembered for this machine (`~/.local/state/ai-dev-team/plugin-src`), the plugin itself when you run it with `--plugin-dir`, `../ai-dev-team` next to the project, or else a clone of the public repository into `~/.local/state/ai-dev-team/source/ai-dev-team`. The result is remembered for every project on the machine; it asks only when all of these fail. `/ai-dev-team:monitor on <path>` or `on none` sets it by hand.
- `status` and the run's final report show unpushed commits in `plugin_src`, so changes landed in a clone are not forgotten.
- While on, the leader spawns a sonnet `monitor` scan every ~30 minutes or after a task reaches `done`. It reads what the leader and agents did since the last scan (`monitor-scan.py`, with a cursor) and reports `run-fix` findings the leader applies in this run, `plugin` findings and notes.
- `plugin` findings go to an opus apply agent, which lands the change in `plugin_src` through `monitor-integrate.sh` (own worktree, machine-wide lock, the plugin checks, fast-forward only, no version bump, no push); the leader applies the new rule by hand in the running session and reports `monitor: <commit> — <rule>`. With `plugin_src: none` the change is written to `~/.local/state/ai-dev-team/proposals/` instead.
- Review the landed commits with `git log` in the plugin checkout before the next push; parallel monitors' change log rows merge cleanly (`merge=union` on `CLAUDE.md`).

### Resource budget
Parallel agents are cheap; the test runners and builds they start are not. The profile sets the budget, and you can edit it:
- `max_agents` (default 5): developers running at once; `max_verifiers` (default 4): reviewers, qc, research agents and the final-review workflow at once; extra work queues. Both are per leader session, not shared between sessions on one machine; only heavy commands share the machine-wide `heavy_slots`.
- `heavy_workers` (default CPU threads ÷ 4, kept per machine in the git-ignored `.ai-dev-team/local.md`): worker cap written into every heavy test/build command.
- `heavy_slots` (default CPU threads ÷ 8, at least 1, per machine in `local.md`): heavy commands running at once across every project on the machine. They go through `$TEAM_BIN/run-heavy.sh` (`flock` slots, one `mkdir` lock on macOS) under `nice`; `run-heavy.sh --status` shows what holds each slot. One test file, a small related run or lint of changed files runs directly, without queuing. `AI_DEV_TEAM_LOCK_WAIT` sets the maximum wait in seconds (default 1800); `AI_DEV_TEAM_TIMEOUT` stops a command that runs longer (default 1800, `0` = no limit), so a hung test runner cannot stall a run.

The reviewer reads the developer's test output instead of rerunning it, per-task QC runs in parallel with review, and the full suite runs once at sign-off. Developers run only the tests related to the files they changed (`vitest related`, mapped guards), once per task and once per fix round; tasks that share files or a built bundle never run at the same time on one working tree.

Heavy commands and UI checks follow two rule packs (`skills/dev-team/references/resource-budget.md`): `COST` for every task (each check once by the agent that owns it, browsers and runners queued by the wrapper, no `sleep`/`pgrep` polling, one sign-off qc with one full-suite run) and `SWEEP` for web screens (every changed screen at every width tier × every theme from the profile in one `overflow-check.mjs --sheet` run per build, one contact sheet per screen that the developer, reviewer and qc each look at, no second sweep of an unchanged build).

## Conventions

- All files the team writes (code, comments, specs, commit messages) are in English. Replies to the user follow the user's language.
- Phone screens (mobile web and app) waste no space and never overflow: adjacent buttons and short fields share a row when they fit, icon/text rows leave no dead space, every text element has a truncate / clamp / wrap rule checked with worst-case strings (`skills/pwa-headless-ui/references/compact-layout.md`).
- Default stack when the request names no technology: NestJS backend, PostgreSQL + Prisma, Redis for caching, Vue 3 + TypeScript frontend — proposed for approval, and only for parts the project does not already have (`skills/technical-design/SKILL.md`).
- Mobile lists support pull to refresh of the visible tab only, without triggering the browser reload or fighting tab swipes (`skills/pwa-headless-ui/references/pull-to-refresh.md`); app screens carry no redundant instruction text, and designs avoid the generated look (`skills/ui-ux-design/references/authentic-design.md`).
- Query count never grows with row count: no N+1 queries or per-row requests, proven by query-count tests (`skills/code-review-checklist/references/query-performance.md`).
- Rules are enforced per task: the task board lists the rule packs each task must follow, the developer reports one row of evidence per rule, the reviewer and qc re-check them, and the leader only closes a task when every rule is confirmed (`skills/dev-team/references/rule-packs.md`).
- No commits unless you ask; one commit per task, imperative English; AI attribution follows the project's own policy (its `CLAUDE.md` or settings), else your global instructions. Agents never change the git index; only the leader commits.
- Secrets never land in team files: command output with passwords, tokens or keys is redacted, and test logins are referenced by environment key name only.
- Environment values changed for a phone or LAN test are logged with their undo and reverted when the preview ends.

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
agents/                          4 agent definitions (developer, reviewer, qc, monitor)
skills/dev-team/                 orchestrator
skills/<role-skill>/             per-role procedures (some have references/, e.g. project-profiling/references/run-heavy.sh)
scripts/check-plugin.py          repo consistency check (cross-references, rule packs, version)
```

Validate after changes: `python3 scripts/check-plugin.py`, `claude plugin validate .` and `claude --plugin-dir . plugin details ai-dev-team`.

## License

MIT — see [LICENSE](LICENSE).
