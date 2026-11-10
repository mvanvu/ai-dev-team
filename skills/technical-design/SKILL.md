---
name: technical-design
description: "Produces a technical design and task board from a spec: components, data model, API contracts, decisions with trade-offs, risks, and right-sized ordered tasks tagged ui/pwa/mobile/security. Also covers greenfield stack proposals. Used by architect, or when asked to 'design the solution', 'plan the implementation', 'break this into tasks', or 'pick a stack'. Not for UI visuals (ui-ux-design) or specs (spec-writing)."
---

# Technical design

The design exists so the developer never has to make an architectural decision mid-task and QA knows exactly which contracts to check.

## Procedure
1. Read the spec, project profile and the code in the affected area.
2. List affected components and new components. Prefer extending existing ones.
3. Define the data model changes (fields, types, constraints, migrations) and **contracts** between modules: endpoint/function signature, request and response shapes with types and nullability, error codes.
4. Record decisions: for each non-obvious choice, the options considered, the choice and why.
5. Risks: what can break (migrations, performance, backward compatibility) and mitigation.
6. Break into tasks: 3–8 for a typical feature, each a coherent slice of one module with one Owner. Every task pays a fixed cost (agent start-up, review, QA), so merge small changes in the same module; split only past ~1–2 hours of work or when owners differ. Order so each task leaves the build green. Contract-defining tasks (schema, API) come before consumers (UI, mobile). The `Files` column lists every file the task will change, including shared components, stylesheets, language files and tests; two tasks whose files overlap — or that both change the same frontend app's built bundle — get a dependency between them, so the leader never runs them at the same time on one tree.
6a. Resource lists: plan one list component per resource reused by its page and its picker (`ai-dev-team:pwa-headless-ui` → `references/list-page.md`); every list endpoint contract includes `limit`/`offset` with a server maximum, `search`, allowlisted `order`, the filters, `ids` for picker labels, `{ items, total }` and the permission keys the server returns (user and per row, in the project's own naming).
6b. CRUD entities follow `references/record-lifecycle.md`: `active` + soft delete, trash/restore/purge permissions and endpoints, status filter, active switch, the permission keys the server returns (user and per row, in the project's own naming), and bulk actions with the same rules as single rows. Plan these into the entity's tasks without being asked.
6c. Query shape: for every list, detail-with-children, export and bulk contract, name the relations and aggregates the response includes so they can be loaded in a fixed number of queries, and give clients a batch form (`ids`) instead of per-row requests (`ai-dev-team:code-review-checklist` → `references/query-performance.md`).
6d. Rule packs: for every task, list the rule packs that apply in the task board's `Rules` column, using the "Applies when" table in `ai-dev-team:dev-team` → `references/rule-packs.md` §2 and §5. Assign by what the task touches, not only by its tags; when unsure, assign the pack.
7. When the UI spec / threat model exist, reconcile them: add UI tasks per screen/component and security requirements to the relevant tasks.

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
- Versions follow the latest-stable rules below; the defaults are recorded in the design's `## Toolchain` table and the `## Decisions` table (`Choice: default stack`). For the mobile app, use the platform the user chose (Flutter — recommended, Capacitor wrapping the PWA, or native Swift/Kotlin); if no choice is recorded, mark it `needs-user-decision` with those three options instead of picking one. Mark as `needs-user-approval`; do not proceed past design until approved.

### Latest-stable toolchain
New projects — and new apps or packages added to an existing repo — start on the **latest stable** build tools, runtimes and frameworks; a fresh project has no reason to begin on outdated tooling.
- Look every version up when designing, never from memory: `npm view <pkg> version` (or `dist-tags`), `pnpm view`, `pip index versions <pkg>`, `uv`/PyPI, `cargo search`, `go list -m -versions`, `flutter --version` on the stable channel, Gradle / Android Gradle Plugin / Kotlin / Xcode release notes, or the context7 docs MCP when available.
- Stable only: no beta, RC, canary or nightly. Runtimes use the latest LTS where the project has an LTS line (Node.js, JDK); otherwise the latest stable.
- Check compatibility before committing to a new major (framework ↔ build tool ↔ plugins, e.g. Vite ↔ `vite-plugin-pwa`, Capacitor ↔ its plugins, Flutter ↔ key packages). When a required library does not support the newest major yet, choose the newest compatible version and write the reason.
- Prefer the current generation of a tool over its legacy setup (official scaffolder at `@latest`, current config formats such as ESLint flat config, current package manager).
- Record the result in the design's `## Toolchain` table; implementers install exactly these versions and commit the lockfile.
- Existing projects keep their versions; upgrading is a task only when the user asks for it.

## Template: `_workspace/02_architect_design.md`

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

## Template: `_workspace/02_architect_tasks.md` (task board)

```markdown
| ID | Task | Owner | Depends on | Tags | Rules | Files | Verify with | Status |
|----|------|-------|-----------|------|-------|-------|-------------|--------|
| T1 | Add order table migration | developer | - | - | LIFE | migrations/... | `<test cmd>` | todo |
| T2 | GET/POST /orders endpoints | developer | T1 | security | LIFE, ABUSE, QUERY | src/... | `<test cmd>` | todo |
| T3 | Order list + form screens | pwa-frontend-engineer | T2 | ui | ARCH, COMPACT, LIST, LIFE | web/... | `<test cmd>` | todo |
```
Owner: `pwa-frontend-engineer` for all frontend and mobile app work (screens, core components, templates, PWA, Flutter / Capacitor / native); `developer` for backend, data, infrastructure and non-UI code. Tags: `ui`, `pwa`, `mobile`, `security`.
Rules: rule pack IDs from `ai-dev-team:dev-team` → `references/rule-packs.md` (`BASE` applies to every task and is not written). The implementer reports one row per rule ID; reviewers and QA re-check them.
Status values: `todo | in-progress | review | qa | done | blocked | needs-rework`. The leader owns status updates.
