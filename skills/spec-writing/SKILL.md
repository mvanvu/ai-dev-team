---
name: spec-writing
description: "Writes a feature spec: goal, scope, Given/When/Then acceptance criteria, edge cases, non-functional constraints, has_ui/security_sensitive flags and open questions. Used by the dev-team leader when superpowers is not installed (and as the header and AC format any spec must have), or when asked to 'write a spec', 'analyze requirements', or 'write acceptance criteria'. Not for technical design (use technical-design)."
---

# Spec writing

A good spec lets three different readers (developer, reviewer, qc) read it and understand the same thing. The test: every acceptance criterion converts directly into one test.

## Procedure
1. Read the request, the project profile and related code (models, routes, existing screens).
2. Separate the goal (why) from the solution (how) — record only goals and constraints.
3. Write acceptance criteria. Each one: a single observable behavior with concrete data.
   - Good: `Given a cart with 2 items, When the user removes 1, Then the total updates and 1 line remains`.
   - Bad: `The cart works well`.
4. Walk the edge-case list: empty data, very large data, malformed input, duplicates, concurrency, network loss (mobile apps using online data always get acceptance criteria for the offline screen/banner and automatic reconnect to the same screen), missing permission, expired session, i18n/time zones. Media and file features add: animated formats (GIF, animated WebP, APNG) that a static conversion would freeze, SVG, HEIC, transparency, EXIF orientation, very large dimensions.
   - **Removed or replaced behavior**: when the change removes a feature or replaces a mechanism (a manual rebuild, a cleanup job, a setting), list what it used to create, clean up or repair (stored files, cache entries, rows, jobs) and write an acceptance criterion for who does that now — a prune command, a migration, or an explicit "kept as is" the user agreed to.
5. Set flags `has_ui` and `security_sensitive` (auth, authorization, PII, payments, uploads, external input, third-party integrations).
6. Open questions: only ask what changes behavior; each comes with a proposed default.

## Template: `$TEAM_WS/01_spec.md`

```markdown
# Spec: <feature name>
flags: has_ui=<true|false>, security_sensitive=<true|false>, platforms=<web|ios|android|...>

## Goal
## Users & context
## Scope
- In scope:
- Out of scope:
## Acceptance criteria
- AC-1: Given … When … Then …
## Edge cases
## Non-functional constraints
## Open questions
- Q1: … (proposed default: …)
```

A spec written with `superpowers:brainstorming` gets the `flags:` line and `AC-n` numbering added by the leader; the rest of its structure stays.

Bug fix: replace "Goal" with "Current behavior / Expected behavior / Steps to reproduce".
