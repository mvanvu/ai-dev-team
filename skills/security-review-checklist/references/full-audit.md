# Full security audit

Procedure for a whole-codebase audit or pen-test style review. Condensed and adapted from Cloudflare's `security-audit` skill (MIT — see `THIRD-PARTY-NOTICES.md` at the plugin root). Per-task reviews use the checklist in `SKILL.md`; this file is for "audit the codebase", "full / comprehensive security review", or a requested audit report.

Goal: find vulnerabilities that violate a real trust boundary, and give owners the source evidence, a safe reproduction, a priority and the smallest effective fix. Defensive and source-first.

## Contents
1. Modes
2. Execution safety
3. Principles
4. Severity
5. Workflow
6. Candidate gate
7. Record states
8. Report
9. Anti-patterns

## 1. Modes
- **Guidance** (default): a security question, a focused review, triage of one finding → use only the relevant parts; write no audit files.
- **Full audit**: only when the user explicitly asks for an audit, pen test, full/end-to-end review or report artifacts → run §5 completely. If the request could mean either, ask one question first.
- Scope and depth are stated up front: whole repo, named paths, one subsystem, or a diff. A scoped or quick pass is reported as **partial coverage**; everything not examined is `out of scope`, never "fine".

## 2. Execution safety
1. Source inspection is read-only; the audit never modifies target source.
2. Run target code (builds, tests, fixtures, local servers) only when it is isolated: no external network, dummy principals / data / secrets, no real credentials or host secrets in its environment, writes confined to a scratch directory, bounded time and resources. No dependency installs or fetches for the audit.
3. Never probe deployed endpoints, production identities, other users' data, shared infrastructure or third-party services. No load, stress, fuzzing or scanning against anything live or shared; no publishing, no paid API spend.
4. Stop at the minimum effect that proves the defect (wrong return value, unauthorized dummy record, sanitizer hit). No persistence, concealment or impact expansion.
5. When the isolation in item 2 is not available, do not execute: record the candidate as `needs_validation` with the missing capability and a safe validation plan.

## 3. Principles
1. **Boundary and result.** Every candidate names: the lower-trust principal, the input or action accepted, the control that should have stopped it, the boundary crossed, the affected principal or resource, and the concrete result. A missing best practice, a guessed deployment behavior, a generic crash or self-impact is not a finding.
2. **Bounded local evidence.** Static analysis establishes the path; the narrowest local check settles behavior — an existing unit test, a minimal harness, a small fixture, a dummy-tenant call.
3. **Source visibility.** Proxy, CDN, IAM, broker ACLs, browser headers and other deployment controls are real. When one is decisive and not in the repository, assume neither presence nor absence: `needs_validation` with the exact missing fact.
4. **Priority is not certainty.** Only `confirmed` records get a severity, and it cannot exceed the demonstrated impact.
5. **Smallest effective fix.** Name the invariant the code must enforce and the narrowest change at the last trusted decision point, plus a regression test. Prefer a specific file-level change over generic hardening advice.

## 4. Severity
| Level | Anchor |
|---|---|
| critical | An unauthenticated actor gains code execution, full data-store access, or takeover of arbitrary accounts |
| high | An explicit security control is fully defeated with real consequences: auth bypass, cross-tenant read/write, stored script execution against other users, authenticated code execution, unauthenticated remote stop of a shared service |
| medium | A real boundary violation with limited blast radius, uncommon preconditions, or a narrow resource set |
| low | Disclosure of non-secret internals, or sustained effort for minimal gain |
| informational | Confirmed but minimal impact; mainly a prerequisite for a larger finding |

High vs medium: does the demonstrated result fully defeat a control for an action with real consequences, or only weaken it? If the concrete damage cannot be stated, the severity is lower than it feels.

