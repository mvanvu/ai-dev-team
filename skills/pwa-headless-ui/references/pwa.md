# PWA setup (Vite + vite-plugin-pwa)

## Plugin config

```ts
// vite.config.ts (add to the Vue or React plugin list)
import { VitePWA } from 'vite-plugin-pwa'

VitePWA({
  registerType: 'prompt',            // show an update prompt instead of silently reloading
  includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
  manifest: {
    name: 'App Name',
    short_name: 'App',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    orientation: 'portrait',
    background_color: '#ffffff',
    theme_color: '#ffffff',
    icons: [
      { src: '/pwa-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/pwa-512.png', sizes: '512x512', type: 'image/png' },
      { src: '/pwa-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  },
  workbox: {
    navigateFallback: '/index.html',
    navigateFallbackDenylist: [/^\/api\//],
    runtimeCaching: [
      // API: fresh data first, fall back to cache when offline.
      { urlPattern: ({ url }) => url.pathname.startsWith('/api/'), handler: 'NetworkFirst',
        options: { cacheName: 'api', networkTimeoutSeconds: 5, expiration: { maxEntries: 100, maxAgeSeconds: 86400 } } },
      // Images: cache first, bounded.
      { urlPattern: ({ request }) => request.destination === 'image', handler: 'CacheFirst',
        options: { cacheName: 'images', expiration: { maxEntries: 200, maxAgeSeconds: 2592000 } } },
    ],
  },
})
```

Never cache authenticated API responses that contain personal data unless the spec allows it; coordinate with `security-auditor` (shared devices, logout must clear caches).

## Update prompt
- Vue: `import { useRegisterSW } from 'virtual:pwa-register/vue'` → `needRefresh`, `offlineReady`, `updateServiceWorker()`.
- React: `import { useRegisterSW } from 'virtual:pwa-register/react'` → same fields as state tuples.
Render the prompt with core components (`UiToast` / `UiDialog`), never ad-hoc markup.

## index.html essentials
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<meta name="theme-color" content="#ffffff" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
```

## Checks before marking a PWA task done
1. `npm run build && npm run preview`, then in Chrome DevTools → Application: manifest has no errors, service worker activated, installable.
2. Offline: toggle offline, reload — app shell loads, API screens show the designed offline/error state.
3. Update flow: rebuild with a change, reload — the update prompt appears and applies.
4. HTTPS is required in production (service workers only run on secure origins; localhost is exempt).
5. Lighthouse no longer has a PWA category; verify installability manually as above.
