---
name: project-profiling
description: "Procedure for surveying a repo and writing .claude/team/project-profile.md (stack, verified test/lint/build/audit commands, code conventions, web/mobile UI presence). Used by repo-scout, or when asked to 'scan the project', 'update the project profile', or 'what stack does this project use'. Not for code review or design."
---

# Project profiling

The project profile is the team's shared source of truth: which test command the developer runs, what QA checks, which audit tool security uses. Errors here propagate to every later step, so record only what you verified.

## Procedure

1. **List stack marker files** (Glob at root and two levels down):
   `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `composer.json`, `pyproject.toml`, `requirements*.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle*`, `Gemfile`, `pubspec.yaml`, `*.csproj`, `Dockerfile`, `docker-compose*.yml`, `Makefile`, `.github/workflows/*`, `.gitlab-ci.yml`.
2. **Detect UI**: web (React/Vue/Svelte/Angular/Next/Nuxt, Twig/Blade templates), mobile (React Native, Flutter `pubspec.yaml`, `android/`, `ios/`, Swift/Kotlin). Record `ui: none | web | mobile | web+mobile`. Record `mobile_platform`: `flutter` (`pubspec.yaml`), `capacitor` (`capacitor.config.*`), `react-native`, `native` (Swift/Kotlin projects without Capacitor), else `none`.
   Also record frontend architecture facts: PWA (`vite-plugin-pwa`, `manifest.webmanifest`, service worker), Capacitor (`capacitor.config.*`, its `server.url`), headless library (`reka-ui`, `radix-ui`, `@radix-ui/*`, `react-aria-components`), and template packs (`src/templates/*`, active template selection).
3. **Find commands** in package.json `scripts`, `Makefile`, composer scripts, and CI config. CI config is usually the most trustworthy source because it actually runs.
4. **Run** each test/lint command (with a sensible timeout). Record `verified` / `failed: <key error>` / `not-run: <reason>`.
5. **Conventions**: read 3–5 representative files per kind (controller, service, component, test) to extract naming, layout, test framework and assertion style.
6. **Security tooling**: record the dependency audit command for the stack (`npm audit`, `composer audit`, `pip-audit`, `govulncheck`, ...).
7. **Resource budget** — so parallel agents do not saturate the machine:
   - Copy `references/run-heavy.sh` from this skill's directory to `.claude/team/run-heavy.sh` and make it executable. It runs one heavy command at a time machine-wide, at low CPU priority.
   - `heavy_workers` = max(2, CPU threads ÷ 4) (`nproc`, or `sysctl -n hw.ncpu` on macOS). `max_agents` = 4 unless the existing profile sets another value — keep the user's value on re-profiling.
   - Write every heavy command (full/module test runs, builds, e2e, audits, native builds) in the Commands table already wrapped and worker-capped, e.g. `.claude/team/run-heavy.sh npx vitest run --maxWorkers=8`. Worker flags: Vitest/Jest `--maxWorkers=N`, pytest-xdist `-n N`, ParaTest `--processes=N`, Go `-p N`, Gradle `--max-workers=N`, Maven `-T N`, `flutter test -j N`, Playwright `--workers=N`, `cargo test -j N`, `make -jN`. Docker-based runners: add `--cpus=N` or set it in the compose file used for tests. Record also the light command for a single test file.
7a. **Per-task test scope** — record what an implementer runs per task, so it never defaults to the whole suite:
   - `test (related)`: a command that takes the changed files and runs only the tests that import them — `vitest related --run <files>`, `jest --findRelatedTests <files>`, `pytest <test paths>`, PHPUnit / Go / Cargo with the test files of the touched module. Cap workers. Verify it on one file.
   - `test (full)`: the whole suite, marked sign-off only. A "module" command that covers the whole app is the full suite, not a per-task command.
   - `## Guard map`: which guard / architecture / lint-style tests to run for which changed paths (e.g. `*.vue` → the component-class guard; `app.css` → the stylesheet guard; language files → the parity test). Per task only the mapped guards run, never every guard suite.
   - Whether builds write tracked files (bundles, hashed assets): record it under `## Environment issues` — such builds make parallel implementers on one tree collide.
8. **Rule check scripts**: copy `references/rule-checks.sh` and `references/overflow-check.mjs` from this skill's directory to `.claude/team/` and make them executable. Implementers and QA run them as evidence for the rules a script can decide (`ai-dev-team:dev-team` → `references/rule-packs.md` §9).
9. Write the profile using the template below.

Empty repo: write `status: greenfield`, `tooling_policy: latest-stable`, and skip steps 3–6. Existing projects get `tooling_policy: keep-existing`.

## Profile template

```markdown
---
updated: YYYY-MM-DD
status: active | greenfield
tooling_policy: latest-stable | keep-existing
ui: none | web | mobile | web+mobile
mobile_platform: none | flutter | capacitor | native | react-native
max_agents: 4
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
| test (full, sign-off only, heavy) | .claude/team/run-heavy.sh ... | verified |
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
