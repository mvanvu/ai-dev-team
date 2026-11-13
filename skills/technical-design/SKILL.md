---
name: technical-design
description: "Produces a technical plan and task board from a spec: components, data model, API contracts, decisions with trade-offs, risks, and right-sized ordered tasks tagged ui/pwa/mobile/security with their rule packs. Also covers greenfield stack proposals. Used by the dev-team leader in planning (on its own, or as the requirements a superpowers writing-plans plan must meet), or when asked to 'design the solution', 'plan the implementation', 'break this into tasks', or 'pick a stack'. Not for UI visuals (ui-ux-design) or specs (spec-writing)."
---

# Technical design

The plan exists so the developer never has to make an architectural decision mid-task and qc knows exactly which contracts to check. When the plan is written with `superpowers:writing-plans`, it must still contain what this procedure requires (contracts, decisions, toolchain, sizing), and the leader turns its tasks into the task board below.

## Procedure
1. Read the spec, project profile and the code in the affected area.
2. List affected components and new components. Prefer extending existing ones: check `$TEAM_STATE/capabilities.md` and search by name before planning anything new, and write per task what it reuses (path) or why nothing fits (`BASE-16`).
3. Define the data model changes (fields, types, constraints, migrations) and **contracts** between modules: endpoint/function signature, request and response shapes with types and nullability, error codes.
4. Record decisions: for each non-obvious choice, the options considered, the choice and why.
5. Risks: what can break (migrations, performance, backward compatibility) and mitigation.
6. Break into tasks: 3–8 for a typical feature, each a coherent slice of one module. Every task pays a fixed cost (agent start-up, review, QC), so merge small changes in the same module; split only past ~1–2 hours of work. Order so each task leaves the build green. UI changes that come from the same mockup or UI-spec option, touch the same component family or rebuild the same bundle are **one task** (one build, one review, one QC), split only past the size limit above. For a `has_ui` feature built through the design gate's stage 2 in the project's frontend (`ai-dev-team:ui-ux-design` → `references/design-gate.md` §3), the screens and their fake adapter come first, the contract is taken from the approved adapter interface when no API exists yet, and the remaining client tasks are "wire" tasks that swap the fake adapter for the real client. Contract-defining tasks (schema, API) come before the consumers that call them for real (UI wiring, mobile): a task never mixes server and client code, and every client task lists the server task whose contract it consumes in `Depends on`, so it starts only after that task is `done` (reviewed and QC'd, contract frozen) — never in parallel with it. A site template or theme builds on the CMS's or framework's default layouts and styles them with CSS and tokens; it overrides only the views whose markup the approved mockup must change, and the plan lists those overrides by name — never a rewrite of every view. Variants that repeat (colour presets, themes, sizes, locales, page types of a template) are planned as data plus one loop or generator — a token table rendered to CSS custom properties, a list of page definitions — never as hand-written copies per variant. A task that changes a shared component, style or layout primitive names in `Files` every screen and route that renders it (search its usages; other apps, modes and embedded variants included) so the sweep covers them (`SWEEP-4`). The `Files` column lists every file the task will change, including shared components, stylesheets, language files and tests; two tasks whose files overlap — or that both change the same frontend app's built bundle — get a dependency between them, so the leader never runs them at the same time on one tree.
6a. Resource lists: plan one list component per resource reused by its page and its picker (`ai-dev-team:pwa-headless-ui` → `references/list-page.md`); every list endpoint contract includes `limit`/`offset` with a server maximum, `search`, allowlisted `order`, the filters, `ids` for picker labels, `{ items, total }` and the permission keys the server returns (user and per row, in the project's own naming).
6b. CRUD entities: decide per entity whether the lifecycle of `references/record-lifecycle.md` applies (active flag, trash/restore/purge, status filter, server-returned permission keys, bulk actions with single-row rules) — by default yes for user-managed master data, no for child rows, join tables, settings, logs and messages. When the request did not say, it is an open question for the user with the default as the proposal; never add trash, purge or permission endpoints the user did not agree to.
6c. Query shape: for every list, detail-with-children, export and bulk contract, name the relations and aggregates the response includes so they can be loaded in a fixed number of queries, and give clients a batch form (`ids`) instead of per-row requests (`ai-dev-team:code-review-checklist` → `references/query-performance.md`).
6d. Rule packs: for every task, list the rule packs that apply in the task board's `Rules` column, using the "Applies when" table in `ai-dev-team:dev-team` → `references/rule-packs.md` §2 and §5. Assign by what the task touches, not only by its tags; when unsure, assign the pack.
6e. Integration points: list the files several tasks would each change by a line or two — the app entry that registers overrides or providers, the router, a DI module, a barrel export, the nav menu, `AndroidManifest.xml` / `Info.plist`. Either plan one small setup task that adds every task's hook first, or note that the leader adds those registrations after each task; the tasks then list only their own files and can run in parallel (`ai-dev-team:dev-team` → Phase 3 step 3).
7. When the UI spec / threat model exist, reconcile them: add UI tasks per screen/component and the `SEC-n` requirements to the relevant tasks. A contradiction between spec, UI spec and threat model goes to the user, not into a guess.

## Greenfield
Propose the stack with a directory layout and a test scaffold. When the user has not named the technology for a part, propose the default stack below as the recommended option; list an alternative only when the spec gives a concrete reason the default does not fit (and say why).

### Default stack
| Part | Default | Notes |
|---|---|---|
| Backend | **NestJS** (TypeScript) | Modules per domain, DTO validation with `class-validator`, OpenAPI from decorators |
| Database | **PostgreSQL + Prisma** | Prisma schema and migrations; raw SQL only for queries Prisma cannot express |
| Caching | **Redis** | Cache, rate-limit counters, queues (BullMQ) and sessions when needed |
| Frontend | **Vue 3 + TypeScript** | Mobile-first PWA on the headless core-component + template-pack architecture with `reka-ui` (`ai-dev-team:pwa-headless-ui`) |

- Applies per part: a part the user named keeps the user's choice; a part the existing project already has keeps the project's technology (`tooling_policy: keep-existing`). The default fills only parts that are both unspecified and new — e.g. an existing project that needs a cache for the first time gets Redis proposed.
- Include a part only when the spec needs it (no Redis for a project with nothing to cache or queue).
- Versions follow the latest-stable rules below; the defaults are recorded in the design's `## Toolchain` table and the `## Decisions` table (`Choice: default stack`). For the mobile app, use the platform the user chose (Flutter — recommended, Capacitor wrapping the PWA, or native Swift/Kotlin); if no choice is recorded, mark it `needs-user-decision` with those three options instead of picking one. Mark as `needs-user-approval`; do not proceed past planning until approved.

### Latest-stable toolchain
New projects — and new apps or packages added to an existing repo — start on the **latest stable** build tools, runtimes and frameworks; a fresh project has no reason to begin on outdated tooling.
- Look every version up when designing, never from memory: `npm view <pkg> version` (or `dist-tags`), `pnpm view`, `pip index versions <pkg>`, `uv`/PyPI, `cargo search`, `go list -m -versions`, `flutter --version` on the stable channel, Gradle / Android Gradle Plugin / Kotlin / Xcode release notes, or the context7 docs MCP when available.
- Stable only: no beta, RC, canary or nightly. Runtimes use the latest LTS where the project has an LTS line (Node.js, JDK); otherwise the latest stable.
- Check compatibility before committing to a new major (framework ↔ build tool ↔ plugins, e.g. Vite ↔ `vite-plugin-pwa`, Capacitor ↔ its plugins, Flutter ↔ key packages). When a required library does not support the newest major yet, choose the newest compatible version and write the reason.
- Prefer the current generation of a tool over its legacy setup (official scaffolder at `@latest`, current config formats such as ESLint flat config, current package manager).
- Record the result in the plan's `## Toolchain` table; developers install exactly these versions and commit the lockfile.
- Existing projects keep their versions; upgrading is a task only when the user asks for it.

## Template: `$TEAM_WS/02_plan.md`

```markdown
# Design: <feature>
## Overview
## Components (affected / new)
## Data model
## Contracts
### <METHOD /path or function>
- Request: { field: type, ... }
- Response 200: { ... }
- Errors: 400 {code}, 403 {code}, ...
## Decisions
| Decision | Options | Choice | Why |
## Toolchain (greenfield / new app only)
| Tool | Version | Checked via | Date |
## Risks & mitigation
```

## Template: `$TEAM_WS/02_tasks.md` (task board)

```markdown
| ID | Task | Owner | Depends on | Tags | Rules | Files | Verify with | Status | Rounds |
|----|------|-------|-----------|------|-------|-------|-------------|--------|--------|
| T1 | Add order table migration | be | - | - | LIFE | migrations/... | `<test cmd>` | todo | 0 |
| T2 | GET/POST /orders endpoints | be | T1 | security | LIFE, ABUSE, QUERY, AC-1, AC-2, SEC-1 | src/... | `<test cmd>` | todo | 0 |
| T3 | Order list + form screens | fe | T2 | ui | ARCH, COMPACT, LIST, LIFE, SWEEP, AC-3 | web/... | `<test cmd>` | todo | 0 |
```
Every task is built by a `developer` agent. Owner is the task's side: `be` server (schema, APIs, jobs, integrations, infra) or `fe` client (web, PWA, Capacitor, Flutter, native); one side per task. Tags: `ui`, `pwa`, `mobile`, `security`.
Rules: rule pack IDs from `ai-dev-team:dev-team` → `references/rule-packs.md` plus the task's `AC-n` and `SEC-n` (`BASE` and `COST` apply to every task and are not written). The developer reports one row per rule ID; the reviewer and qc re-check them.
Status values: `todo | in-progress | review | fix | done | blocked | needs-rework`. Rounds counts fix rounds (max 3, then one escalation) so a resumed run keeps the count. The leader owns both columns.
