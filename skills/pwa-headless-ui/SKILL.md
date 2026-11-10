---
name: pwa-headless-ui
description: "How to build a mobile-first PWA in Vue 3 or React + TypeScript on a headless core-component architecture with swappable template packs (Reka UI / Radix UI / React Aria), PWA setup (manifest, service worker, offline, updates), and the mobile app platform choice — Flutter (recommended), Capacitor wrapping the PWA's HTTPS URL, or native Swift/Kotlin. Used by pwa-frontend-engineer, or when asked to add a core component, create/switch a UI template or theme, set up the PWA, build a mobile app, or configure Capacitor. Not for backend work (implementation) or visual design specs (ui-ux-design)."
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
1. Read the task, the design contracts and the UI spec section, and every must-read reference of the rule packs in the task's `Rules` column (`ai-dev-team:dev-team` → `references/rule-packs.md` §2).
2. Need a component the core layer lacks? Add it to `src/ui/core/` first (with behavior tests), add its recipe slot to the `UiTemplate` contract, then implement the recipe in **every** existing template (the compiler will list the ones you missed).
3. Build the feature screen using only core components. Mobile layout first; add `md:` / `lg:` enhancements and the desktop shell second.
4. Implement every UI-spec state (loading, empty, error, success, disabled).
5. Run once, at the end: type-check (`vue-tsc --noEmit` or `tsc --noEmit`), lint of changed files, the profile's `test (related)` command on the changed files plus mapped guards, and the production build only when the task changes built output or a browser check needs it. Record real output in task notes. Never the whole suite per task.
6. After that build, verify once at 360px and 1280px widths (screenshot via the `run` skill or Playwright when available); at 360px also with worst-case strings (longest locale, long unbroken name, large amount) per `references/compact-layout.md` §7.

## Adding a new template
1. Copy `src/templates/default/` to `src/templates/<name>/`.
2. Change only `tokens.css`, recipes and shells. Type-check must pass — it proves the contract is complete.
3. Register it in `src/templates/index.ts`; select it by env (`VITE_UI_TEMPLATE`) or at runtime via the provider.
4. Run the full component test suite against the new template — behavior must be identical.

## Mobile-first rules
- Base styles target ~360px; enhance with `sm/md/lg/xl` breakpoints. Never write desktop-first then override down.
- Touch targets ≥ 44px; no hover-only interactions; use `:focus-visible`.
- Pagination never renders every page number: `UiPagination` shows first/last pages, the current page with neighbors and ellipses (`1 2 3 … 10 11 12`), fewer items on mobile — see `references/architecture.md` §4a.
- No wasted space and no overflowing text on phones (mobile web and app): button pairs and short fields share a row, icon rows leave no dead space, horizontal scrollers are swipe-only with the scrollbar hidden, no redundant instruction text, every text container is `min-w-0` with a truncate / clamp / wrap decision — `references/compact-layout.md`.
- Respect safe areas: `viewport-fit=cover` + `env(safe-area-inset-*)` padding in shells.
- Use `dvh` units for full-height layouts (mobile browser bars).
- Adaptive shells: `MobileShell` (bottom nav, top app bar) and `DesktopShell` (sidebar, wider content) chosen by a media-query composable/hook, both supplied by the template.

## Pull to refresh
Every phone screen with a server-data list supports pull to refresh: platform-style indicator that follows the finger with resistance, 64–72px threshold with a light haptic in the native app, refetch of the visible tab only with content kept on screen, toast on error, browser/WebView page reload disabled, vertical/horizontal direction lock, off while a modal is open or an input has focus. Read `references/pull-to-refresh.md` (web, Flutter, native).

## Native feel
The PWA must feel like a native app: gesture-driven navigation that follows the finger, direction-aware page transitions, bottom sheets, haptic feedback, virtualized 60fps lists, optimistic updates, and instant launch from a persisted cache. Read `references/native-feel.md` for the library stack (Vue: `motion-v`, `@vueuse/core`, `vue-sonner`, `@tanstack/vue-virtual`, `@tanstack/vue-query`; React: `motion`, `sonner`, `@tanstack/react-virtual`, `@tanstack/react-query`; both: View Transitions API, `@capacitor/haptics`), the core components that wrap them, motion tokens in templates, the touch CSS baseline, and the performance budget.

Interaction libraries are used only inside `src/ui/core/` and template shells — features get native behavior through core components, and motion values come from the active template, so swapping templates still never touches components.

## PWA
Read `references/pwa.md`: `vite-plugin-pwa` setup, manifest with maskable icons, caching strategies per resource type, offline fallback, update prompt, installability checks.

## List pages and pickers
Every paginated resource list is **one** `<Resource>List` component (search, filters, server-side sort, truncated pagination, column chooser, all states) used both on the list page and inside a picker modal: a `UiPickerInput` opens the same list in a modal and selects one or many records by props. Column order: identifying always-visible columns (title/name/description) first, then data columns, then the actions icon, then the auto-increment ID last. Column visibility is saved in localStorage; filters, sort and page live only in the URL query params (history `replace`, never localStorage) on the page and only in memory in the picker. Read `references/list-page.md`.

## Connectivity (mobile apps with online data)
Every mobile app that uses online data — on any platform — listens for connectivity changes for its whole lifetime: offline banner or offline screen within ~2s of losing the internet, automatic reconnect with backoff, and a return to the same screen with refreshed data, replayed mutations and resumed realtime, without user action. Read `references/connectivity.md` (detection with a reachability probe, UI contract, reconnect sequence, Capacitor/PWA, Flutter and native implementations, tests).

## Mobile app platform
Read `references/mobile-options.md` whenever a mobile app is involved. The user chooses between **Flutter (Recommended)**, **Capacitor wrapping the PWA** (the setup below) and **native apps** (Swift/Kotlin); an existing platform in the repo is kept. The reference covers when to ask, the trade-offs to present, and how to build the Flutter and native options.

## Capacitor (remote HTTPS URL)
Read `references/capacitor.md` before touching native config. It covers `server.url` config, iOS App-Bound Domains for service workers, the offline/fallback page, platform detection, plugin use, and the risks to report to the user (Capacitor documents `server.url` as meant for live reload; App Store guideline 4.2 on thin web wrappers).

To make the wrapped app feel native, also read `references/capacitor-native-feel.md`: splash held until content paints, fixed shell with inner scroll containers, keyboard handling without WebView resize, Android back button and iOS swipe back, transitions on older WebViews, a reduced-effects mode for low-end Android, native UI where the web is weak, and on-device profiling.

## Done criteria
- Type-check, lint, tests, build all green (real output in notes).
- Task notes contain the `## Rule compliance` table: one row with evidence per rule ID of `BASE` and each assigned pack (`ai-dev-team:dev-team` → `references/rule-packs.md` §6).
- Without assigned packs (standalone use), run the numbered checks of every reference this task touched: `architecture.md` §9 always; `compact-layout.md` §7 for phone screens; `list-page.md` §9 for lists and pickers; `native-feel.md` §11 for navigation, gestures, overlays and long lists; `pull-to-refresh.md` §8 for server-data lists on phones; `connectivity.md` §10 for mobile apps with online data; the Checks sections of `pwa.md`, `capacitor.md` and `capacitor-native-feel.md` §10 for PWA / Capacitor tasks.
