# Native feel inside the Capacitor WebView

Read this when the user chose **Capacitor wrapping the PWA**. Everything in `native-feel.md` still applies; this file covers what changes inside a WKWebView (iOS) or Android System WebView, where users compare the app directly with native apps.

## Contents
1. What makes a wrapped PWA feel non-native
2. Launch: splash, shell, cache
3. Native shell config (scroll, bounce, link preview, background)
4. Keyboard
5. Navigation: Android back button, iOS swipe back, transitions on older WebViews
6. Status bar, safe areas, edge-to-edge
7. Low-end Android: reduced-effects mode
8. Use native UI where the web is weak
9. Profiling on devices
10. Checks before marking a task done

## 1. What makes a wrapped PWA feel non-native

| Symptom | Cause | Fix (section) |
|---|---|---|
| White flash or blank screen at launch | Splash hides before the remote page paints | 2 |
| Whole app rubber-bands, header scrolls away | WebView root scroll view scrolls | 3 |
| Long-press on links opens a preview / callout | WKWebView link preview, `-webkit-touch-callout` | 3, `native-feel.md` §8 |
| Layout jumps when the keyboard opens | WebView resize on keyboard show | 4 |
| Android back button closes the app | No `backButton` handler | 5 |
| Pages switch with no transition on iOS 17 | View Transitions API missing in older WKWebView | 5 |
| Stutter while scrolling or dragging on cheap Android | Blur/shadow/filter effects, too many GPU layers, re-renders during gestures | 7, `native-feel.md` §12 |

## 2. Launch: splash, shell, cache

- Keep the native splash until the app has painted real content: `plugins.SplashScreen.launchAutoHide: false`, then call `SplashScreen.hide({ fadeOutDuration: 200 })` after the shell mounted and the first route rendered from the persisted query cache (`native-feel.md` §7). Add a safety timeout (e.g. 4s) so a stuck load never traps the user on the splash.
- Set `backgroundColor` (top-level config) and the splash background to the template's surface color so there is no white frame between splash and app.
- Second and later launches must not need the network: the service worker precaches the app shell, route chunks and fonts (`pwa.md`); hashed assets get `Cache-Control: immutable`. On iOS this requires App-Bound Domains (`capacitor.md`).
- Inline critical CSS for the shell in `index.html`; preconnect to the API origin.
- Fonts: the system font stack (`system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`) looks native and costs nothing; brand fonts are self-hosted, preloaded and precached with `font-display: swap`.

## 3. Native shell config

```ts
// capacitor.config.ts (additions to the config in capacitor.md)
const config: CapacitorConfig = {
  backgroundColor: '#ffffff',            // template surface color
  ios: {
    scrollEnabled: false,                // fixed app shell; content scrolls in inner containers
    allowsLinkPreview: false,            // no 3D-touch/long-press link previews
    contentInset: 'never',
  },
  android: {
    webContentsDebuggingEnabled: false,  // true only in debug builds (section 9)
  },
  plugins: {
    SplashScreen: { launchAutoHide: false, backgroundColor: '#ffffff' },
    Keyboard: { resize: 'none' },        // see section 4
  },
}
```

- With `scrollEnabled: false` the app shell is fixed (`height: 100dvh; overflow: hidden`) and each page scrolls inside its own container (`overflow-y: auto; overscroll-behavior: contain`). This keeps top bars and bottom nav still, gives native momentum and bounce per page, and restores per-page scroll position on back.
- Inner scroll containers break the browser's "scroll focused input into view"; the keyboard handling in section 4 covers it.

## 4. Keyboard

- Default to `Keyboard.resize: 'none'` and react to the keyboard yourself: on `keyboardWillShow` set `--keyboard-height` on `<html>` from `info.keyboardHeight`, animate the bottom bar / composer with `transform: translateY(calc(-1 * var(--keyboard-height)))`, add matching `padding-bottom` to the active scroll container, and `scrollIntoView({ block: 'center' })` the focused input. Reset on `keyboardWillHide`. This moves with the keyboard instead of reflowing the whole WebView.
- If a screen is form-heavy and the custom handling is not worth it, `resize: 'body'` is the simpler fallback; never `'native'` with a fixed shell (the whole WebView resizes and every layout reflows).
- Hide the iOS accessory bar (`Keyboard.setAccessoryBarVisible({ isVisible: false })`) only when the form has its own next/done controls.
- Set `inputmode`, `enterkeyhint` and `autocomplete` on every input so the right native keyboard appears.

