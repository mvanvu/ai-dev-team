# Mobile app platform options

Whenever a request needs an iOS/Android app and the platform is not already fixed, the user chooses between three options. Never pick one silently.

## When to ask
- Ask: greenfield with a mobile app, adding a mobile app to a web-only project, or a request that explicitly reopens the platform choice ("should we go native?").
- Do not ask: the project profile already records a mobile platform (`capacitor.config.*`, `pubspec.yaml`, native `ios/` + `android/` projects without Capacitor) — keep using it unless the user asks to migrate.

## The three options (present in this order)

| # | Option | Choose when | Trade-offs |
|---|---|---|---|
| 1 | **Flutter (Recommended)** | A real app-store app with native performance and one codebase for iOS + Android | Dart codebase separate from the web frontend; web stays a PWA or uses Flutter web; best balance of native feel, performance and cost |
| 2 | **Capacitor wrapping the PWA** (current setup) | The PWA already covers the product and speed to market matters most | One codebase for web + mobile; native feel limited by the WebView; remote `server.url` risks (App Store guideline 4.2, offline) — see `capacitor.md` |
| 3 | **Native apps** (Swift/SwiftUI for iOS, Kotlin/Jetpack Compose for Android) | Deep platform integration, maximum performance, or platform-specific UX is the core value | Two codebases, highest cost and slowest delivery; best platform fidelity |

The leader asks with `AskUserQuestion` (header `Mobile`, Flutter first with the label `Flutter (Recommended)`), records the answer in `_workspace/02_plan.md` under **Decisions**, and plans the tasks for that platform.

## Building each option

### 1. Flutter
- Flutter stable + Dart null safety; state with Riverpod (or the project's existing choice); routing with `go_router`; HTTP with `dio`; models with `freezed` + `json_serializable`.
- Keep the same layering as the web app: `lib/ui/core/` widgets own behavior and accessibility (`Semantics`), `lib/templates/<name>/` supplies `ThemeData` + `ThemeExtension` tokens (colors, radii, spacing, motion), `lib/features/` import only core widgets. Swapping a template must not touch core or feature widgets.
- Connectivity: `connectivity_plus` + reachability probe, offline banner/view and auto-reconnect per `connectivity.md` §8.
- Native feel: platform-adaptive widgets (Cupertino page transitions on iOS, predictive back on Android), `HapticFeedback`, `ListView.builder`/slivers for long lists, safe areas via `SafeArea`/`MediaQuery.padding`.
- Compact layout: no wasted space, no `RenderFlex overflowed`, text in rows wrapped in `Expanded`/`Flexible` with `maxLines` + ellipsis, button pairs on one row when they fit — per `compact-layout.md` §6.
- Tests: `flutter test` for widget/unit tests, `integration_test` for flows. Verify with `flutter analyze`, `flutter test`, `flutter build apk --debug` (and `flutter build ios --no-codesign` on macOS).
- API contracts come from the plan exactly as for the web client.

### 2. Capacitor
Follow `capacitor.md`, `capacitor-native-feel.md`, `connectivity.md`, `compact-layout.md`, `pwa.md` and `native-feel.md` — the existing PWA-first flow.

### 3. Native
- iOS: Swift + SwiftUI, Swift Concurrency, `URLSession`/`async` networking, MVVM with `@Observable`; tests with XCTest / Swift Testing. Android: Kotlin + Jetpack Compose, coroutines/Flow, Retrofit or Ktor, MVVM with `ViewModel`; tests with JUnit + Compose UI tests.
- Design tokens from the UI spec map to a SwiftUI theme and a Compose `MaterialTheme`/custom theme so visuals stay swappable per platform.
- Connectivity: `NWPathMonitor` / `ConnectivityManager.NetworkCallback` + reachability probe, offline banner/view and auto-reconnect per `connectivity.md` §9.
- Keep feature parity tracked per task: each mobile task names both platforms or is split into an iOS task and an Android task.
- Verify with `xcodebuild test` (macOS only) and `./gradlew test assembleDebug`.

## Tooling not available
If the Flutter SDK, Xcode or the Android SDK is missing, finish the code and the tests that can run, report native builds as `not-run` with the reason, and tell the leader which command the user must run.
