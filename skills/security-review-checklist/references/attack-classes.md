# Attack classes

What to hunt in a full audit (`full-audit.md` §5) or a deep review. Condensed and adapted from Cloudflare's `security-audit` skill (MIT — see `THIRD-PARTY-NOTICES.md` at the plugin root). Pick the core classes that fit the target, add the domains that match it, and split large codebases per subsystem. Every item still has to pass the candidate gate: a named principal, a crossed boundary and a concrete result.

## Contents
1. Core classes
2. Web protocol and authentication
3. Client side and browser
4. Data isolation and lifecycle
5. Resource exhaustion and availability
6. AI, LLM and agents
7. Protocols, RPC and messaging
8. Supply chain and release
9. Cloud and deployment
10. Desktop, mobile and local IPC
11. Memory safety and binaries

## 1. Core classes
- **Injection** — trace untrusted input from entry to sink: SQL and other queries, HTML, shell, templates, file paths, redirects, deserialization, format strings, logs, LDAP/XPath. Also indirect paths: stored safely then used dangerously by other code; injection through field names, keys, headers and metadata; injection into logs, caches, search indexes and analytics.
- **Access control** — not whether a check exists but whether it is the right permission, for the right resource, by the right mechanism. A second path to the same state change with a weaker check; a body field overriding what permissions restrict; authentication without authorization; inconsistent checks across access paths; bulk, batch, export and import skipping per-item checks.
- **Resource and file handling** — path traversal (symlinks, encodings, null bytes); SSRF (redirects, DNS rebinding, URL-parser differentials); unsafe deserialization; archive extraction outside the target directory; temp files; check-then-use races on files.
- **Cryptography and secrets** — weak randomness for tokens, keys, nonces; secrets in source, logs, errors, URLs or client responses; broken key derivation, missing MAC verification, nonce reuse; non-constant-time secret comparison; ECB, unauthenticated encryption, static IVs; error paths that fall back to no crypto.
- **Business logic** — skipped, repeated or reversed workflow steps, replay of a completed flow, partial failure without rollback; non-atomic check-then-act (double spend, double approve, lost update); negative, zero, overflowing or coerced quantities; a restriction on one operation bypassed through another with the same effect; stored data trusted because "it was validated on the way in"; expiry, rate-window, clock-skew and time-zone boundaries; posture when config is missing, a flag is off, a dependency is down or a migration is half done.
- **Feature abuse and leakage** — export or backup returning data above the caller's access (other users', deleted, draft, history); import or restore that overwrites, bypasses validation or writes where the caller cannot; search, filter and sort as an oracle for hidden records or fields; enumeration through differing errors, status codes, sizes or timing (reset, invite, signup); preview/draft tokens unlocking more than one item, drafts visible in search, feeds, sitemaps or CDN caches; user-supplied webhook or callback URLs fetched by the server.
- **Chains and trust gaps** — what a low-privilege principal can read, write, invoke and retain, connected to later trust decisions; component A's exact guarantee versus what B assumes (truncation, coercion, normalization, tenant scope); second-order use (a field name becomes a JSON path, a slug a file path, a string a URL, regex or template); token, API-key, plugin or OAuth scope growing after delegation, refresh, caching or role change; stale state accepted across setup, soft-delete, revoke and cache-expiry windows; undelete, restore and rollback skipping current ownership and validation.
- **Wildcard** — strange, half-finished, experimental, legacy and fallback code; API calls the UI never makes; undocumented endpoints, parameters and headers in route and middleware registration; features never designed to combine (localization + preview + caching, import + plugins + webhooks); reverted fixes and removed secrets in git history; what the tests do not test.
- **Obvious things** — hardcoded credentials and keys; `TODO/FIXME: auth`; debug or dev mode reachable in production; seed credentials; unprotected `/debug`, `/admin`, `/metrics`, `/env`, `/config`; committed `.env`, `*.pem`, `*.key`; unpinned dependencies and known CVEs; `eval`, `exec`, dynamic `import` on input; wildcard CORS with credentials; cookies missing `HttpOnly`/`Secure`/`SameSite`; open redirects; missing TLS; stack traces and SQL errors in responses. A flag is not a finding — trace the impact first.

