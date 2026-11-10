# Native-feel interactions for the PWA

Goal: the PWA should feel like a native app on a phone — instant feedback on touch, gesture-driven navigation, smooth 60fps motion, no layout jank, content visible immediately on launch (even offline).

## Contents
1. Library stack
2. Where the libraries live (architecture rules)
3. Navigation & page transitions
4. Gestures
5. Sheets, toasts, overlays
6. Lists & scrolling
7. Perceived performance (data, skeletons, prefetch)
8. Touch & platform CSS baseline
9. Device APIs & haptics
10. Motion tokens in templates
11. Performance budget & verification
12. Rendering performance in Vue / React

## 1. Library stack

| Need | Vue 3 | React |
|---|---|---|
| Animation, springs, drag, layout animation | `motion-v` (Motion for Vue) | `motion` (`motion/react`) |
| Gestures (drag, pan, swipe) | `motion-v` drag/pan + `@vueuse/core` (`usePointerSwipe`, `useScrollLock`) | `motion` drag/pan (default); `@use-gesture/react` only if a gesture Motion cannot express |
| Page transitions | View Transitions API + Vue Router hook | View Transitions API + React Router / TanStack Router |
| Bottom sheet / drawer | core `UiSheet` = Reka `Dialog` + `motion-v` drag (default) | core `UiSheet` = Radix `Dialog` + `motion` drag (default) |
| Toasts | `vue-sonner` | `sonner` |
| Virtualized lists | `@tanstack/vue-virtual` | `@tanstack/react-virtual` |
| Data tables (column visibility, selection, manual sort) | `@tanstack/vue-table` (inside `UiDataList`) | `@tanstack/react-table` (inside `UiDataList`) |
| Server state, optimistic UI, cache | `@tanstack/vue-query` | `@tanstack/react-query` |
| Persist query cache (instant offline launch) | `@tanstack/query-persist-client-core` + `@tanstack/query-async-storage-persister` + `idb-keyval` | `@tanstack/react-query-persist-client` + `@tanstack/query-async-storage-persister` + `idb-keyval` |
| Haptics | `@capacitor/haptics` (native app), `navigator.vibrate` fallback (Android web only) | same |
| Icons & iOS splash screens | `@vite-pwa/assets-generator` | same |

Before adding a library, check it is maintained (recent releases, open issue activity) and its bundle cost. As of 2026-11, `vaul`, `vaul-vue` and `@use-gesture/react` have had no release for over a year, so the defaults above build sheets and gestures on Motion instead; adopt those libraries only after re-checking their status. Do **not** add: full UI kits that impose their own look (they break template swapping), or scroll-hijacking libraries (e.g. smooth-scroll emulators) — native momentum scrolling on touch devices is already the best.

## 2. Where the libraries live

- Interaction libraries are used **only inside `src/ui/core/` and template shells**. Features get native feel by using core components (`UiSheet`, `UiPullToRefresh`, `UiSwipeAction`, `UiVirtualList`, `UiToaster`, `UiPage`), never by importing the libraries.
- Motion *values* (durations, easings, spring stiffness/damping) come from the active template (section 10), so a template can be snappy or calm without touching components.
- Extend the ESLint `no-restricted-imports` group for `src/features/**` and `src/pages/**` with: `motion`, `motion-v`, `motion/*`, `vaul`, `vaul-vue`, `sonner`, `vue-sonner`, `@use-gesture/*`, `@tanstack/*-virtual`, `@tanstack/*-table`.
- TanStack Query is the exception: features use it directly through composables/hooks in `src/features/**/api/` (it is data, not UI).

## 3. Navigation & page transitions

- Use the **View Transitions API** for route changes (supported in Chromium and Safari 18+); fall back to an instant switch when unsupported or when `prefers-reduced-motion: reduce`.
- Direction-aware: push = slide in from the right, back = slide out to the right, tab switch = cross-fade. Set a `data-nav-direction` attribute on `<html>` before starting the transition and style `::view-transition-old/new(root)` from the template.
- Shared-element transitions (list thumbnail → detail header) via `view-transition-name` on both elements.
- Keep page state alive when going back: Vue `<KeepAlive>` around `<RouterView>` for stack pages; React keeps list pages mounted or restores scroll + query cache. Always restore scroll position on back.
- iOS-style edge swipe-back inside the app (not in Safari, which has its own): `UiPage` listens for a pointer swipe starting within 20px of the left edge and calls `router.back()` past a threshold; drives the page translate with the finger via motion values.