## 5. Workflow
1. **Reconnaissance** — map, with `file:line` references and without running anything:
   - product, users, operators, stack, entry points, subsystem boundaries, deployment modes visible in the repo;
   - principals and controls: who each lower-trust principal is, how it is authenticated, per-resource authorization and tenant/owner scope, privilege changes, revocation, recovery and fallback paths;
   - entry surfaces and sinks: HTTP/browser, RPC/messages, files/archives, CLI/env/config, plugins/dependencies/CI, cloud events, model context and tool arguments, mobile deep links/webviews, local IPC — each followed through transformations, stored copies and security-relevant sinks, including parallel paths to the same effect;
   - which controls are source-visible and which depend on unobserved deployment facts;
   - offline tests and fixtures usable for bounded validation.
2. **Coverage plan** — a table of units: surface × boundary × attack class (from `attack-classes.md`, core classes plus the domains that match the target). Each unit ends as `covered`, `candidate`, `needs_validation`, `blocked`, `deferred` or `out_of_scope`. Nothing is silently dropped.
3. **Hunting** — per unit, work from a concrete invariant:
   1. name the principal and its starting capability;
   2. name the value, action, state transition or resource selector it controls;
   3. locate the control that should reject, bind, isolate, limit or revoke it;
   4. trace the exact path after that decision, including sibling, legacy, batch, retry, cancellation, migration and error paths that reach the same effect; compare sibling controls for equivalence, not presence, and what one component guarantees with what the next assumes;
   5. test sad paths where the interface accepts them: absent, empty, zero, negative, maximum, duplicate, mixed encoding, stale, revoked, reordered, concurrent, partially migrated, failed dependency, rollback;
   6. stop when the invariant is settled either way and record the result.
   A high or critical root cause triggers a search for lexical, structural and logical variants; each variant's conditions and impact are established on their own.
4. **Independent validation** — every candidate is re-checked by a fresh reviewer who did not find it (a second agent when available; otherwise a separate pass that tries to refute it): full source trace, the strongest preventing control, the bounded local result.
5. **Coverage critique** — after hunting, list surfaces, classes and paths the plan missed; hunt them or record them as `deferred` with the reason.
6. **Report** — written only from validated records (§8).

## 6. Candidate gate
1. A candidate has a complete repository-relative source trace for the claimed root cause, including the strongest source-visible control.
2. `confirmed` additionally needs a bounded observed result, meaningful impact across a stated boundary, complete conditions and no visible preventing layer.
3. Do not strengthen a crash into code execution, ordinary work into shared-service unavailability, or a same-principal action into privilege gain.
4. A decisive fact that is neither source-visible nor locally observable → `needs_validation`, with the exact blocker, no severity.
5. A missing best practice with no affected principal or resource is a hardening note, not a finding. A candidate disproved by source is `rejected`, not `needs_validation`.
6. The same root cause is one record, however many places or reviewers surfaced it.

## 7. Record states
| State | Meaning | Has severity |
|---|---|---|
| `confirmed` | Path, boundary and result established and independently validated | yes |
| `needs_validation` | Source-grounded hypothesis blocked on one named external fact; includes a safe owner-run check | no |
| `rejected` | Disproved; kept with the reason so it is not re-raised | no |

## 8. Report
Write `_workspace/security-audit/REPORT.md` (or the path the user names), in this order:
1. Scope, source ref (commit, dirty or not), depth, and a coverage statement: what was covered, deferred, out of scope. Never imply the audit exhausted the target.
2. Confirmed findings, most severe first, each with: title, severity, `file:line`, principal → input → missing or weak control → boundary → result, conditions, safe local reproduction (command and input, dummy data only), smallest fix and regression test.
3. Needs validation: hypothesis, the exact missing fact, the safe check the owner can run.
4. Hardening notes (not findings), kept separate.
No live-probe instructions, no real credentials, no data from outside the repository.

## 9. Anti-patterns
1. Checklist deviations presented as vulnerabilities.
2. Defense-in-depth advice with no reachable boundary violation.
3. Live or shared-environment testing when local evidence is not enough.
4. Guessing provider, proxy, browser, identity or deployment behavior that is not in source.
5. Treating intended same-principal authority or self-impact as a cross-boundary result.
6. Reporting an effect stronger than the one observed.
7. Prose-only findings that cannot be deduplicated or verified.
8. Severity on `needs_validation` records.
9. Writing the report before independent validation, or letting summary and details disagree.
