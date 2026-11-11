---
name: ui-ux-design
description: "Produces a web/mobile UI spec: user flows, screen inventory, wireframes with all states, design tokens, component specs, responsive/platform rules and accessibility; plus design QA of implemented UI. Used by the developer agent (UI design mode) and the reviewer agent (design QA), or when asked to 'design screens', 'make a UI spec', 'design for mobile', or 'review the UI against the design'. Not for backend/API design (technical-design)."
---

# UI/UX design

The UI spec removes visual guesswork from implementation. A developer should be able to build every screen state from it without asking.

## Procedure
1. Read the spec (`has_ui`, `platforms`), project profile (`ui:` field) and existing UI code: components, theme/tokens, CSS/Tailwind config, navigation.
2. **Flows**: map each acceptance criterion to the screens and steps the user goes through.
3. **Screen inventory**: one entry per screen/modal/sheet.
4. **Wireframes** per screen (ASCII by default; static HTML prototype in `$TEAM_WS/` for complex layouts). Always include loading, empty, error, success and disabled states; for mobile apps using online data also `offline` (banner over cached content, or a full offline screen with Retry when nothing is cached) and `reconnecting`.
5. **Tokens**: reuse existing tokens; only add new ones with a reason. For new palettes/typography, consult the `ui-ux-pro-max` skill when it is installed.
6. **Components**: name, props, variants, interactions, and which existing component it extends.
7. **Platform rules**:
   - Web: breakpoints (e.g. 360 / 768 / 1024 / 1440), hover vs touch, keyboard navigation. Pagination, resource lists and record pickers follow `ai-dev-team:pwa-headless-ui` → `references/list-page.md` (truncated pagination, one list layout for the page and the picker modal, cards on mobile, filters/sort/page in the URL); the status filter, active switch, row menu and bulk bar follow `ai-dev-team:technical-design` → `references/record-lifecycle.md`.
   - Mobile pull to refresh on every server-data list (`ai-dev-team:pwa-headless-ui` → `references/pull-to-refresh.md`): spec the indicator style, threshold haptic and which data each tab refreshes.
   - Mobile: safe areas, native navigation patterns (iOS back swipe, Android back), touch targets ≥ 44pt / 48dp, offline/slow-network behavior, keyboard covering inputs.
   - Mobile space and text (mobile web and app): no wasted space and no overflowing text — button pairs and short fields share a row, icon-left/text-right rows leave no dead space, horizontal scrollers are swipe-only with no visible scrollbar, no redundant instruction text (no subtitle restating a title, no helper text repeating a label), every text element states truncate / clamp / wrap, and wireframes use worst-case content. Rules: `ai-dev-team:pwa-headless-ui` → `references/compact-layout.md`.
8. **Accessibility**: contrast ≥ 4.5:1 for text, visible focus, labels for icons/inputs, logical reading order, no information by color alone.

## Visual identity and authenticity
Every screen must look designed for this product, not generated: real content shapes, the domain's conventions, a restrained palette, sparse consistent icons, short copy in the users' terms, and none of the generated-design tells — rules and checks in `references/authentic-design.md`. App screens favor consistency with the existing template; a new template or a marketing page additionally needs a deliberate identity:
1. **Ground it in the subject**: name the product, its audience and its world before choosing anything; every choice below must trace back to them.
2. **Plan before building**: write a compact token plan — 4–6 named colors, 1–2 typefaces with roles and a type scale, a layout concept with an ASCII wireframe, and 2–3 principles that make this design specific.
3. **Check the plan against defaults**: if it would come out the same for any similar product, revise it. Remove the tells in `references/authentic-design.md` §2; for a template or marketing page also avoid the stock palettes (cream background + serif display + terracotta accent; near-black background + one acid accent).
4. **Spend boldness in one place**: one memorable element, everything around it quiet; cut decoration that encodes no information. Structural devices (borders, numbering, labels) must carry meaning.
5. **Typography**: deliberate typefaces (not the usual defaults), clear scale, body line length under ~80 characters.
6. **Motion**: user-triggered motion follows the template's motion tokens; ambient motion is rare — one orchestrated moment beats scattered effects.
7. **Real copy**: write plausible, specific content; placeholder copy makes a design feel templated.
When `ui-ux-pro-max` is installed, use it for palette, font-pairing and stack data, then filter its suggestions through the steps above.

## Template: `$TEAM_WS/02_ui-spec.md`

```markdown
# UI Spec: <feature>
platforms: web | ios | android
## Flows
## Screens
### S1 <name>
- Purpose / entry points
- Wireframe (default state)
- States: loading / empty / error / success / disabled
- Responsive / platform notes
- Mobile density: rows shared by buttons/fields, icon-row layout, overflow rule per text element (truncate / clamp / wrap)
## Tokens (new or changed)
## Components
| Component | Base | Props / variants | Behavior |
## Accessibility checklist
## Open questions
## Changelog
```

## Design QA
Compare the implemented UI to the spec (read code and the contact sheets of this build — every width × theme per screen — from the developer and qc; capture yourself only a state no sheet shows, through `$TEAM_BIN/run-heavy.sh` — `ai-dev-team:dev-team` → `references/resource-budget.md` §1). Report each deviation as `blocker` (missing state, broken flow, a11y failure), `major` (wrong token/layout at a breakpoint; on phones: text overflowing or clipped without ellipsis, horizontal page scroll, wasted space such as stacked buttons that fit one row or dead space beside/under a row icon — `ai-dev-team:pwa-headless-ui` → `references/compact-layout.md` §7), `minor` (spacing/polish), with `file:line`.
When the task's `Rules` include a pack that names `reviewer` for design QA in `ai-dev-team:dev-team` → `references/rule-packs.md` §2 (`COMPACT`, `REAL`, `SWEEP`), also return the `## Rule check T{id}` table: one row per rule ID, `pass | fail | n-o` with evidence (`file:line` or screenshot); a `fail` is a deviation with the rule ID in its title.
