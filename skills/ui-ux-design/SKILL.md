---
name: ui-ux-design
description: "Produces a web/mobile UI spec: user flows, screen inventory, wireframes with all states, design tokens, component specs, responsive/platform rules and accessibility; plus design QA of implemented UI. Used by ui-ux-designer, or when asked to 'design screens', 'make a UI spec', 'design for mobile', or 'review the UI against the design'. Not for backend/API design (technical-design)."
---

# UI/UX design

The UI spec removes visual guesswork from implementation. A developer should be able to build every screen state from it without asking.

## Procedure
1. Read the spec (`has_ui`, `platforms`), project profile (`ui:` field) and existing UI code: components, theme/tokens, CSS/Tailwind config, navigation.
2. **Flows**: map each acceptance criterion to the screens and steps the user goes through.
3. **Screen inventory**: one entry per screen/modal/sheet.
4. **Wireframes** per screen (ASCII by default; static HTML prototype in `_workspace/` for complex layouts). Always include loading, empty, error, success and disabled states.
5. **Tokens**: reuse existing tokens; only add new ones with a reason. For new palettes/typography, consult the `ui-ux-pro-max` skill.
6. **Components**: name, props, variants, interactions, and which existing component it extends.
7. **Platform rules**:
   - Web: breakpoints (e.g. 360 / 768 / 1024 / 1440), hover vs touch, keyboard navigation.
   - Mobile: safe areas, native navigation patterns (iOS back swipe, Android back), touch targets ≥ 44pt / 48dp, offline/slow-network behavior, keyboard covering inputs.
8. **Accessibility**: contrast ≥ 4.5:1 for text, visible focus, labels for icons/inputs, logical reading order, no information by color alone.

## Visual identity (new template packs, landing / marketing pages)
App screens favor consistency with the existing template; a new template or a marketing page needs a deliberate identity instead of generated defaults.
1. **Ground it in the subject**: name the product, its audience and its world before choosing anything; every choice below must trace back to them.
2. **Plan before building**: write a compact token plan — 4–6 named colors, 1–2 typefaces with roles and a type scale, a layout concept with an ASCII wireframe, and 2–3 principles that make this design specific.
3. **Check the plan against defaults**: if it would come out the same for any similar product, revise it. Common generated-design tells to avoid unless the brief asks for them: cream background + serif display + terracotta accent; near-black background + one acid accent; identical rounded cards with the same soft shadow and decorative gradients; ALL-CAPS eyebrow labels above every heading; accenting a single word in a headline.
4. **Spend boldness in one place**: one memorable element, everything around it quiet; cut decoration that encodes no information. Structural devices (borders, numbering, labels) must carry meaning.
5. **Typography**: deliberate typefaces (not the usual defaults), clear scale, body line length under ~80 characters.
6. **Motion**: user-triggered motion follows the template's motion tokens; ambient motion is rare — one orchestrated moment beats scattered effects.
7. **Real copy**: write plausible, specific content; placeholder copy makes a design feel templated.
Use `ui-ux-pro-max` for palette, font-pairing and stack data, then filter its suggestions through the steps above.

## Template: `_workspace/02_designer_ui-spec.md`

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
## Tokens (new or changed)
## Components
| Component | Base | Props / variants | Behavior |
## Accessibility checklist
## Open questions
## Changelog
```

## Design QA
Compare the implemented UI to the spec (read code; run the app or take screenshots if the project's `run` setup allows). Report each deviation as `blocker` (missing state, broken flow, a11y failure), `major` (wrong token/layout at a breakpoint), `minor` (spacing/polish), with `file:line`.
