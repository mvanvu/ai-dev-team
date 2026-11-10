---
name: spec-writing
description: "Writes a feature spec: goal, scope, Given/When/Then acceptance criteria, edge cases, non-functional constraints, has_ui/security_sensitive flags and open questions. Used by architect (spec mode), or when asked to 'write a spec', 'analyze requirements', or 'write acceptance criteria'. Not for technical design (use technical-design)."
---

# Spec writing

A good spec lets three different people (designer, developer, QA) read it and understand the same thing. The test: every acceptance criterion converts directly into one test.

## Procedure
1. Read the request, the project profile and related code (models, routes, existing screens).
2. Separate the goal (why) from the solution (how) — record only goals and constraints.
3. Write acceptance criteria. Each one: a single observable behavior with concrete data.
   - Good: `Given a cart with 2 items, When the user removes 1, Then the total updates and 1 line remains`.
   - Bad: `The cart works well`.
4. Walk the edge-case list: empty data, very large data, malformed input, duplicates, concurrency, network loss (mobile apps using online data always get acceptance criteria for the offline screen/banner and automatic reconnect to the same screen), missing permission, expired session, i18n/time zones.
5. Set flags `has_ui` and `security_sensitive` (auth, authorization, PII, payments, uploads, external input, third-party integrations).
6. Open questions: only ask what changes behavior; each comes with a proposed default.

## Template: `_workspace/01_architect_spec.md`

```markdown
# Spec: <feature name>
flags: has_ui=<true|false>, security_sensitive=<true|false>, platforms=<web|ios|android|...>

## Goal
## Users & context
## Scope
- In scope:
- Out of scope:
## Acceptance criteria
- AC1: Given … When … Then …
## Edge cases
## Non-functional constraints
## Open questions
- Q1: … (proposed default: …)
```

Bug fix: replace "Goal" with "Current behavior / Expected behavior / Steps to reproduce".
