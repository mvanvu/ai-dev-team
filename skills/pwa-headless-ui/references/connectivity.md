# Connectivity: offline screen and automatic reconnect

**Rule:** every mobile app that uses online data — Capacitor, Flutter or native, and the installed PWA — listens for connectivity changes for its whole lifetime. When the internet drops it switches to the designed offline state; when it returns it reconnects by itself and puts the user back where they were, without a tap or a restart.

## Contents
1. Behavior contract
2. Detecting "really online"
3. Offline UI: banner vs offline screen
4. Reconnect sequence
5. Retry pacing (protect the server)
6. Capacitor / PWA (Vue, React)
7. Capacitor remote URL: the bundled offline page
8. Flutter
9. Native iOS / Android
10. Tests and checks

## 1. Behavior contract

| Event | App behavior |
|---|---|
| Connection lost | Within ~2s (debounced): show the offline banner; screens without cached data switch to the offline screen; online-only actions are disabled with a reason; mutations are queued where the design allows |
| While offline | Probe with backoff (section 5); cached content stays readable; a **Retry** button runs a probe immediately |
| Connection back | Hide the offline UI, return to the route the user was on (never reset to home), refetch active data, replay queued mutations, reconnect realtime channels, show a short "Back online" toast |
| App returns to foreground | Re-check connectivity immediately, then follow the matching row above |

One `ConnectivityService` (or provider/store) in the app shell owns this state; screens read `status: 'online' | 'offline' | 'checking'` from it and never call the network APIs themselves.

## 2. Detecting "really online"

OS signals say a network interface is up, not that the internet works (captive portal, Wi-Fi without uplink, server down). Combine both:
1. **OS signal** — fast trigger: `@capacitor/network` `networkStatusChange`, browser `online`/`offline` events, Flutter `connectivity_plus`, iOS `NWPathMonitor`, Android `ConnectivityManager.NetworkCallback`.
2. **Reachability probe** — the truth: a small `GET /health` (or `HEAD`) to the app's own API with a 3–5s timeout and `cache: 'no-store'`. Online = probe succeeds. Also treat repeated network-level request failures from the API client as an "offline suspected" trigger for a probe.
3. Debounce flapping: require the new state to hold ~1–2s before switching UI.

`navigator.onLine === true` alone never means online.

## 3. Offline UI

- **Banner** (default): when the screen has cached data, keep it visible with a persistent offline banner below the top bar (above the safe area), and mark stale data ("Last updated 10:42").
- **Offline screen**: when the screen has nothing to show (first load, uncached route, online-only feature such as payment or live chat), render the designed offline screen in place of the content: illustration/icon, message, **Retry** button, and a visible "Reconnecting…" indicator while probes run. It is a state of the current route, not a navigation, so back history stays intact and the route is restored automatically on reconnect.
- Online-only actions (submit payment, upload) are disabled with an explanation, or queued when the design marks them as queueable.
- Announce changes to screen readers (`aria-live="polite"` / platform equivalents).
- `ui-ux-designer` specifies these as the `offline` and `reconnecting` states of each screen.

## 4. Reconnect sequence

On the transition to online, in order:
1. Hide the offline screen/banner; keep the current route.
2. Refetch active queries (stale-while-revalidate — cached content stays on screen while refreshing).
3. Replay the mutation queue in order; conflicts surface as errors on the affected item, not a global failure.
4. Reconnect WebSocket / SSE / realtime subscriptions and resubscribe channels; fetch missed events since the last received cursor.
5. Refresh the auth session if it expired while offline (silent refresh first, login screen only if that fails).
6. Show "Back online" toast (short, no action needed).

## 5. Retry pacing (protect the server)

Thousands of devices coming back at once must not become a self-inflicted DDoS:
- Probes and realtime reconnects use exponential backoff with full jitter: 1s, 2s, 4s… capped at 30s.
- OS "online" events, app resume and the Retry button trigger one immediate probe and reset the backoff.
- No probing while the app is in the background.
- Server responses `429` / `503` with `Retry-After` are honored.

## 6. Capacitor / PWA (Vue, React)

- `src/native/connectivity.ts`: subscribe to `@capacitor/network` when `isNative` (guarded with `isPluginAvailable('Network')`), otherwise `window` `online`/`offline` events; add the probe and backoff; listen to `@capacitor/app` `appStateChange` (native) or `visibilitychange` (web) for resume checks.
- Expose it through a composable/hook (`useConnectivity()`) and a core `UiOfflineBanner` / `UiOfflineState` pair rendered by the template shells; features never import the plugin.
- Wire TanStack Query to it: `onlineManager.setEventListener((setOnline) => connectivity.subscribe((s) => setOnline(s === 'online')))` so queries pause offline and refetch on reconnect; `focusManager` follows app resume; mutations use `networkMode: 'offlineFirst'` with a persisted mutation queue where the design allows.
- Realtime client: one reconnecting wrapper (backoff from section 5) that also listens to the connectivity service.

## 7. Capacitor remote URL: the bundled offline page

With `server.url`, losing the network before the PWA has loaded shows the bundled `server.errorPath` page (`capacitor.md`), not the app. That page must reconnect by itself:
- Listen to `online` events and probe the PWA URL with backoff (section 5), plus a **Retry** button.
- On success, `location.replace('<server.url>' + lastPath)` so the user lands back where they were (store the last path in `localStorage` from the app).
- Inline styles and assets only; no network dependencies.
Once the PWA has loaded once on iOS (App-Bound Domains) or Android, the service worker serves the shell offline and the in-app offline UI from section 3 takes over.

## 8. Flutter

- `connectivity_plus` stream for OS changes + `internet_connection_checker_plus` (or an own probe to `/health` via `dio`) for reachability; expose a Riverpod `connectivityProvider` (`online | offline | checking`).
- `AppLifecycleListener` (`onResume`) triggers a check.
- A shell-level widget shows the offline banner; screens without cached data render an `OfflineView` with Retry; `go_router` keeps the current location.
- On reconnect: invalidate active providers, replay the queued requests, reconnect web sockets with the backoff from section 5.

## 9. Native iOS / Android

- iOS: `NWPathMonitor` on a background queue, publish to an `@Observable` connectivity model on the main actor; probe with `URLSession` (`timeoutInterval` 5s); re-check on `scenePhase == .active`.
- Android: `ConnectivityManager.registerDefaultNetworkCallback` exposing a `StateFlow`; treat `NET_CAPABILITY_VALIDATED` as a strong hint and still probe; re-check in `onResume` / `Lifecycle.Event.ON_RESUME`.
- Same UI contract (banner, offline view, restore route) and reconnect sequence on both.

## 10. Tests and checks

1. Unit: the connectivity service state machine (debounce, probe success/failure, backoff caps, resume trigger) with fake timers and a mocked probe.
2. Device / emulator: airplane mode on → banner or offline screen within ~2s; airplane mode off → returns to the same screen, data refreshes, queued actions sent, realtime resumes, toast shown — with no tap.
3. Wi-Fi connected without internet (or blocked API host) → app shows offline, not an endless spinner.
4. Capacitor remote URL: cold start in airplane mode → bundled offline page; network back → app loads at the last path by itself.
5. Browser: DevTools offline toggle / Playwright `context.setOffline(true|false)` for the PWA (requires a real rendering engine, not Lightpanda).