## 2. Web protocol and authentication
- **HTTP framing and caches** — front end and back end disagreeing on request length or header normalization (request smuggling); cache poisoning through input that changes the response but is not in the cache key; private dynamic responses cached as static assets; untrusted `Host` / forwarded headers used for absolute URLs, tenant routing, reset links or client IP; untrusted data in `Location`, `Set-Cookie` or CSP.
- **Browser sessions** — state-changing, cookie-authenticated endpoints without an effective CSRF defense (including JSON-like, multipart, method-override and legacy routes); session IDs not rotated on login, MFA completion or impersonation, or still valid after logout, password change, revocation or account disable; over-broad cookie `Domain`/`Path`.
- **Federated identity** — JWT: signature verified, algorithm and key source pinned server-side, `exp`/`nbf`/`aud`/`iss` checked, `kid`/`jku`/`x5u` treated as untrusted, no decode-without-verify path, tokens for another service rejected. OAuth/OIDC: exact `redirect_uri`, session-bound `state`, PKCE, ID-token issuer/audience/nonce, selected-IdP binding; callback, retry, deep-link and account-link routes compared. SAML: the signed element is the element used; safe XML parsing; audience, recipient, validity and replay checks.
- **MFA and account transitions** — MFA enrollment or removal without re-authentication, fallback to a weaker factor; step-up not bound to the action it protects; WebAuthn challenge, origin and user-verification checks; account linking by unverified email (identity collision); password reset and recovery — token entropy, single use, expiry, binding to the account, host-header poisoning of the link, session invalidation afterwards.
- **API keys and mTLS** — key scope not bound to the resource or tenant; keys in URLs, logs or client code; peer certificate identity confused with application identity; fallback to unauthenticated when certificate checks fail.

## 3. Client side and browser
- **DOM and object state** — DOM XSS (sources: URL, storage, `postMessage`, API data → sinks: `innerHTML`, `v-html`, `dangerouslySetInnerHTML`, `eval`, URL attributes); DOM clobbering; prototype pollution reaching a gadget.
- **Cross-origin** — `postMessage` handlers that do not check `origin` and `source`, or send to `*`; WebSocket handshakes authenticated by cookies without an origin check; CORS reflecting arbitrary origins with credentials.
- **Service worker and storage** — worker scope or registration controllable by untrusted content; caches serving one user's authenticated response to another or after logout; tokens and personal data in `localStorage`/IndexedDB readable after XSS or on shared devices; stale authorization in client state; cross-tab `BroadcastChannel` or storage events trusted without checks.
- **Leaks and UI redress** — cross-site state oracles (frame counts, timing, error events, redirects); `window.opener` exposure; clickjacking on sensitive actions (`frame-ancestors`); client-side routing or redirect parameters that navigate to attacker-chosen destinations.

## 4. Data isolation and lifecycle
- **Tenant and object isolation** — queries missing the tenant or owner predicate (IDOR/BOLA), especially by-ID, bulk and nested routes; composite-key and namespace collisions; policy layer and query disagreeing on scope; blob and signed URLs valid for more objects, longer or for other principals than intended.
- **Derived data** — search indexes, caches and materialized views that do not carry the source ACL; analytics, logs, traces and diagnostics as an alternate reader of protected data; counts, aggregates and autocomplete as oracles.
- **Export, backup, restore, migration** — export or backup wider than the caller's access; import or restore setting owner, tenant, role or IDs the caller could not set directly; migrations defaulting ownership or visibility to something permissive; replicas and backups under weaker access rules.
- **Deletion and revocation** — soft-deleted or trashed records still readable or usable as references through another path; revoked access still honored by caches, tokens, queued jobs or derived copies; retention overrun; restore bringing back state that current rules forbid.

## 5. Resource exhaustion and availability
Count only effects on shared resources or other principals, shown locally with bounded input — never by stressing a live service. See also `automated-abuse.md`.
- **Amplification** — superlinear regex, parsing or evaluation; decompression and nested-structure bombs; one request fanning out into unbounded queries or downstream calls.
- **Accumulation** — unbounded buffers, collections, cardinality or pagination; leaked handles and temp files; work that continues after the client cancels.
- **Quotas and scheduling** — expensive work before authentication; quotas scoped or reset so they can be multiplied (per key instead of per account, per route instead of global); one tenant starving shared workers, pools or queues.
- **Failure and recovery** — input reaching a fatal error or deadlock in a shared process; retry storms and fail-open behavior; a poison message blocking a queue; recovery that drops limits.

## 6. AI, LLM and agents
- **Context and memory** — instructions in retrieved or ingested content steering the model (indirect prompt injection); context, cache or memory shared across sessions or tenants; persistent memory poisoned by one interaction and trusted later; user or tool text able to pose as a system/developer message.
- **Tools and actions** — model-produced tool arguments reaching SQL, shell, file paths or URLs without validation; the agent acting with more authority than the requesting user (confused deputy); confirmation not bound to the final action, target and arguments; tool schema and dispatcher disagreeing on what is allowed; unbounded action loops and spend.
- **MCP and sub-agents** — sub-agents or MCP servers inheriting broader credentials than the task needs; tool identity confusion (same name, different server); tool descriptions and schemas treated as trusted policy.
- **Output** — model output rendered as HTML/Markdown, links or images without sanitization (exfiltration through URLs); system prompt, secrets or other users' data extractable from context.

