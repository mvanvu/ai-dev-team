---
name: feedback-monitor-runs-workflow
description: When monitoring live dev-team runs, implement recommended fixes, commit locally, notify the run sessions; bump and push only on the user's word
metadata:
  type: feedback
---

While monitoring live dev-team runs in other projects, a recommended plugin fix is implemented right away, committed locally (no bump), and announced to the run's session; the version bump and push wait until the user says "bump … rồi push".

**Why:** The user set this flow on 2026-11-23 ("nếu có đề xuất được khuyến nghị thì commit local rồi gửi tin nhắn"), then asked for bump + push separately each time. A "why is it slow" question still gets an analysis with proposals first; "làm hết đi" approves them.

**How to apply:**
- Read the run's transcript under `~/.claude/projects/<project>/` with a follower script through Monitor (30-minute expiry, re-arm).
- Before naming a root cause in a rule or change log row, confirm it from the run (agent report or code) — a guessed cause had to be rewritten once.
- Change log rows of already pushed versions are never edited; new work goes in the unpushed row ([[feedback-bump-version-once-per-push]]).
- Sessions running under another claude-swap account do not show in ListAgents; give the user a paste-in message instead of SendMessage.
- Rule text reaches a running leader only after it reloads the dev-team skill; hooks and scripts apply right after `/plugin marketplace update` + `/reload-plugins` ([[project-plugin-update-reach]]).
