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
6. **Security tooling**: record the dependency audit command for the stack (`npm audit`, `composer audit`, `pip-audit`, `govulncheck`, ...).
7. **Resource budget** — so parallel agents do not saturate the machine:
   - **Team scripts stay in the plugin** — nothing is copied into the project, so a plugin update never leaves stale copies behind. `$TEAM_BIN` is the absolute path of this skill's `references/` directory (the base directory given at the top of the loaded skill + `/references`; without it, the newest `~/.claude/plugins/cache/*/ai-dev-team/*/skills/project-profiling/references`). It holds `run-heavy.sh` (one heavy command at a time machine-wide, at low CPU priority), `rule-checks.sh` and `overflow-check.mjs`. The profile writes commands with the literal `$TEAM_BIN/…`; the leader resolves it and the other team paths once per session (`ai-dev-team:dev-team` → `references/team-paths.md`) and agents call the scripts by the absolute path in their brief.
   - `heavy_workers` = max(2, CPU threads ÷ 4) (`nproc`, or `sysctl -n hw.ncpu` on macOS). `max_agents` = 4 unless the existing profile sets another value — keep the user's value on re-profiling. Only when `ui` is `web` or `web+mobile`: `ui_widths` = the widths of the devices the app targets plus one width inside every breakpoint tier its CSS or design tokens define (a phone-first app with tablet and desktop layouts: e.g. `360,390,768,1024,1280,1440,1920`; a phone-only app: `360,390,430`; a desktop-only console: `1280,1440,1920`); `ui_themes` = the themes the app ships (`light,dark` when it has a dark mode, else `light`); `ui_theme_set` = how to switch theme when it is not `prefers-color-scheme` (a `--theme-set` snippet such as `document.documentElement.dataset.theme = theme`); `ui_seed` = how to load worst-case content (longest names, many items, large amounts) for the sweep — seed scripts in `$TEAM_STATE/seed/` passed with `--init`, or URLs / fixture commands; `none yet` until a task builds one; for a monorepo, one set per app in its subsection. Otherwise write `ui_widths: none`. Flutter/native apps record `ui_sizes` (the device sizes for widget/golden tests) instead.
   - Write every heavy command (full/module test runs, builds, e2e, audits, native builds) in the Commands table already wrapped and worker-capped, e.g. `$TEAM_BIN/run-heavy.sh npx vitest run --maxWorkers=8`. Worker flags: Vitest/Jest `--maxWorkers=N`, pytest-xdist `-n N`, ParaTest `--processes=N`, Go `-p N`, Gradle `--max-workers=N`, Maven `-T N`, `flutter test -j N`, Playwright `--workers=N`, `cargo test -j N`, `make -jN`. Docker-based runners: add `--cpus=N` or set it in the compose file used for tests. Record also the light command for a single test file.
7a. **Per-task test scope** — record what a developer runs per task, so it never defaults to the whole suite:
   - `test (related)`: a command that takes the changed files and runs only the tests that import them — `vitest related --run <files>`, `jest --findRelatedTests <files>`, `pytest <test paths>`, PHPUnit / Go / Cargo with the test files of the touched module. Cap workers. Verify it on one file.
   - `test (full)`: the whole suite, marked sign-off only. A "module" command that covers the whole app is the full suite, not a per-task command.
   - `## Guard map`: which guard / architecture / lint-style tests to run for which changed paths (e.g. `*.vue` → the component-class guard; `app.css` → the stylesheet guard; language files → the parity test). Per task only the mapped guards run, never every guard suite.
   - Whether builds write tracked files (bundles, hashed assets): record it under `## Environment issues` — such builds make parallel developers on one tree collide.
8. **Rule check scripts**: `$TEAM_BIN/rule-checks.sh` and `$TEAM_BIN/overflow-check.mjs` run from the plugin with the project root as the working directory. `overflow-check.mjs` needs Playwright: when the project has none, record `qa-tools: $TEAM_TOOLS` (set up there on first use, never added to the project). Developers and qc run them as evidence for the rules a script can decide (`ai-dev-team:dev-team` → `references/rule-packs.md` §9).
9. Write the profile using the template below. Monorepo with several stacks or apps: one subsection per package/app with its own commands, `ui`, `ui_widths` and `ui_themes`.

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
ui_widths: none | <comma-separated widths>
ui_themes: light | light,dark
ui_theme_set: <js snippet, only when not prefers-color-scheme>
ui_seed: <$TEAM_STATE/seed/<name>.js per screen group, or URLs / fixture commands; none yet>
heavy_workers: N
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
