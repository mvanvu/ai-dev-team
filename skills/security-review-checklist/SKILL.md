---
name: security-review-checklist
description: "Threat-modeling template and vulnerability review checklist (OWASP Top 10, OWASP MASVS for mobile, authn/authz, secrets, dependencies) with finding format and structured output. Used by security-auditor and the dev-team final review workflow. For a full standalone codebase audit or pen-test report, use the global security-audit skill instead."
---

# Security review checklist

## Threat model (design phase): `_workspace/02_security_threat-model.md`
```markdown
# Threat model: <feature>
## Assets (data/capabilities worth protecting)
## Trust boundaries & data flows
## Threats (STRIDE per flow)
| Flow | Threat | Category | Likelihood | Impact | Mitigation → task |
## Security requirements for implementation
- SR1: ...
```

## Code review checklist
1. **Injection** — SQL/NoSQL, OS command, LDAP, template injection; trace every untrusted input to its sink.
2. **Broken access control** — authorization on every endpoint/handler/resolver; IDOR (object IDs from the client); privilege escalation via mass assignment.
3. **Authentication & sessions** — password storage (bcrypt/argon2), JWT validation (alg, expiry, signature), session fixation, CSRF on state-changing requests, rate limiting on login/OTP.
4. **XSS & output** — unescaped output, `dangerouslySetInnerHTML`/`v-html`/`|raw`, unsafe URL schemes.
5. **SSRF & redirects** — user-controlled URLs fetched server-side; open redirects.
6. **Files** — path traversal, upload type/size validation, serving uploads from an executable path.
7. **Deserialization & XXE** — unsafe unserialize/pickle/YAML load, XML external entities.
8. **Secrets & config** — keys in code, env files committed, secrets in logs/errors, debug mode, permissive CORS, missing security headers.
9. **Crypto** — weak algorithms, hard-coded IVs/keys, non-crypto RNG for tokens.
10. **Dependencies** — when a manifest/lockfile changed (or in a full audit), run the audit command from the project profile (wrapped by `run-heavy.sh`); report high/critical with fixed versions.
11. **Mobile (MASVS)** — secrets/tokens in plain storage (use Keychain/Keystore), exported components and deep-link validation, WebView JS bridges, TLS/pinning, excessive permissions, sensitive data in logs/screenshots.

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

Never run exploits against real systems or third-party services; analysis is static plus local tests only.
