---
name: feedback-bump-version-once-per-push
description: Bump the plugin version only once, right before a push — never per change or per commit
metadata:
  type: feedback
---

Bump `version` in `.claude-plugin/plugin.json` only once per push, right before pushing. Do not bump it for each change or each commit. Patch number only (1.0.x) unless the user asks otherwise.

**Why:** The user stated this on 2026-11-10 after versions had been bumped for every change in one session (1.0.8 → 1.0.18 before a single push), which then had to be collapsed into 1.0.9 with a force-push; machines that had already updated to 1.0.18 could not pick up 1.0.9.

**How to apply:** Before touching the version, compare it with the last pushed one (`git show origin/master:.claude-plugin/plugin.json`). If the working version is already ahead, leave it and extend the existing change log row in `CLAUDE.md` instead of adding a new version. Never lower a version that has been pushed.