## 5. Navigation

- **Android back button**: one handler in the app shell via `App.addListener('backButton', …)`, in this order: close the top-most overlay (sheet, dialog, menu) → `router.back()` when history allows → on the root tab, `App.minimizeApp()` (never `exitApp()` on a non-root page). Core overlays register themselves on a small back-stack so the handler can close them.
- **Android predictive back**: when the target SDK enables it, the system animation only previews; the app still runs the handler above.
- **iOS swipe back**: Safari's gesture does not exist inside the app, so `UiPage`'s edge swipe-back (`native-feel.md` §3) is enabled when `Capacitor.getPlatform() === 'ios'`.
- **Transitions on older WebViews**: the View Transitions API needs iOS 18+ / a recent Android System WebView. When `isNative` and it is missing, `UiPage` falls back to a Motion slide (same direction rules and template motion tokens) instead of an instant switch; reduced motion still switches instantly.
- Tab switches keep each tab's page alive (`KeepAlive` / `<Activity>`, `native-feel.md` §12) so returning to a tab is instant.

## 6. Status bar, safe areas, edge-to-edge

- Status bar style follows the active template (light/dark) via `@capacitor/status-bar` `setStyle`, updated on theme switch.
- Shells pad with `env(safe-area-inset-*)`. Some Android WebView versions report insets as 0 in edge-to-edge mode; check the installed Capacitor version's edge-to-edge guidance (e.g. the Android `adjustMarginsForEdgeToEdge` option or a safe-area plugin) and verify on a device with a gesture bar and a notch.
- Lock orientation in the native projects when the design is portrait-only.

## 7. Low-end Android: reduced-effects mode

Android WebView performance follows the device, and cheap phones are where wrapped apps stutter.
- At startup set `data-effects="reduced"` on `<html>` when `navigator.hardwareConcurrency <= 4` or `navigator.deviceMemory <= 4` (feature-detected), or when the user enabled reduced motion.
- Templates must style the reduced mode: no `backdrop-filter` blur (solid translucent color instead), no animated `box-shadow`/`filter`, shorter shadows, simpler sheet background-scale effect. Motion durations stay; only expensive paint effects go.
- Lists stay virtualized, images are sized for the device (`srcset`), and decoding stays async.

## 8. Use native UI where the web is weak

Prefer the platform's own UI where web emulation feels off, wrapped in `src/native/` with a web fallback:
- Date/time pickers: native `<input type="date|time">` on mobile (opens the system picker) unless the design requires a custom picker.
- Share sheet (`@capacitor/share`), haptics (`@capacitor/haptics`), camera/photos (`@capacitor/camera`), biometric login, push notifications (`@capacitor/push-notifications`).
- System alerts or action sheets (`@capacitor/dialog`, `@capacitor/action-sheet`) only where the UI spec asks for a system look; otherwise core components keep the template look.

These also add the native value Apple expects under guideline 4.2 (`capacitor.md`).

## 9. Profiling on devices

- Android: debug build with `webContentsDebuggingEnabled: true` → `chrome://inspect` → Performance panel while scrolling, dragging a sheet and navigating. iOS: Safari Web Inspector → Timelines on a device build.
- Targets on a mid-range Android phone (and a low-end one when the audience has them): no frame over ~16.7ms during gestures and transitions, INP < 200ms, cold launch to interactive ≤ 2s with a warm service-worker cache, splash hides only after content paints.
- Record the device, OS/WebView version and results in the task notes; device runs not possible in this environment are `not-run` with the reason.

## 10. Checks before marking a task done

1. Splash stays until content paints, with no white flash; second launch works in airplane mode.
2. Root WebView does not scroll or bounce; pages scroll in inner containers and keep their position on back.
3. Keyboard opens without layout jumps and the focused input stays visible.
4. Android back closes overlays first, then navigates back, then minimizes on the root tab.
5. iOS edge swipe-back works; page transitions animate on the minimum supported iOS version.
6. `data-effects="reduced"` styles exist in every template.
7. Debugging is disabled in release builds.
