# Request research before planning

When the user agrees, a short research step turns the request into concrete, sourced options before the spec questions start, so the user corrects a proposal instead of answering abstract questions one by one. It runs in parallel with the leader's own preparation and is time-boxed, so it adds little or no waiting.

## Contents
1. When it is offered
2. Running it
3. Output
4. Reuse and privacy
5. `RESEARCH` checks

## 1. When it is offered
- Only for a new feature, a new product, a greenfield project, or a request whose plan will likely have 4 or more tasks. Never on the bug route, light tier (small change, layout complaint) or review-only route.
- The leader asks once, in the first AskUserQuestion it makes anyway (with `Presence` and the Fable policy), header `Research`: `Research first (≈5–8 min, runs while I profile)` / `No, plan as usual`. No → Phase 2 runs as before. A user who says "research it" or "look at how others do it" has answered yes.
- An ambiguous word that would send the research to two different targets ("the app" = web or mobile) is asked before research starts; any other ambiguity is researched both ways and shown as two options.

## 2. Running it
- Started right after the answer, in the background, while the leader does Phase 0/1 and asks its other questions.
- **Lenses**, one agent each, only the ones the request needs (often one or two):
  - **Product and UX** — 4–6 comparable products or public examples: main flows, what users expect as standard, what sets products apart. Skipped when the request has no UI.
  - **Technical** — first what the repo and the systems it talks to already have (`$TEAM_STATE/capabilities.md`, the profile, existing integrations), then common approaches and libraries with current versions (official docs, release pages) and what fits this stack.
  - **Risk** — security, automated abuse, data and legal constraints, failure cases the request implies.
- Lens agents: a general-purpose agent or `reviewer` on `sonnet` with WebSearch/WebFetch, read-only in the repo; each has a hard limit of about 4 minutes and 10 searches and returns what it has when the limit is reached. One synthesis agent on `opus` (or `fable` under the run's Fable policy for a greenfield product) merges the lens notes into the output below in about 2 minutes. All of them count against `max_agents` as verifiers.
- Lens notes go to `$TEAM_WS/00_research/<lens>.md`; the synthesis to `$TEAM_WS/00_research.md`.

## 3. Output
`$TEAM_WS/00_research.md`:
- The request restated in one paragraph, with each reading when there is more than one.
- **What the project already has** that the request can build on (paths), and what is missing.
- References: product, page or doc, what it shows, the date it was read.
- **3–5 options**, each split into `core` (what the user asked for), `expected` (what users of this kind of product take for granted; missing it feels broken) and `optional` (good ideas, each with a rough cost in tasks); pros, cons, risks; exactly one marked Recommended.
- Open questions that remain, each with a proposed default.

The leader shows the user a short summary (options, the recommendation, the optional items) and asks with AskUserQuestion: the option, and the optional items as a multi-select. What the user picks goes straight into the spec; brainstorming or `spec-writing` then asks only what is still open and never re-asks what was settled here.

## 4. Reuse and privacy
- Results are kept in `$TEAM_STATE/research/<topic>.md` (committed with the team files). A later request in the same area starts from that file and only refreshes what is older than about 90 days or does not cover the new question. The UI design research of `DESIGN-11` reads it before searching again.
- Search queries describe the domain in general terms. They never contain the project's name, client names, internal URLs, code, data or credentials.
- Learn patterns, never copy: no other product's name, logo, text or screens go into the options (`REAL`).

## 5. `RESEARCH` checks
1. **Asked first** — the research ran only after the user chose it (or asked for it), and only on a route of §1.
2. **Private queries** — no query or fetched URL carried the project's name, client names, internal hosts, code or data.
3. **Sourced** — every claim about another product, library version or practice names its source and the date it was read; anything inferred is marked as inferred.
4. **Options** — 3–5 options split into core / expected / optional with pros, cons and rough cost; exactly one Recommended; what the repo already has is listed before anything new is proposed.
5. **Time-boxed** — each lens stopped at its limit and the synthesis was ready before or soon after the leader's own preparation; no lens repeated research a stored `$TEAM_STATE/research/` file already covered.
6. **Carried over** — the spec records the user's picks, and later questions did not ask them again.