Vue Router example:
```ts
let finishTransition: (() => void) | null = null

router.beforeResolve((to, from) => {
  if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) return
  document.documentElement.dataset.navDirection = isBack(to, from) ? 'back' : 'forward'
  // The transition callback stays pending until afterEach has rendered the new route,
  // so the browser captures the new page as the "new" snapshot.
  return new Promise<void>((resolveGuard) => {
    document.startViewTransition(() => new Promise<void>((done) => {
      finishTransition = done
      resolveGuard()
    }))
  })
})

// Runs for successful and failed navigations, so a pending transition never hangs.
router.afterEach(async () => {
  await nextTick()
  finishTransition?.()
  finishTransition = null
})
```

## 4. Gestures

| Gesture | Core component | Rule |
|---|---|---|
| Pull to refresh | `UiPullToRefresh` | Only when scrolled to top; resistance curve; triggers query `refetch`; set `overscroll-behavior-y: contain` on the scroller to disable the browser's own refresh |
| Swipe actions on list rows | `UiSwipeAction` | Reveal actions with drag; snap open/closed with spring; full swipe = primary action with haptic |
| Drag to dismiss sheet | `UiSheet` | Velocity-aware dismissal; snap points |
| Edge swipe back | `UiPage` | See section 3 |
| Long press | `UiPressable` | 450–500ms, haptic on trigger, cancels on move > 10px |

- Gestures must follow the finger 1:1 (drive `transform` from pointer movement), then hand off to a spring with the release velocity — this is what makes it feel native.
- Use pointer events; set `touch-action` precisely (`pan-y` on horizontally swipeable rows) so vertical scrolling still works.
- Every gesture has an accessible non-gesture alternative (button/menu).

## 5. Sheets, toasts, overlays

