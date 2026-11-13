---
name: project-profiling
description: "Procedure for surveying a repo and writing $TEAM_STATE/project-profile.md (stack, verified test/lint/build/audit commands, code conventions, web/mobile UI presence). Used by the dev-team leader in Phase 1, or when asked to 'scan the project', 'update the project profile', or 'what stack does this project use'. Not for code review or design."
---

# Project profiling

The project profile is the team's shared source of truth: which test command the developer runs, what qc checks, which audit tool the reviewer uses. Errors here propagate to every later step, so record only what you verified.

## Procedure

1. **List stack marker files** (Glob at root and two levels down):
   `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `composer.json`, `pyproject.toml`, `requirements*.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle*`, `Gemfile`, `pubspec.yaml`, `*.csproj`, `Dockerfile`, `docker-compose*.yml`, `Makefile`, `.github/workflows/*`, `.gitlab-ci.yml`.
2. **Detect UI**: web (React/Vue/Svelte/Angular/Next/Nuxt, Twig/Blade templates), mobile (React Native, Flutter `pubspec.yaml`, `android/`, `ios/`, Swift/Kotlin). Record `ui: none | web | mobile | web+mobile`. Record `mobile_platform`: `flutter` (`pubspec.yaml`), `capacitor` (`capacitor.config.*`), `react-native`, `native` (Swift/Kotlin projects without Capacitor), else `none`.
   Also record frontend architecture facts: PWA (`vite-plugin-pwa`, `manifest.webmanifest`, service worker), Capacitor (`capacitor.config.*`, its `server.url`), headless library (`reka-ui`, `radix-ui`, `@radix-ui/*`, `react-aria-components`), and template packs (`src/templates/*`, active template selection).
3. **Find commands** in package.json `scripts`, `Makefile`, composer scripts, and CI config. CI config is usually the most trustworthy source because it actually runs.
4. **Run** each test/lint command (with a sensible timeout; heavy ones in the background through the wrapper, keeping only the trimmed result). Record `verified` / `failed: <key error>` / `not-run: <reason>`. No test runner, lint or type-check at all → record `tests: none` / `lint: none` / `typecheck: none` in the front matter, so rules that need them are `n-a` instead of failing every task.
4a. **Frontend architecture** for routing: record `frontend_arch: headless-core` only when the repo already uses the headless core-component layering (`src/ui/core`, template packs); otherwise `frontend_arch: <framework>-conventional` (e.g. `angular-conventional`, `blade-templates`). Developers follow the project's own conventions unless it is `headless-core` or a new frontend.
5. **Conventions**: read 3–5 representative files per kind (controller, service, component, test) to extract naming, layout, test framework and assertion style.
5a. **Capability index** — write `$TEAM_STATE/capabilities.md` when it is missing (committed with the team files): one line per reusable piece the project already has, grouped by kind — services and integrations, shared UI components and layouts, hooks and helpers, API endpoints by resource, scripts and make targets, test fixtures, factories and seeds — each as `` `path` — what it does `` (from the directory layout, exports and route lists; no deep reading). It is what developers check before building something new (`BASE-16`) and what the plan's reuse notes come from. Developers append what they add that others can reuse; a re-profile refreshes it.
6. **Security tooling**: record the dependency audit command for the stack (`npm audit`, `composer audit`, `pip-audit`, `govulncheck`, ...).
7. **Resource budget** — so parallel agents do not saturate the machine:
   - **Team scripts stay in the plugin** — nothing is copied into the project, so a plugin update never leaves stale copies behind. `$TEAM_BIN` is the absolute path of this skill's `references/` directory (the base directory given at the top of the loaded skill + `/references`; without it, the newest `~/.claude/plugins/cache/*/ai-dev-team/*/skills/project-profiling/references`). It holds `run-heavy.sh` (at most `heavy_slots` heavy commands at a time machine-wide, at low CPU priority; `--status` shows the holders), `rule-checks.sh`, `overflow-check.mjs` and `device-preview.mjs` (QR to the user's phone, with `qr.mjs`). The profile writes commands with the literal `$TEAM_BIN/…`; the leader resolves it and the other team paths once per session (`ai-dev-team:dev-team` → `references/team-paths.md`) and agents call the scripts by the absolute path in their brief.
   - `heavy_workers` = max(2, CPU threads ÷ 4) (`nproc`, or `sysctl -n hw.ncpu` on macOS). `heavy_slots` = max(1, CPU threads ÷ 8): how many heavy commands `run-heavy.sh` lets run at once on this machine. `max_agents` (developers at once) = 4 and `max_verifiers` (reviewers, qc and other read-mostly agents at once) = 4 unless the existing profile sets other values — keep the user's values on re-profiling. Only when `ui` is `web` or `web+mobile`: `ui_widths` = the widths of the devices the app targets plus one width inside every breakpoint tier its CSS or design tokens define (a phone-first app with tablet and desktop layouts: e.g. `360,390,768,1024,1280,1440,1920`; a phone-only app: `360,390,430`; a desktop-only console: `1280,1440,1920`); `ui_themes` = the themes the app ships (`light,dark` when it has a dark mode, else `light`); `ui_theme_set` = how to switch theme when it is not `prefers-color-scheme` (a `--theme-set` snippet such as `document.documentElement.dataset.theme = theme`); `mockup_dir` = where approved mockups are kept in the repo — ask the user once with a proposed default (`docs/mockups/`, or the project's existing design folder), `none` when they do not want them kept; it must be a tracked path (`git check-ignore -q <dir>` fails), otherwise the approved mockup never reaches another machine — when the existing value is ignored (by `.gitignore`, `.git/info/exclude` or a project rule that keeps mockups in a git-ignored folder), ask the user once whether to move it to a tracked folder, and record the answer; `ui_seed` = how to load worst-case content (longest names, many items, large amounts) for the sweep — seed scripts in `$TEAM_STATE/seed/` passed with `--init`, or URLs / fixture commands; `none yet` until a task builds one; for a monorepo, one set per app in its subsection. Otherwise write `ui_widths: none`. Flutter/native apps record `ui_sizes` (the device sizes for widget/golden tests) instead.
   - Write every heavy command (full/module test runs, builds, e2e, audits, native builds) in the Commands table already wrapped and worker-capped, e.g. `$TEAM_BIN/run-heavy.sh npx vitest run --maxWorkers=8`. Worker flags: Vitest/Jest `--maxWorkers=N`, pytest-xdist `-n N`, ParaTest `--processes=N`, Go `-p N`, Gradle `--max-workers=N`, Maven `-T N`, `flutter test -j N`, Playwright `--workers=N`, `cargo test -j N`, `make -jN`. Docker-based runners: add `--cpus=N` or set it in the compose file used for tests. Record also the light command for a single test file.
7a. **Per-task test scope** — record what a developer runs per task, so it never defaults to the whole suite:
   - `test (related)`: a command that takes the changed files and runs only the tests that import them — `vitest related --run <files>`, `jest --findRelatedTests <files>`, `pytest <test paths>`, PHPUnit / Go / Cargo with the test files of the touched module. Cap workers. Verify it on one file.
   - `test (full)`: the whole suite, marked sign-off only. A "module" command that covers the whole app is the full suite, not a per-task command.
   - `## Guard map`: which guard / architecture / lint-style tests to run for which changed paths (e.g. `*.vue` → the component-class guard; `app.css` → the stylesheet guard; language files → the parity test). Per task only the mapped guards run, never every guard suite.
   - Whether builds write tracked files (bundles, hashed assets): record it under `## Environment issues` — such builds make parallel developers on one tree collide.
7b. **App start** — record `app_start`: the command that brings up the app or demo the team checks against (dev server, `docker compose up -d --wait`, plus any known follow-up such as recreating a proxy container that shares another container's network), the readiness check (`curl -fsS <url>` once, after the wait), and where the URL comes from (`http://localhost:${HTTP_PORT}` from `.env`, the dev server's printed URL). Run it once to verify it; leader and qc start the app with it instead of rediscovering the steps. Record with it: how failure shows (a script that prints `FAILED:` and still exits 0 is read for that line, not by its exit code), the services whose code is bind-mounted and must be restarted when it changes (a stub or worker started once keeps old code), and the sibling services in the stack whose migrations or imports must be current (`app_start` runs them or reports what is pending). Record also the test login the team may use on this stack (a test persona, a sign-in link, a seed account) in `ui_flows`, so nobody signs in with an admin password from `.env`. Also run `$TEAM_BIN/rule-checks.sh env-drift` and record missing keys under `## Environment issues` — a local `.env` older than its example file builds and installs incomplete packages.
8. **Rule check scripts**: `$TEAM_BIN/rule-checks.sh` and `$TEAM_BIN/overflow-check.mjs` run from the plugin with the project root as the working directory. `overflow-check.mjs` and every browser check need Playwright. Find it once here — the project's own `node_modules`, then `$TEAM_TOOLS`; when neither has it, install it into `$TEAM_TOOLS` (`npm init -y && npm i -D playwright && npx playwright install chromium --only-shell`) — and record the directory as `playwright_dir`. Agents get it as `PLAYWRIGHT_DIR` in their brief and never search the file system for it. Never add Playwright to the project's own manifest. Developers and qc run them as evidence for the rules a script can decide (`ai-dev-team:dev-team` → `references/rule-packs.md` §9).
9. Write the profile using the template below. Monorepo with several stacks or apps: one subsection per package/app with its own commands, `ui`, `ui_widths` and `ui_themes`.
   - **Each field once, in front matter**: a field the template has goes in the front matter (or the app's subsection in a monorepo), once; a missing field found later is added there, never appended to the body or written a second time.
   - **Portable vs machine fields**: the profile is committed and read on every machine, so it holds only what is true everywhere, with paths relative to the repo root. Machine-specific values — `playwright_dir`, `heavy_workers`, `heavy_slots`, the resolved app URL and port, local tool paths (an SDK installed under `$TEAM_TOOLS`, a pinned toolchain the project's scripts require), `device_preview` — go in `$TEAM_STATE/local.md` (same front-matter format, git-ignored by `.ai-dev-team/.gitignore`), checked and filled on each machine in Phase 0. "The profile's `playwright_dir`" means that file's value.

Empty repo: write `status: greenfield`, `tooling_policy: latest-stable`, skip steps 3–6 but still do steps 7–8 (budget, script check); the leader profiles again right after the scaffold task. Existing projects get `tooling_policy: keep-existing`.

## Profile template

```markdown
---
updated: YYYY-MM-DD
status: active | greenfield
tooling_policy: latest-stable | keep-existing
ui: none | web | mobile | web+mobile
mobile_platform: none | flutter | capacitor | native | react-native
frontend_arch: none | headless-core | <framework>-conventional
tests: present | none
max_agents: 4
max_verifiers: 4
app_start: <command that starts the app or demo and waits until it answers; URL source, e.g. http://localhost:${HTTP_PORT} from .env; none>
ui_widths: none | <comma-separated widths>
ui_themes: light | light,dark
ui_theme_set: <js snippet, only when not prefers-color-scheme>
ui_seed: <$TEAM_STATE/seed/<name>.js per screen group, or URLs / fixture commands; none yet>
ui_flows: <$TEAM_STATE/flows/<name>.mjs — reusable UI steps (login, open record, open dialog); none yet>
design_taste: usability-first <plus lasting look-and-feel preferences the user stated, e.g. bright energetic palette>
mockup_dir: <tracked repo directory where approved mockups are kept, e.g. docs/mockups; none = not kept>
---
# Project Profile

## Stack
| Part | Technology | Version | Source |
|---|---|---|---|

## Commands
| Purpose | Command | Status |
|---|---|---|
| test (related, per task) | e.g. `npx vitest related --run --maxWorkers=N <changed files>` | verified |
| test (single file, light) | ... | verified |
| test (e2e, one spec) | e.g. `$TEAM_BIN/run-heavy.sh npx playwright test e2e/<spec> --workers=N` — per task; the whole e2e target is sign-off only | verified |
| test (full, sign-off only, heavy) | $TEAM_BIN/run-heavy.sh ... | verified |
| lint | ... | ... |
| build | ... | ... |
| security audit | ... | ... |

## Guard map
| Changed paths | Guard tests to run |
|---|---|
| ... | ... |

## Layout & key modules
- `path/` — role

## Code conventions
- ...

## Environment issues
- ...
```

`$TEAM_STATE/local.md` (git-ignored, one per machine):

```markdown
---
updated: YYYY-MM-DD
playwright_dir: <directory whose node_modules has Playwright: the project root, an existing install, or $TEAM_TOOLS; none>
heavy_workers: N
heavy_slots: N
app_url: <the app URL on this machine, e.g. http://localhost:8080>
tools: <local SDK or tool paths the commands need, e.g. flutter=~/.local/state/ai-dev-team/flutter/bin/flutter; none>
device_preview: <modes of $TEAM_BIN/device-preview.mjs this machine supports: web, url, apk, android-pair (needs adb); none>
---
```
