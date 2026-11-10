# Pull to refresh

**Rule:** every screen that shows server data in a vertically scrolling list or feed supports pull to refresh — in the native app (Capacitor, Flutter, native), the installed PWA and the phone browser. It looks and feels like the platform's own control, refreshes only what the user is looking at, and never fights another gesture.

## Contents
1. Behavior contract
2. Gesture rules
3. Refresh rules
4. Conflicts to prevent
5. Web / PWA / Capacitor (Vue, React)
6. Flutter
7. Native iOS / Android
8. Checks

## 1. Behavior contract
- Available only while the list is scrolled to the very top. Pulling down then shows a circular, platform-style indicator.
- The indicator follows the finger with resistance (it moves less than the finger) and its arc / rotation grows with the pull distance, so the user sees how close they are to triggering.
- Trigger threshold: **64–72px** of indicator travel. Crossing it gives one light haptic in the native app (not on the plain web, where the vibration API is unreliable and silent on iOS). Pulling back above the threshold before release cancels without refreshing.
- On release past the threshold: the indicator settles at its resting position and spins until the refresh finishes, then animates away. On release before the threshold: it springs back, nothing is fetched.
- The current content stays on screen during the refresh — no skeleton, no blank list, no spinner replacing the list.
- On failure the old content stays and a toast explains the error (with Retry when it makes sense). On success nothing extra is shown beyond the updated data.

## 2. Gesture rules
1. Start only when the scroll container's `scrollTop` is 0 (or within 1px) at touch start **and** the first movement is downward.
2. Lock the direction after ~8–10px of movement: if the movement is mostly vertical (|dy| > |dx|), it is a pull; if mostly horizontal, it is a tab swipe / carousel / swipe action and pull to refresh does nothing for the rest of that touch. Once locked, the other gesture never runs in the same touch.
3. Resistance: indicator offset = `maxPull × (1 − e^(−pull / maxPull))` or an equivalent damping curve, capped at about 1.5× the threshold.
4. The indicator is driven by `transform` from the pointer, without framework re-renders during the drag (`native-feel.md` §12); release hands off to a spring.
5. `prefers-reduced-motion`: no rubber-band animation; the indicator appears at the threshold position and spins.
6. Every pull-to-refresh screen also has a non-gesture refresh path for accessibility (a Refresh item in the app bar or overflow menu, or a keyboard shortcut on desktop).

## 3. Refresh rules
1. Refresh only the data of the screen and tab currently visible: invalidate / refetch exactly the queries that screen uses (with TanStack Query: `refetch` of the active list query, or `invalidateQueries` with that screen's key), not the whole cache, not other tabs, not a page reload.
2. The indicator's lifetime is bound to that refetch's promise: it stops when the request settles, not after a fixed timeout.
3. A pull while a refresh of the same screen is already running does not start a second request.
4. Offline: do not spin; show the offline toast/banner from `connectivity.md` and spring back.
5. Paginated or infinite lists reset to the first page and keep the scroll at the top.

## 4. Conflicts to prevent
1. **Browser and WebView native refresh off.** Chrome on Android and Android WebView reload the whole page on overscroll at the top; the app's own control replaces that. Set `overscroll-behavior-y: none` on `html, body` (or `contain` on the scroll container that owns the gesture) so the browser's reload never fires. In Capacitor, also make sure no native `SwipeRefreshLayout` wraps the WebView.
2. **Horizontal gestures win their axis.** Tab swiping, carousels and row swipe actions keep working; the direction lock in §2 item 2 decides per touch.
3. **Not while a modal, sheet, dialog, popover or menu is open**, and not while any text input, textarea, select or contenteditable has focus (the keyboard is up and a downward drag means "scroll / dismiss keyboard").
4. **Not inside nested scrollers** that are not at their own top; only the screen's main list owns the gesture.
5. **No conflict with system gestures**: iOS edge swipe back and the Android back gesture take precedence at the screen edges.

## 5. Web / PWA / Capacitor (Vue, React)
- One core component, `UiPullToRefresh`, wraps the screen's scroll container: props `onRefresh: () => Promise<unknown>` and `disabled`; it reads the threshold, spinner and motion values from the template, and calls `haptics.impact('light')` (`native-feel.md` §9) when crossing the threshold — a no-op on the plain web.
- It renders a platform-style indicator from the template (Material circular indicator on Android, iOS-style activity indicator on iOS, chosen by the platform helper), not a custom brand animation.
- It disables itself automatically when the overlay stack is not empty or `document.activeElement` is an editable element; features can add `disabled` for their own cases.
- Pointer events with `touch-action: pan-y` on the container (vertical scroll stays native); the component cancels its own handling as soon as the direction lock says horizontal.
- `html, body { overscroll-behavior-y: none; }` belongs in the template base styles (`native-feel.md` §8); the scroll container gets `overscroll-behavior-y: contain`.
- Features pass the active tab's refetch: `<UiPullToRefresh :on-refresh="() => ordersQuery.refetch()">`.

## 6. Flutter
- `RefreshIndicator.adaptive` (Material on Android, Cupertino on iOS) around the tab's scrollable, or `CupertinoSliverRefreshControl` in a `CustomScrollView` for iOS-style sliver lists. `onRefresh` returns the active tab's refresh future (with Riverpod: `ref.refresh(provider.future)` of that tab only).
- `notificationPredicate: (n) => n.depth == 0` so nested scrollables do not trigger it; horizontal `PageView` / `TabBarView` keep their own axis.
- Crossing the threshold: `HapticFeedback.lightImpact()` — track the overscroll from `ScrollUpdateNotification`, since `RefreshIndicator` has no threshold callback.
- Disabled while a route is pushed on top (bottom sheet, dialog — it stops receiving notifications) and while a `TextField` has focus.

## 7. Native iOS / Android
- iOS: `.refreshable { await viewModel.refresh() }` in SwiftUI, or `UIRefreshControl` on the list's `UIScrollView`; `UIImpactFeedbackGenerator(style: .light)` when refreshing begins.
- Android: Compose `PullToRefreshBox` (Material 3) with `isRefreshing` bound to the active tab's state and a haptic at the threshold; Views: `SwipeRefreshLayout`.
- Both refresh only the visible tab's data and are disabled while a sheet or dialog is presented or the keyboard is up.

## 8. Checks
1. Every server-data list or feed screen on phones has pull to refresh, plus a non-gesture refresh path.
2. Starts only at the top of the main list; the indicator follows the finger with resistance and grows with the pull; springs back when released below the threshold.
3. Threshold 64–72px; one light haptic when crossing it in the native app; none on the plain web.
4. Release past the threshold refetches only the visible screen / tab's data; the indicator spins until that request settles; content stays visible throughout; a second pull during a refresh starts no new request.
5. Failure keeps the old content and shows a toast; offline shows the offline state instead of spinning.
6. The browser / WebView page reload never fires (Android Chrome, installed PWA, Capacitor Android): `overscroll-behavior-y` set, no native wrapper.
7. Vertical pull and horizontal tab swipe never run in the same touch (direction lock).
8. Disabled while a modal, sheet, dialog or menu is open and while a text input has focus.
9. Reduced motion: no rubber-band animation; refresh still works.
