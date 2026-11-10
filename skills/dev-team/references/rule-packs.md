# Rule packs and compliance reports

Rules are followed when two things are true: the agent doing the work was handed exactly the rules that apply to its task, and it has to show evidence for each one. This file is the single index of the team's rule packs and the report format every role uses.

## Contents
1. How it works
2. Rule packs
3. `BASE` — rules for every task
4. `TOOL` — greenfield toolchain
5. Assigning packs to tasks (architect)
6. Compliance report (implementer)
7. Rule check (reviewers, QA, design QA)
8. Leader gates
9. Automated checks

## 1. How it works
- A **rule pack** is a numbered list of checks kept in one reference file. A **rule ID** is the pack ID plus the item number in that list: `COMPACT-3` is item 3 of the checks in `compact-layout.md` §7.
- The architect writes the packs that apply to each task in the `Rules` column of the task board.
- The leader copies those packs, with their must-read files, into the brief of the implementer and of every reviewer and QA agent for that task.
- The implementer reports one row per rule ID with evidence. Reviewers and QA re-check the rules they can observe and report one row per rule ID too.
- The leader accepts a task only when every rule ID is `pass` (or a justified `n-a`) from the implementer and confirmed by at least one other role.

## 2. Rule packs
Paths are relative to the plugin's `skills/` directory. "Verified by" names the roles that must return a rule check for the pack; other roles may still raise findings against it.

| Pack | Applies when the task… | Must read | Numbered checks | Verified by |
|---|---|---|---|---|
| `BASE` | always | this file §3 | §3 | code-reviewer |
| `TOOL` | scaffolds a new project, app or package | `technical-design/SKILL.md` → Latest-stable toolchain | this file §4 | code-reviewer |
| `ARCH` | adds or changes web frontend code on the headless core-component architecture | `pwa-headless-ui/SKILL.md`, `pwa-headless-ui/references/architecture.md` | `architecture.md` §9 | code-reviewer |
| `COMPACT` | builds or changes a phone-sized screen (mobile web, PWA, Capacitor, Flutter, native) | `pwa-headless-ui/references/compact-layout.md` | §7 | qa-engineer, ui-ux-designer |
| `LIST` | builds or changes a paginated resource list or a record picker | `pwa-headless-ui/references/list-page.md` | §9 | code-reviewer, qa-engineer |
| `LIFE` | creates or changes a CRUD entity (active flag, trash, restore, purge, bulk actions) — backend and UI tasks alike | `technical-design/references/record-lifecycle.md` | §10 | code-reviewer, qa-engineer |
| `QUERY` | reads or writes the database for a list, a detail with children, an export, a bulk action, a background job or a GraphQL resolver — or a client screen that loads data per row | `code-review-checklist/references/query-performance.md` | §4 | code-reviewer, qa-engineer |
| `CONN` | touches a mobile app or installed PWA that uses online data | `pwa-headless-ui/references/connectivity.md` | §10 | qa-engineer |
| `FEEL` | touches navigation, page transitions, gestures, sheets/overlays or long lists | `pwa-headless-ui/references/native-feel.md` | §11 | code-reviewer, qa-engineer |
| `PWA` | touches the manifest, service worker, caching, offline fallback or update flow | `pwa-headless-ui/references/pwa.md` | Checks section | qa-engineer |
| `CAP` | touches Capacitor config, plugins or the native shell (always together with `CAPFEEL`) | `pwa-headless-ui/references/capacitor.md` | Checks section | qa-engineer |
| `CAPFEEL` | same as `CAP` | `pwa-headless-ui/references/capacitor-native-feel.md` | §10 | qa-engineer |
| `ABUSE` | adds or changes a public or unauthenticated endpoint, a list/search/export endpoint, or an AI/agent feature | `security-review-checklist/references/automated-abuse.md` | sections §2–§9 (`ABUSE-3` = §3) | security-auditor |

Requirements that come from the feature itself keep their own IDs and are reported the same way: acceptance criteria (`AC-n` from the spec) and threat-model requirements (`SEC-n` from `_workspace/02_security_threat-model.md`).

Used without a task board (a standalone review, QA or frontend task), each role picks the packs itself from the "Applies when" column.

A check that names a tool or environment the task cannot use (a device, Xcode, an emulator) is reported `n-a` with the reason, never silently dropped.

## 3. `BASE` — rules for every task
1. **Scope** — only the task's files and behavior change; unrelated problems are written in the notes, not fixed.
2. **Contracts** — request/response shapes, types, nullability and error codes match the design exactly; a wrong contract is reported `BLOCKED`, not changed.
3. **Tests first** — each acceptance behavior the task touches has a test that was seen failing before the code existed, or the notes say why a test is impractical and how it was verified instead.
4. **Evidence** — the notes hold the trimmed real output of the final related-test, lint and type-check/build runs.
5. **Heavy commands** — test runs, builds and e2e went through `.claude/team/run-heavy.sh`; no watcher, dev server, emulator or browser is left running.
6. **Language** — code, comments, specs and notes are in English; comments explain why and never describe bug history.
7. **Commits** — none unless the user asked; messages are English, imperative, without AI attribution.
8. **Dependencies** — no new dependency without a stated reason (maintained, size/cost acceptable, no existing utility does it).
9. **Security defaults** — input validated at the boundary, parameterized queries, an authorization check on every entry point, no secrets in code or logs.

