# Automated abuse: scrapers, bots, AI crawlers and AI agents

Automated clients can pull raw data out of an app in bulk, or exhaust its resources until it is effectively down (DoS) or too expensive to run. AI clients are now a large share of this traffic, so they get the same scrutiny as any other bot: AI training and search crawlers, LLM-driven agents and browser automation, and abuse of the app's own AI features.

References: OWASP API Security Top 10 2023 — API1 (BOLA / enumeration), API3 (excessive property exposure), API4 (Unrestricted Resource Consumption), API6 (Unrestricted Access to Sensitive Business Flows); OWASP Top 10 for LLM Applications 2025 — LLM01 (Prompt Injection), LLM02 (Sensitive Information Disclosure), LLM10 (Unbounded Consumption); CWE-200, CWE-400, CWE-639, CWE-770, CWE-799.

## Contents
1. Threat model rows
2. Raw data exposure
3. Rate limits and quotas
4. Resource exhaustion
5. Bots and AI crawlers
6. Sensitive business flows
7. The app's own AI features and agent access
8. Edge and infrastructure
9. Mobile and PWA clients
10. Severity guide
11. Verifying without causing harm

## 1. Threat model rows

For every public or semi-public flow (unauthenticated pages and APIs, search, listing, export, signup, login, OTP, contact/comment forms, AI endpoints, webhooks), add at least one row:

| Flow | Threat | Category | Likelihood | Impact | Mitigation → task |
|---|---|---|---|---|---|
| `GET /api/products` | Scraper or AI crawler harvests the full catalog and prices | Information disclosure | High | Medium | Page size cap, rate limit per IP/key, bot management at the edge → T4 |
| `POST /api/chat` | Agent loops requests to run up LLM cost | Denial of service | Medium | High | Per-user token quota, max steps, budget alert → T6 |

Whether AI crawlers may index or train on public content is a **product decision**: record it as an open question for the user with a proposed default (allow search crawlers, block training crawlers), not as a security choice made silently.

## 2. Raw data exposure

- Responses come from an explicit allowlist (DTO, serializer, resource, GraphQL field auth), never raw ORM rows or `SELECT *`; internal fields (ids of other tenants, emails, cost, flags, timestamps that leak behavior) are not serialized.
- Data meant for logged-in users is not embedded in public HTML, SSR hydration state, JSON-LD, sitemaps, RSS or cached public responses.
- Identifiers on public resources are not enumerable: random IDs (UUID v4 or similar) or slugs, and object-level authorization on every lookup — sequential IDs plus a missing check is a full-table dump.
- No unauthenticated "list all", bulk export or unbounded search; exports need authentication, authorization, a rate limit and an audit log entry.
- Pagination: server-enforced maximum page size, cursor pagination for large sets, a cap on `offset`/total reachable results; search requires a minimum query length.
- Error messages and timing do not reveal whether a record exists for enumeration-sensitive lookups (accounts, emails, phone numbers).

## 3. Rate limits and quotas

- Limits by IP **and** by authenticated identity (user, API key, tenant) — IP-only limits are bypassed by rotating proxies, identity-only limits miss anonymous traffic.
- Stricter limits on expensive or sensitive endpoints: search, export, reports, file processing, AI calls, login, OTP/SMS/email sending, signup, password reset.
- Counters live in a shared store (Redis or the gateway), not per-process memory that resets per instance.
- Respond `429` with `Retry-After`; daily/monthly quotas for API keys and paid features.
- Webhooks and callbacks from third parties are verified (signature) and limited too.

## 4. Resource exhaustion

- Request body, JSON depth, multipart and upload size limits; decompression limits (zip/gzip bombs); image dimension limits before decoding.
- Timeouts everywhere: HTTP server, DB statement timeout, outbound calls, background jobs.
- GraphQL: depth, complexity/cost, alias and batch limits; persisted queries for public clients where possible.
- No user-controlled regex or ReDoS-prone patterns on input; bounded `IN` lists, sort fields from an allowlist, no user-controlled unindexed filters on large tables.
- Heavy work (reports, exports, media processing) runs as queued jobs with per-user concurrency limits, not inline in the request.
- Public read endpoints are cacheable (CDN / HTTP cache headers) so repeated scraping hits the cache, not the origin.