- On mobile, prefer bottom sheets over centered modals for actions and pickers; `UiDialog` can render as a sheet below the `md` breakpoint and as a dialog above it.
- Sheets: snap points, drag handle, background scale/dim effect from the template, scroll inside the sheet without dragging the sheet (drag only from handle/header or when content is scrolled to top).
- Toasts: one `UiToaster` in the shell, positioned above the bottom nav and safe area; swipe to dismiss.
- Lock body scroll while an overlay is open (`useScrollLock` or the primitive's built-in lock).

## 6. Lists & scrolling

- Virtualize any list that can exceed ~100 rows (`UiVirtualList`).
- Native momentum scrolling only; never `preventDefault` on touchmove for scroll containers.
- `scroll-snap` for carousels/tabs; `content-visibility: auto` for long non-virtualized sections.
- Sticky headers with `position: sticky`, not scroll listeners.
- Infinite scroll via `IntersectionObserver` + TanStack Query `useInfiniteQuery`.

## 7. Perceived performance

- **Instant launch**: persist the query cache to IndexedDB; on start, render cached data immediately and revalidate in the background (stale-while-revalidate).
- **Optimistic updates** for user actions (like, toggle, reorder, delete with undo toast) — the UI responds in the same frame as the tap.
- **Skeletons** matching final layout (no spinners for content areas); reserve space for images (`aspect-ratio`, width/height) to prevent layout shift.
- **Prefetch** the next likely route's code and data on link visibility or touchstart.
- Images: responsive `srcset`, `loading="lazy"` below the fold, `decoding="async"`, modern formats.

## 8. Touch & platform CSS baseline (in the template's base styles)

```css
html { -webkit-tap-highlight-color: transparent; text-size-adjust: 100%; }
body { overscroll-behavior-y: none; }               /* no rubber-band bounce of the whole app shell */
button, a, [role='button'] { touch-action: manipulation; user-select: none; -webkit-user-select: none; }
:where(button, [role='button']):active { transform: scale(0.97); transition: transform var(--motion-press, 80ms) ease-out; }
input, textarea, select { font-size: max(16px, 1rem); }  /* prevents iOS zoom on focus */
.app-shell { min-height: 100dvh; padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left); }
@media (prefers-reduced-motion: reduce) { *, ::view-transition-group(*) { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }
```
- Disable text selection and the iOS callout (`-webkit-touch-callout: none`) only on interactive chrome, never on content.
- `index.html`: `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, iOS splash `apple-touch-startup-image` links (generated by `@vite-pwa/assets-generator`).

## 9. Device APIs & haptics

Wrap each in `src/native/` with feature detection and a no-op fallback:
- `haptics.impact('light' | 'medium')`, `haptics.selection()` → `@capacitor/haptics` when native, `navigator.vibrate(10)` on Android web, no-op otherwise. Use on: toggle, snap, long-press trigger, pull-to-refresh threshold, destructive confirm.
- Web Share (`navigator.share`) / `@capacitor/share`.
- Badging API (`navigator.setAppBadge`) for unread counts.
- Screen Wake Lock for scanning/reading flows.
- Network status → offline banner / offline screen, automatic reconnect and queued mutations — see `connectivity.md`.

## 10. Motion tokens in templates

Extend the `UiTemplate` contract (see `architecture.md`):
```ts
export interface UiMotion {
  durations: { press: number; fast: number; base: number; slow: number } // ms
  easing: { standard: string; emphasized: string; exit: string }          // CSS easing strings
  spring: { stiffness: number; damping: number; mass: number }            // for drag release / sheets
  pageTransition: 'slide' | 'fade' | 'none'
}
export interface UiTemplate { name: string; recipes: UiRecipes; shells: { /* … */ }; motion: UiMotion }
```
Templates also expose the durations/easings as CSS variables (`--motion-fast`, `--motion-ease-standard`, …) for CSS transitions and view-transition styles. Core components read springs/durations from `useTemplate().motion`.

## 11. Performance budget & verification

1. Animate only `transform` and `opacity`; never animate layout properties (`top`, `height`, `width`) on mobile.
2. Targets on a mid-range Android device: INP < 200ms, CLS < 0.1, LCP < 2.5s, no dropped frames during transitions in the DevTools Performance panel (CPU throttling 4x).
3. Initial JS for the first route ≤ ~170KB gzipped; lazy-load routes and heavy libraries (charts, editors).
4. Verify on real devices (iOS Safari standalone + Android Chrome installed PWA + Capacitor builds): gestures don't conflict with system gestures, keyboard doesn't cover focused inputs, safe areas correct in both orientations, reduced-motion respected.

## 12. Rendering performance in Vue / React

Smooth motion is lost when the framework re-renders during a gesture or a long task blocks the main thread. These rules apply to every build and matter most inside a WebView (see `capacitor-native-feel.md`).

**Both frameworks**
- Gesture and animation values never go through framework state: drive `transform` from Motion values (`useMotionValue` / `useTransform` in `motion` and `motion-v`) so `pointermove` causes zero component re-renders. Commit to state only on release.
- No task over 50ms on the main thread during interaction: move parsing, sorting, diffing, crypto and image processing to a Web Worker (`comlink`); split remaining long work with `scheduler.yield()` (feature-detected, fallback `setTimeout(0)`).
- Listeners for `touchstart`/`touchmove`/`wheel`/`scroll` are `{ passive: true }`; no scroll listeners for layout effects (use `position: sticky`, `IntersectionObserver`, CSS scroll-driven animations).
- `will-change: transform` only while an element is animating or being dragged, removed afterwards — permanent layers exhaust WebView GPU memory on low-end Android.
- Route-level code splitting plus prefetch of the next likely route on link visibility or `touchstart`; heavy widgets (charts, editors, maps) load on demand.
- Search/filter inputs: update the input immediately, defer the expensive result (debounce or a deferred value), never re-filter a large list on every keystroke synchronously.

**Vue 3**
- Large or external objects (API collections, map/chart/editor instances) live in `shallowRef` or are wrapped with `markRaw`; deep reactivity on thousands of rows is the most common Vue slowdown.
- `v-memo` on rows of long non-virtualized lists; `v-once` for static content; stable `:key`s.
- Avoid inline object/array/function props in hot lists — each render creates a new value and re-renders the child; hoist them or use `computed`.
- `computed` over methods in templates; no `deep: true` watchers on large structures.
- `<KeepAlive :max="N">` around stack pages so back navigation is instant and scroll is preserved, with a cap to bound memory.
- Pinia: keep big collections in `shallowRef` state or in the TanStack Query cache, not in deeply reactive store state.

**React**
- Enable the React Compiler (`babel-plugin-react-compiler`) for automatic memoization; without it, `memo` list rows and stabilize callbacks/objects passed to them.
- `useTransition` / `useDeferredValue` for filtering, tab switches and other non-urgent updates so taps and typing stay responsive.
- Fast-changing shared values do not go in React Context (every consumer re-renders); use a store with selectors (`zustand` or `useSyncExternalStore`) or keep them local.
- Keep stack pages alive with `<Activity mode="hidden">` (React 19.2+) or keep list routes mounted, so back navigation does not remount and refetch.
- Colocate state with the component that uses it; lift only what must be shared.