## 4. `TOOL` — greenfield toolchain
1. Installed versions equal the design's `## Toolchain` table; anything not in the table was looked up at install time, not recalled.
2. No beta, RC, canary or nightly; runtimes on the latest LTS where one exists.
3. Current config formats and official scaffolders; lockfile committed.
4. Any tool held below latest stable has its reason in the notes.

## 5. Assigning packs to tasks (architect)
For every task, walk the "Applies when" column and list each matching pack in the task board's `Rules` column (`BASE` is implied and not written). Assign by what the task touches, not only by its tags — a backend task for a CRUD entity gets `LIFE`, a list endpoint gets `ABUSE` and `QUERY`. When unsure whether a pack applies, assign it: an `n-a` row costs less than a missed rule.

## 6. Compliance report (implementer)
Before coding, read every must-read file of the assigned packs. Before reporting `DONE`, add this section to the task notes, one row per rule ID of every assigned pack plus `BASE`:

```markdown
## Rule compliance
| Rule | Status | Evidence |
|---|---|---|
| BASE-1 | pass | diff touches only src/features/orders/** |
| COMPACT-2 | pass | overflow script at 360×800: [] — _workspace/qa-artifacts/T3-360.png |
| COMPACT-4 | n-a | screen has no icon rows |
| LIST-3 | pass | OrderPicker.spec.ts "keeps selection across pages" |
```

- Status is `pass`, `n-a` or `fail`.
- `pass` needs evidence someone else can open: a test name, `file:line`, a command with its output, or an artifact path. "Checked" or "done" is not evidence.
- `n-a` needs the reason the rule cannot apply to this task.
- `fail` means the task is not done: fix it, or report `BLOCKED T{id}` with the rule ID and the reason.
- Never mark a rule `pass` without having checked it in this task; an unchecked rule is reported as `fail`.
- A rule listed in §9 is proven by its script: the evidence is the command and its output, nothing else.

## 7. Rule check (reviewers, QA, design QA)
Each verifier adds this table to its verdict, covering the rule IDs of the packs it is named for in §2 (and any other rule it happened to check):

```markdown
## Rule check T{id}
| Rule | Result | Evidence |
|---|---|---|
| ARCH-1 | pass | lint output in notes; grep of src/features finds no reka-ui import |
| LIST-4 | fail | filter `status` stored in localStorage — src/features/orders/useOrders.ts:41 |
| COMPACT-3 | n-o | needs a rendered page |
```

- Result is `pass`, `fail` or `n-o` (not observable by this role — say what it would take).
- Check the rule itself, not the implementer's claim: open the evidence, then look at the code or the running app.
- A `fail` is also written as a normal finding or defect in the role's own format, with the rule ID in the title; severity follows the role's checklist (a rule that protects data, access or a contract is at least `major` / `high`).
- An implementer `pass` whose evidence does not exist or does not show the rule is a `fail` plus a `major` finding ("unsupported compliance claim").
- A missing `## Rule compliance` section in the notes is a `major` finding; do not review the rest as if it were there.

## 8. Leader gates
- **Brief**: every implementer, reviewer and QA brief contains the task's `Rules` cell and the must-read file list for those packs (resolved from §2), plus "report per `ai-dev-team:dev-team` → `references/rule-packs.md` §6" (implementer) or "§7" (verifier).
- **DONE gate**: open the notes. No `## Rule compliance` section, a missing rule ID, a `pass` without evidence or an `n-a` without a reason → send the task back with the list of missing rows. This does not count as a fix round.
- **Verdict gate**: a verdict without a `## Rule check` table for the packs that role verifies → ask that agent for it before accepting the verdict.
- **Coverage**: a task is `done` when every assigned rule ID is `pass` or `n-a` from the implementer **and** `pass` from at least one verifier (an accepted `n-a` needs a verifier that does not contradict it). Rule IDs every verifier marked `n-o` are listed as `unverified` in the task board notes and in the Phase 6 report.
- **Ledger**: append every verifier `fail` to `_workspace/rule-violations.md` (`T{id} | rule ID | role that found it | fixed in round n`). A rule that fails in two tasks goes into the brief of every later task as a one-line warning, and into the Phase 6 report.

## 9. Automated checks
Rules a script can decide are decided by the script, not by reading. `repo-scout` installs both scripts in `.claude/team/` (missing → rerun Phase 1). Each prints `<RULE-ID> ok`, `<RULE-ID> n-a: <reason>` or one line per violation, and exits 1 on violations.

| Rule | Command | Run by |
|---|---|---|
| `ARCH-1` | `.claude/team/rule-checks.sh arch` | implementer, code-reviewer |
| `LIST-4` (list state in web storage) | `.claude/team/rule-checks.sh list-storage` — hits are candidates; confirm each | implementer, code-reviewer |
| `BASE-7` | `.claude/team/rule-checks.sh commits [base]` — only when commits were made | implementer, code-reviewer |
| `TOOL-2` | `.claude/team/rule-checks.sh prerelease` | implementer, code-reviewer |
| `COMPACT-1`, `COMPACT-2`, `COMPACT-7` | `.claude/team/run-heavy.sh node .claude/team/overflow-check.mjs --shots _workspace/qa-artifacts <url>...` on the screens the task touched, loaded with worst-case content | implementer (when the app can run), qa-engineer |
| `COMPACT-6` (Flutter) | `.claude/team/rule-checks.sh flutter-overflow <saved flutter test output>` | implementer, qa-engineer |

`.claude/team/rule-checks.sh all [base]` runs the first four. A script that cannot run here (exit 2 from `overflow-check.mjs`: Playwright not installed) leaves the rule to the manual check in its reference file; say so in the evidence.
