# Capacitor wrapping the PWA's HTTPS URL

## Risks to report to the user (once, with mitigations)
1. **Capacitor documents `server.url` as intended for live reload**, not production. It works, but it is outside the officially recommended path. Mitigation: keep a bundled offline/error page (`webDir` + `server.errorPath`), test on real devices each release.
2. **App Store guideline 4.2 (minimum functionality)**: Apple may reject apps that are only a website in a wrapper. Mitigation: add native value — push notifications, share sheet, haptics, biometric login, deep links.
3. **Web/native version skew**: the web deploys instantly, the native binary does not. New web code calling a plugin that the installed binary lacks will fail. Mitigation: guard every plugin call with `Capacitor.isPluginAvailable('Name')` and degrade gracefully.
4. **iOS service workers in WKWebView** only work with App-Bound Domains enabled (below). Without it the PWA runs but has no SW caching/offline inside the iOS app.

If the user prefers lower risk, offer the alternative: bundle the built PWA into `webDir` (standard Capacitor) and ship web updates via a live-update service. Let the user decide.

## Config

```ts
// capacitor.config.ts
import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.example.app',
  appName: 'App',
  webDir: 'native-shell',           // minimal bundled assets: offline/error page only
  server: {
    url: 'https://app.example.com', // production PWA URL; per-env via process.env
    cleartext: false,
    errorPath: 'offline.html',      // shown when the remote URL cannot load
    allowNavigation: ['auth.example.com'], // extra hosts allowed inside the webview (e.g. SSO)
  },
  ios: {
    limitsNavigationsToAppBoundDomains: true, // required for service workers on iOS
    contentInset: 'never',
  },
  android: { allowMixedContent: false },
}
export default config
```

iOS `Info.plist` (App-Bound Domains, max 10):
```xml
<key>WKAppBoundDomains</key>
<array>
  <string>app.example.com</string>
  <string>auth.example.com</string>
</array>
```

Keep `native-shell/` tiny: `index.html` + `offline.html` with inline styles matching the default template tokens and a retry button.

## Environments
Generate `server.url` from an env var (`CAP_SERVER_URL`) so dev can point to a LAN dev server (`cleartext: true` only in dev) and release builds point to production. Never ship a release with `cleartext: true` or an http URL.

## Native integration in web code
```ts
import { Capacitor } from '@capacitor/core'

export const isNative = Capacitor.isNativePlatform()
export const platform = Capacitor.getPlatform() // 'ios' | 'android' | 'web'
```
- Wrap each plugin in a small service in `src/native/` that checks `isPluginAvailable` and provides a web fallback (e.g. `navigator.share` → `@capacitor/share`).
- Plugin JS packages are part of the web bundle; the same plugins must be installed in the native project (`npm i` + `npx cap sync`) before release.
- Hide the PWA install prompt and the SW update prompt behavior that does not apply when `isNative` (the app updates by reloading the URL).
- Status bar / safe area: `@capacitor/status-bar` with overlay + CSS `env(safe-area-inset-*)` in shells.
- Deep links: Universal Links (iOS `apple-app-site-association`) and Android App Links (`assetlinks.json`) hosted on the PWA domain; route them with `@capacitor/app` `appUrlOpen`.

## Commands
```
npm i @capacitor/core && npm i -D @capacitor/cli
npx cap init
npm i @capacitor/ios @capacitor/android
npx cap add ios && npx cap add android
npx cap sync
npx cap open ios | npx cap open android
```

## Checks before marking a Capacitor task done
- `npx cap sync` succeeds; config contains no http URL and `cleartext: false` for release.
- Airplane mode on device/emulator → `offline.html` appears, retry works.
- iOS: service worker registers inside the app (Safari Web Inspector → Service Workers).
- Plugin calls are guarded; web fallback works in a normal browser.
- Native builds not runnable in this environment (no Xcode/SDK) → mark `not-run` with reason.
