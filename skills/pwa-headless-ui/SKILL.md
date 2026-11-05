---
name: pwa-headless-ui
description: "How to build a mobile-first PWA in Vue 3 or React + TypeScript on a headless core-component architecture with swappable template packs (Reka UI / Radix UI / React Aria), PWA setup (manifest, service worker, offline, updates), and Capacitor wrapping the PWA's HTTPS URL. Used by pwa-frontend-engineer, or when asked to add a core component, create/switch a UI template or theme, set up the PWA, or configure Capacitor. Not for backend work (implementation) or visual design specs (ui-ux-design)."
---

# PWA + headless UI + Capacitor

## Goal of the architecture
One codebase → responsive PWA (mobile-first, desktop-ready) → native apps via Capacitor. The look is a **replaceable template pack**: changing or adding a template must not touch any core or feature component.

## The three layers

```
features/pages  ──imports only──▶  ui/core  ──uses──▶  headless primitives (reka-ui | radix-ui | react-aria-components)
                                      │
                                      └──reads styles from──▶  active template (tokens.css + recipes + shells)
```

| Layer | Location | Owns | Must not |
|---|---|---|---|
| Headless primitives | npm package | behavior, focus, ARIA | be imported outside `src/ui/core` |
| Core components | `src/ui/core/` | typed props API, composition, a11y, slots | contain visual classes or colors |
| Template packs | `src/templates/<name>/` | CSS variables, per-component style recipes, layout shells | contain behavior or business logic |
| Features | `src/features/`, `src/pages/` | screens, data fetching | import primitives or templates |

Library choice:
- **Vue 3** → `reka-ui` (the successor of Radix Vue).
- **React** → `radix-ui` primitives by default; `react-aria-components` when the spec needs heavy i18n / complex accessibility (date pickers, comboboxes).
- Styling engine: Tailwind CSS v4 + CSS variables + a recipe helper (`tailwind-variants` or `class-variance-authority`). Recipes return class strings; tokens live in CSS variables so a template can restyle without rebuilding components.

Read `references/architecture.md` for the template contract, provider, core component examples (Vue and React), directory layout and lint enforcement.

## Procedure for a frontend task
1. Read the task, the design contracts and the UI spec section.
2. Need a component the core layer lacks? Add it to `src/ui/core/` first (with behavior tests), add its recipe slot to the `UiTemplate` contract, then implement the recipe in **every** existing template (the compiler will list the ones you missed).
3. Build the feature screen using only core components. Mobile layout first; add `md:` / `lg:` enhancements and the desktop shell second.
4. Implement every UI-spec state (loading, empty, error, success, disabled).
5. Run: type-check (`vue-tsc --noEmit` or `tsc --noEmit`), lint, unit tests, production build. Record real output in task notes.
6. Verify at 360px and 1280px widths (screenshot via the `run` skill or Playwright when available).

## Adding a new template
1. Copy `src/templates/default/` to `src/templates/<name>/`.
2. Change only `tokens.css`, recipes and shells. Type-check must pass — it proves the contract is complete.
3. Register it in `src/templates/index.ts`; select it by env (`VITE_UI_TEMPLATE`) or at runtime via the provider.
4. Run the full component test suite against the new template — behavior must be identical.

## Mobile-first rules
- Base styles target ~360px; enhance with `sm/md/lg/xl` breakpoints. Never write desktop-first then override down.
- Touch targets ≥ 44px; no hover-only interactions; use `:focus-visible`.
- Respect safe areas: `viewport-fit=cover` + `env(safe-area-inset-*)` padding in shells.
- Use `dvh` units for full-height layouts (mobile browser bars).
- Adaptive shells: `MobileShell` (bottom nav, top app bar) and `DesktopShell` (sidebar, wider content) chosen by a media-query composable/hook, both supplied by the template.

## Native feel
The PWA must feel like a native app: gesture-driven navigation that follows the finger, direction-aware page transitions, bottom sheets, haptic feedback, virtualized 60fps lists, optimistic updates, and instant launch from a persisted cache. Read `references/native-feel.md` for the library stack (Vue: `motion-v`, `@vueuse/core`, `vue-sonner`, `@tanstack/vue-virtual`, `@tanstack/vue-query`; React: `motion`, `sonner`, `@tanstack/react-virtual`, `@tanstack/react-query`; both: View Transitions API, `@capacitor/haptics`), the core components that wrap them, motion tokens in templates, the touch CSS baseline, and the performance budget.

Interaction libraries are used only inside `src/ui/core/` and template shells — features get native behavior through core components, and motion values come from the active template, so swapping templates still never touches components.

## PWA
Read `references/pwa.md`: `vite-plugin-pwa` setup, manifest with maskable icons, caching strategies per resource type, offline fallback, update prompt, installability checks.

## Capacitor (remote HTTPS URL)
Read `references/capacitor.md` before touching native config. It covers `server.url` config, iOS App-Bound Domains for service workers, the offline/fallback page, platform detection, plugin use, and the risks to report to the user (Capacitor documents `server.url` as meant for live reload; App Store guideline 4.2 on thin web wrappers).

## Done criteria
- Type-check, lint, tests, build all green (real output in notes).
- No feature file imports a headless library or a template (lint rule passes).
- Layout verified at mobile and desktop widths; all UI-spec states present.
- Native-feel checks (when the task touches navigation, gestures, overlays or lists): only `transform`/`opacity` animated, gestures follow the finger and release into a spring, reduced-motion respected, every gesture has a button alternative, budget in `references/native-feel.md` §11 met or the gap reported.
- PWA/Capacitor tasks: checks in the respective reference file pass.
