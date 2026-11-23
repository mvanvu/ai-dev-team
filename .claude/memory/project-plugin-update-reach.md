---
name: project-plugin-update-reach
description: What a mid-run plugin update changes in a running leader session and what it does not
metadata:
  type: project
---

After a push, a running session picks up the new plugin only when the user runs `/plugin marketplace update mvanvu` and then `/reload-plugins` (a reload alone keeps the old cached version). After that:
- hooks (`hooks/leader-guard.py`) and scripts under `$TEAM_BIN` apply at once, once the leader re-sends the new `TEAM_BIN` to running agents;
- the dev-team skill text the leader loaded at the start stays in its context, so new or changed rule wording (messages, board lines, gates) applies only after the skill is invoked again or in the next session.

**Why:** Seen on 2026-11-23: after reloading 1.0.36 a leader used the new golden-diff script and widget-image re-checks immediately (qc re-check fell from 4–9 minutes to about 1), but kept posting board lines for background-wait notices that the new text forbids.

**How to apply:** When a fix must take effect in a running run, prefer a hook or script over rule text, or tell the user to re-invoke `/ai-dev-team:dev-team` once agents are idle. Related: [[feedback-monitor-runs-workflow]].
