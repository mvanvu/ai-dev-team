---
name: security-review-checklist
description: "Threat-modeling template and vulnerability review checklist (OWASP Top 10, OWASP API Top 10, OWASP MASVS for mobile, authn/authz, secrets, dependencies, automated abuse by scrapers/bots/AI crawlers and agents) with finding format and structured output. Used by the reviewer agent (task reviews, threat models, full audits) and the dev-team final review workflow. Also covers full codebase audits and pen-test style reviews (procedure, severity anchors, attack classes by domain) in its references."
---

# Security review checklist

## Threat model (planning phase): `_workspace/02_threat-model.md`
```markdown
# Threat model: <feature>
## Assets (data/capabilities worth protecting)
## Trust boundaries & data flows
## Threats (STRIDE per flow)
| Flow | Threat | Category | Likelihood | Impact | Mitigation → task |
## Automated abuse (scrapers, bots, AI crawlers/agents) — one row per public flow, see references/automated-abuse.md
## Security requirements for implementation
- SEC-1: ... (one testable requirement per line; the leader assigns each to tasks)
```

## Code review checklist
1. **Injection** — SQL/NoSQL, OS command, LDAP, template injection; trace every untrusted input to its sink.
2. **Broken access control** — authorization on every endpoint/handler/resolver; IDOR (object IDs from the client); privilege escalation via mass assignment. Trash/restore/purge need their own permission plus the view-trash permission (names follow the project's scheme) and purge only trashed rows; bulk/batch endpoints repeat every per-row authorization check and cap the number of ids (`ai-dev-team:technical-design` → `references/record-lifecycle.md`).
3. **Authentication & sessions** — password storage (bcrypt/argon2), JWT validation (alg, expiry, signature), session fixation, CSRF on state-changing requests, rate limiting on login/OTP.
4. **XSS & output** — unescaped output, `dangerouslySetInnerHTML`/`v-html`/`|raw`, unsafe URL schemes.
5. **SSRF & redirects** — user-controlled URLs fetched server-side; open redirects.
6. **Files** — path traversal, upload type/size validation, serving uploads from an executable path.
7. **Deserialization & XXE** — unsafe unserialize/pickle/YAML load, XML external entities.
8. **Secrets & config** — keys in code, env files committed, secrets in logs/errors, debug mode, permissive CORS, missing security headers.
9. **Crypto** — weak algorithms, hard-coded IVs/keys, non-crypto RNG for tokens.
10. **Dependencies** — when a manifest/lockfile changed (or in a full audit), run the audit command from the project profile (wrapped by `run-heavy.sh`); report high/critical with fixed versions.
11. **Mobile (MASVS)** — secrets/tokens in plain storage (use Keychain/Keystore), exported components and deep-link validation, WebView JS bridges, TLS/pinning, excessive permissions, sensitive data in logs/screenshots.
12. **Automated abuse & resource consumption** — raw data exposure (response allowlists, enumerable IDs, unbounded list/search/export), rate limits by IP and identity, size limits and timeouts, GraphQL limits, bot and AI-crawler controls, challenges on sensitive business flows, quotas and authorization for the app's own AI features and agent APIs. Read `references/automated-abuse.md` for the controls and severity guide.

## Full audit
When the user asks to audit or pen-test the codebase, for a full / comprehensive / end-to-end security review, or for an audit report, read `references/full-audit.md` (modes, execution safety, principles, severity anchors, workflow, candidate gate, report) and pick what to hunt from `references/attack-classes.md` (core classes plus the domains matching the target). A per-task review stays on the checklist above and uses those files only to go deeper on one class.

## Rule check
For a task review, return the `## Rule check T{id}` table (`ai-dev-team:dev-team` → `references/rule-packs.md` §7) with one row per `ABUSE` rule ID (its §2–§9, when the pack is assigned) and per threat-model requirement `SEC-n` attached to the task: `pass | fail | n-o` with evidence. A `fail` is also a finding with the rule ID in its title and means `ISSUES_FOUND`.

## Finding format
```
[severity] file:line — CWE-xxx title
Data path: <source> → <sink>
Exploit: <preconditions and steps, at concept level>
Impact: ...
Fix: <concrete code-level fix>
```
Severity: `critical | high | medium | low`. Verdict: `SECURE` or `ISSUES_FOUND`.

## Structured output (workflow)
```json
{ "findings": [ { "title": "", "file": "", "line": 0, "severity": "critical|high|medium|low", "cwe": "", "scenario": "", "fix": "" } ] }
```

Never run exploits against real systems or third-party services; analysis is static plus local tests only. No load, stress, flood or fuzzing tools, active scanners or crawlers against any shared, staging or production system — see `references/automated-abuse.md` §11.