## 7. Protocols, RPC and messaging
- **Framing and schema** — sender and receiver disagreeing on message boundaries or canonical form; unknown enum, union and default values taking a privileged branch; identity in the envelope differing from identity in the payload.
- **RPC authorization** — interceptors or middleware not covering every method or transport; transport peer identity mistaken for the application principal; authorization once per stream or batch instead of per item; replies or callbacks correlated to the wrong caller.
- **Brokers and queues** — topic, routing-key and subscription scope letting one tenant publish or read another's messages; sensitive payloads in dead-letter queues, retries and diagnostics; any producer able to send control messages.
- **Replay and ordering** — duplicate delivery without idempotency; stale or out-of-order messages accepted; acknowledge-before-commit and commit-before-acknowledge losing or repeating effects; webhooks without signature, timestamp and replay protection.

## 8. Supply chain and release
- **Dependencies and build inputs** — dependency-confusion and typo-squat exposure, unscoped private names; unpinned or mutable inputs (tags, `latest`, unverified downloads, install scripts); generated code with unverifiable provenance; secrets or unrelated files inside build contexts and images.
- **CI and automation** — untrusted code (fork PRs) running in workflows with secrets or write tokens; expression and command injection from PR titles, branch names and issue text; caches and artifacts shared between trusted and untrusted jobs; over-scoped automation tokens.
- **Release and update** — the artifact that is promoted not being the one that was built and reviewed; release or signing possible without the required approval; update metadata allowing rollback or substitution; plugins and extensions gaining host authority.

## 9. Cloud and deployment
- **Identity and IAM** — workload roles broader than the workload needs; cross-account or cross-tenant role assumption without binding conditions; application authorization derived from cloud metadata or labels a tenant can set.
- **Network and control plane** — admin, debug, metrics or internal services reachable from outside; trusting proxy or mesh identity headers that clients can forge; metadata endpoints and internal services reachable through SSRF.
- **Containers and orchestration** — privileged containers, host mounts, the container runtime socket, service-account tokens with cluster-wide rights; admission and policy paths that differ by route; namespace or label trust that a tenant can influence.
- **Configuration and secrets** — an environment overlay silently disabling a control; secrets readable across workload boundaries or baked into images and state files; expired credentials falling back to something weaker.
- **Storage, events, edge** — public or over-broad bucket and signed-URL policies; event handlers not verifying the event source; logic split between edge and origin with mismatched assumptions.

## 10. Desktop, mobile and local IPC
See also OWASP MASVS in `SKILL.md`.
- **Deep links and handoff** — custom schemes any app can claim; deep links and universal links driving sensitive actions without validation or confirmation; OAuth and login handoff returning to the wrong app or account; file-open and intent parameters treated as trusted.
- **Webview and bridges** — native bridges exposed to any origin the webview navigates to; bridges offering more capability than the page needs; file and universal access enabled; remote content loaded with the app's privileges.
- **Local IPC and exported components** — sockets, XPC/Binder/D-Bus services and exported activities, services, receivers and providers that do not authenticate the peer or that trust a caller-claimed identity.
- **Privileged helpers and local files** — a helper performing actions for an unprivileged caller without checking it; install, update and repair paths trusting writable locations; world-readable files, TOCTOU on local paths; secrets outside the platform keystore.
- **App state** — data, tokens and caches surviving logout, account switch or device restore; pending actions executed under a different user or without the required user presence.

## 11. Memory safety and binaries
For C/C++, unsafe Rust, parsers, FFI, JITs, kernel modules and firmware.
- **Bounds and integers** — out-of-bounds reads and writes; overflow, truncation and signedness in size and index arithmetic; unit and pointer-depth confusion; uninitialized or partially initialized data returned or copied out.
- **Lifetime, type, concurrency** — use-after-free, stale views, double free; type confusion and invalid downcasts; reference-count and ownership races; shared-state races and TOCTOU; lock-order deadlocks.
- **FFI and ABI** — pointer/length and ownership contracts differing across the boundary; layout, alignment and enum disagreements; exceptions or unwinding crossing the boundary.
- **Loading and runtime** — library, plugin and executable search-order hijack; artifacts loaded without identity or signature checks; malformed binary metadata; generated-code and JIT consistency; unload and teardown while still in use.
- **Privileged interfaces** — user-copy bounds and double fetches; privileged object lifecycle; powerful interfaces (ioctl, syscalls, device nodes) without sufficient authorization.
