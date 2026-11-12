# Ease of use first

**Rule:** the best design is the one users finish their work with fastest and with the fewest mistakes. Looks matter, but when ease of use and looks pull apart, ease of use wins. This file is the `EASE` rule pack, used by UI design mode, every task that builds or changes a screen, and design QA.

## Contents
1. Main tasks
2. Taste
3. Checks

## 1. Main tasks
- The UI spec opens with a `## Main tasks` table: the 3–5 things users do most on the screens in scope, each with its start point and its step count — taps / clicks / keystroke fields from the start point to done, counting every screen change, menu opening and confirmation.
- Each mockup option records the step count of every main task, so the user compares options by these numbers as well as by looks; an option that adds steps to a main task says why.
- A build task that changes a main task's flow reports the step count before and after in its notes.

## 2. Taste
- The profile's `design_taste` holds the user's lasting preferences for how things look and feel (default `usability-first`; for example "bright, energetic palette; no washed-out greys"). Every UI design and UI build brief carries it.
- When the user states a preference that is not specific to one screen ("make colours brighter", "less text"), the leader adds it to `design_taste` and tells the user in one line; a preference for one screen goes into that screen's spec only.
- `design_taste` never overrides `EASE`, `REAL` or `COMPACT`; a conflict goes to the user with both choices.

## 3. Checks
1. **Ease wins on conflict** — no choice makes a main task slower or more error-prone for the sake of looks; where an option traded ease for looks, the trade is named in the notes and the user decided it.
2. **Steps counted** — the UI spec has the main-tasks table with step counts, every mockup option records them, and no main task takes more steps than the domain's common practice without a stated reason.
3. **One obvious primary action** — each screen has at most one primary action, visible without scrolling or opening a menu; on phones it sits in thumb reach (bottom area or bottom bar). Frequent actions are never hidden behind `⋯` or a long press only.
4. **Errors prevented and recoverable** — inputs that can be invalid are constrained up front (pickers, masks, disabled submit with the reason visible); errors show at the field with how to fix them, keeping what the user typed; reversible actions run at once with Undo and only irreversible ones confirm (`ai-dev-team:technical-design` → `references/record-lifecycle.md` §2).
5. **Walked as a new user** — design QA (on the mockup) and qc (on the build) walk every main task as a first-time user without reading any instructions; each point where they had to guess, go back or hunt for a control is reported as a finding with the screen and step.