## 5. Bots and AI crawlers

- `robots.txt` reflects the product decision from section 1, with explicit groups for AI crawlers (e.g. `GPTBot`, `ClaudeBot`, `CCBot`, `Google-Extended`, `Applebot-Extended`, `PerplexityBot`, `Bytespider`) — check current user-agent names when writing it. `robots.txt` is advisory: it stops well-behaved crawlers only.
- Enforcement happens at the edge: WAF / bot management (e.g. Cloudflare bot management and AI crawler controls, AWS WAF Bot Control) or equivalent rules. Verified good bots are identified by reverse DNS or published IP ranges, not by user agent, which is trivially spoofed.
- Headless and agent traffic on sensitive flows is challenged (section 6), not trusted because it executes JavaScript.
- Content that must not be scraped is behind authentication; obfuscation in the frontend is not a control.

## 6. Sensitive business flows

Flows that cost money or harm users when automated — signup, checkout, booking/reservation holds, coupon/voucher redemption, OTP/SMS sending (SMS pumping fraud), contact/comment/review forms, invitations:
- A challenge on suspicious traffic (Turnstile, reCAPTCHA, hCaptcha, or proof-of-work), per-account and per-device limits, and cool-downs.
- Login: limits per account and per IP, breached-password check, MFA option, generic error messages (credential stuffing).
- SMS/OTP: per-number and per-country limits, block premium-rate prefixes, cost alerts.

## 7. The app's own AI features and agent access

- Per-user and per-tenant request and token quotas, max input and output tokens, max agent steps / tool-call loops, request timeouts, and a provider budget cap with alerts (LLM10 Unbounded Consumption — cost exhaustion is a DoS).
- Tools and retrieval called by the model go through the **same authorization as the user** who triggered them; the model never gets a broader data scope than that user (LLM02).
- Content retrieved from users, the web or documents is treated as untrusted input to the model (indirect prompt injection, LLM01); tool calls with side effects need confirmation or strict allowlists.
- System prompts, API keys and other tenants' data never appear in model context that can be echoed back.
- APIs or MCP servers the app exposes for AI agents require authentication, scoped tokens, rate limits and audit logs like any other API.

## 8. Edge and infrastructure

- A CDN/WAF sits in front of public traffic and the origin only accepts traffic from it (origin IP allowlist or authenticated origin pulls).
- Autoscaling has upper bounds and budget alerts, so an attack becomes degraded service, not an unbounded bill.
- Monitoring alerts on spikes in 429s, 4xx/5xx ratios, per-client request volume and AI token spend; logs carry a client identifier for blocking.

## 9. Mobile and PWA clients

- API keys shipped in a web bundle or mobile binary are public; they identify the app, they do not authenticate it.
- For high-value APIs, use App Attest / DeviceCheck (iOS) and Play Integrity (Android) for native apps, plus the server-side controls above for web clients.

## 10. Severity guide

| Finding | Severity |
|---|---|
| Unauthenticated endpoint returning bulk personal or confidential data, or enumerable IDs without object-level authorization | high–critical |
| No rate limit on login, OTP/SMS, password reset or a paid/AI endpoint | high |
| AI endpoint without per-user token/cost quota | high |
| Missing server-side page size cap, body size limit or timeout on a public endpoint | medium |
| Expensive public endpoint without caching or job queue | medium |
| `robots.txt` missing the recorded AI-crawler decision | low |

## 11. Verifying without causing harm

- The auditor checks these controls by reading code and configuration (middleware, gateway/WAF config, ORM queries, serializers, `robots.txt`). It never runs load, stress, flood or fuzzing tools, active scanners or crawlers against any shared, staging or production system or third-party service.
- A rate limit may be demonstrated only against a **local** instance with test data, using a small burst just over the limit (limit + a few requests), sequentially, then stopped.
- Destructive or data-modifying probes are never run; describe the exploit at concept level in the finding instead.
