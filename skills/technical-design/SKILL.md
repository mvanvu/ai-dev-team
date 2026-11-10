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
6. Break into tasks: 3–8 for a typical feature, each a coherent slice of one module with one Owner. Every task pays a fixed cost (agent start-up, review, QA), so merge small changes in the same module; split only past ~1–2 hours of work or when owners differ. Order so each task leaves the build green. Contract-defining tasks (schema, API) come before consumers (UI, mobile).
7. When the UI spec / threat model exist, reconcile them: add UI tasks per screen/component and security requirements to the relevant tasks.

## Greenfield
Propose 1–2 stack options with trade-offs fit to the spec (team skills, hosting, web/mobile needs), a directory layout, and a test scaffold. When the product needs a web frontend, the default proposal is a mobile-first PWA (Vue 3 + reka-ui or React + Radix UI, TypeScript) with the headless core-component + template-pack architecture — see the `ai-dev-team:pwa-headless-ui` skill; the user picks Vue or React. For the mobile app, use the platform the user chose (Flutter — recommended, Capacitor wrapping the PWA, or native Swift/Kotlin); if no choice is recorded, mark it `needs-user-decision` with those three options instead of picking one. Mark as `needs-user-approval`; do not proceed past design until approved.

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
## Risks & mitigation
```

## Template: `_workspace/02_architect_tasks.md` (task board)

```markdown
| ID | Task | Owner | Depends on | Tags | Files | Verify with | Status |
|----|------|-------|-----------|------|-------|-------------|--------|
| T1 | Add order table migration | developer | - | - | migrations/... | `<test cmd>` | todo |
| T2 | POST /orders endpoint | developer | T1 | security | src/... | `<test cmd>` | todo |
| T3 | Order form screen | pwa-frontend-engineer | T2 | ui | web/... | `<test cmd>` | todo |
```
Owner: `pwa-frontend-engineer` for all frontend and mobile app work (screens, core components, templates, PWA, Flutter / Capacitor / native); `developer` for backend, data, infrastructure and non-UI code. Tags: `ui`, `pwa`, `mobile`, `security`.
Status values: `todo | in-progress | review | qa | done | blocked | needs-rework`. The leader owns status updates.
