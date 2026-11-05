---
name: project-profiling
description: "Procedure for surveying a repo and writing .claude/team/project-profile.md (stack, verified test/lint/build/audit commands, code conventions, web/mobile UI presence). Used by repo-scout, or when asked to 'scan the project', 'update the project profile', or 'what stack does this project use'. Not for code review or design."
---

# Project profiling

The project profile is the team's shared source of truth: which test command the developer runs, what QA checks, which audit tool security uses. Errors here propagate to every later step, so record only what you verified.

## Procedure

1. **List stack marker files** (Glob at root and two levels down):
   `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `composer.json`, `pyproject.toml`, `requirements*.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle*`, `Gemfile`, `pubspec.yaml`, `*.csproj`, `Dockerfile`, `docker-compose*.yml`, `Makefile`, `.github/workflows/*`, `.gitlab-ci.yml`.
2. **Detect UI**: web (React/Vue/Svelte/Angular/Next/Nuxt, Twig/Blade templates), mobile (React Native, Flutter `pubspec.yaml`, `android/`, `ios/`, Swift/Kotlin). Record `ui: none | web | mobile | web+mobile`.
   Also record frontend architecture facts: PWA (`vite-plugin-pwa`, `manifest.webmanifest`, service worker), Capacitor (`capacitor.config.*`, its `server.url`), headless library (`reka-ui`, `radix-ui`, `@radix-ui/*`, `react-aria-components`), and template packs (`src/templates/*`, active template selection).
3. **Find commands** in package.json `scripts`, `Makefile`, composer scripts, and CI config. CI config is usually the most trustworthy source because it actually runs.
4. **Run** each test/lint command (with a sensible timeout). Record `verified` / `failed: <key error>` / `not-run: <reason>`.
5. **Conventions**: read 3–5 representative files per kind (controller, service, component, test) to extract naming, layout, test framework and assertion style.
6. **Security tooling**: record the dependency audit command for the stack (`npm audit`, `composer audit`, `pip-audit`, `govulncheck`, ...).
7. Write the profile using the template below.

Empty repo: write `status: greenfield` and skip steps 3–6.

## Profile template

```markdown
---
updated: YYYY-MM-DD
status: active | greenfield
ui: none | web | mobile | web+mobile
---
# Project Profile

## Stack
| Part | Technology | Version | Source |
|---|---|---|---|

## Commands
| Purpose | Command | Status |
|---|---|---|
| test | ... | verified |
| lint | ... | ... |
| build | ... | ... |
| security audit | ... | ... |

## Layout & key modules
- `path/` — role

## Code conventions
- ...

## Environment issues
- ...
```
