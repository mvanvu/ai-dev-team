#!/usr/bin/env node
// Phone layout overflow check for the ai-dev-team rules COMPACT-1 (no horizontal page scroll)
// COMPACT-2 (nothing sticks out of the viewport, no text clipped without an ellipsis)
// and COMPACT-7 (horizontal scrollers draw no scrollbar on phones).
//
// Usage: node .claude/team/overflow-check.mjs [options] <url> [<url>...]
//   --scale <n>        also run with the root font size multiplied by n (default 1.3; 1 disables)
//   --allow <selector> ignore elements matching this CSS selector and their descendants (repeatable)
//   --shots <dir>      save a full-page screenshot per url / viewport / scale
//   --storage <file>   Playwright storage state (logged-in session)
//   --wait <ms>        extra wait after load (default 300)
// Exit: 0 clean, 1 offenders found, 2 Playwright is not installed in this project, 64 usage error.
//
// Other engines (Playwright MCP, Claude in Chrome): evaluate the body of `findOverflow`
// in the page at 360x800 and 390x844; an empty `offenders` array and `pageScroll: false` pass.
import { createRequire } from 'node:module'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const VIEWPORTS = [
  { width: 360, height: 800 },
  { width: 390, height: 844 },
]

// Runs inside the page. Must stay self-contained: it is serialized by page.evaluate.
export function findOverflow(allow = []) {
  // The layout viewport width: on phones window.innerWidth grows when content is too wide
  // (the page zooms out to fit), so it cannot be used to detect the overflow that caused it.
  const vw = document.documentElement.clientWidth
  const describe = (el) => {
    const id = el.id ? `#${el.id}` : ''
    const cls = typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.')
      : ''
    const text = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)
    return `${el.tagName.toLowerCase()}${id}${cls}${text ? ` "${text}"` : ''}`
  }
  const ignored = (el) => {
    for (let node = el; node && node !== document.documentElement; node = node.parentElement) {
      if (allow.some((selector) => node.matches(selector))) return true
      if (node.getAttribute('aria-hidden') === 'true' || node.hasAttribute('inert')) return true
      const cs = getComputedStyle(node)
      if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') return true
      // Intended horizontal scrollers (chip rows, carousels, code blocks) may hold wider content.
      if (node !== el && (cs.overflowX === 'auto' || cs.overflowX === 'scroll')) return true
    }
    return false
  }
  const offenders = []
  for (const el of document.querySelectorAll('body *')) {
    const rect = el.getBoundingClientRect()
    // Zero-size and 1px visually-hidden elements carry no visible layout.
    if (rect.width <= 2 || rect.height <= 2) continue
    if (ignored(el)) continue
    const cs = getComputedStyle(el)
    const scrollsX = (cs.overflowX === 'auto' || cs.overflowX === 'scroll') && el.scrollWidth > el.clientWidth + 1
    if (scrollsX && cs.scrollbarWidth !== 'none' && getComputedStyle(el, '::-webkit-scrollbar').display !== 'none') {
      offenders.push({ rule: 'COMPACT-7', kind: 'visible-horizontal-scrollbar', el: describe(el) })
    }
    if (rect.right > vw + 1 || rect.left < -1) {
      offenders.push({ rule: 'COMPACT-2', kind: 'outside-viewport', el: describe(el), right: Math.round(rect.right) })
      continue
    }
    const hasOwnText = [...el.childNodes].some((node) => node.nodeType === 3 && node.textContent.trim())
    if (!hasOwnText) continue
    const clamped = /\d/.test(cs.webkitLineClamp || '')
    const ellipsis = cs.textOverflow === 'ellipsis'
    const clipsX = cs.overflowX === 'hidden' || cs.overflowX === 'clip'
    const clipsY = cs.overflowY === 'hidden' || cs.overflowY === 'clip'
    if (clipsX && !ellipsis && !clamped && el.scrollWidth > el.clientWidth + 1) {
      offenders.push({ rule: 'COMPACT-2', kind: 'clipped-horizontally', el: describe(el) })
    } else if (clipsY && !clamped && !ellipsis && el.scrollHeight > el.clientHeight + 1) {
      offenders.push({ rule: 'COMPACT-2', kind: 'clipped-vertically', el: describe(el) })
    }
  }
  const pageScroll = document.documentElement.scrollWidth > vw
  return { pageScroll, scrollWidth: document.documentElement.scrollWidth, viewport: vw, offenders }
}

function parseArgs(argv) {
  const options = { scale: 1.3, allow: [], shots: null, storage: null, wait: 300, urls: [] }
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    if (arg === '--scale') options.scale = Number(argv[++i])
    else if (arg === '--allow') options.allow.push(argv[++i])
    else if (arg === '--shots') options.shots = argv[++i]
    else if (arg === '--storage') options.storage = argv[++i]
    else if (arg === '--wait') options.wait = Number(argv[++i])
    else if (arg.startsWith('--')) return null
    else options.urls.push(arg)
  }
  return options.urls.length && options.scale > 0 ? options : null
}

function loadChromium() {
  // Resolve from the project being tested, not from this script's folder.
  const require = createRequire(path.join(process.cwd(), 'package.json'))
  for (const name of ['playwright', '@playwright/test', 'playwright-core']) {
    try {
      return require(name).chromium
    } catch {
      // try the next package name
    }
  }
  return null
}

async function main() {
  const options = parseArgs(process.argv.slice(2))
  if (!options) {
    console.error('usage: overflow-check.mjs [--scale n] [--allow selector] [--shots dir] [--storage file] [--wait ms] <url>...')
    process.exit(64)
  }
  const chromium = loadChromium()
  if (!chromium) {
    console.error('COMPACT-1 COMPACT-2 COMPACT-7 not-run: playwright is not installed in this project (npm i -D playwright && npx playwright install chromium --only-shell)')
    process.exit(2)
  }
  if (options.shots) mkdirSync(options.shots, { recursive: true })
  const scales = options.scale === 1 ? [1] : [1, options.scale]
  const browser = await chromium.launch()
  let failures = 0
  try {
    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({
        viewport, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
        ...(options.storage ? { storageState: options.storage } : {}),
      })
      const page = await context.newPage()
      for (const url of options.urls) {
        await page.goto(url, { waitUntil: 'networkidle' })
        for (const scale of scales) {
          // Approximates the OS font scale for rem-based layouts.
          await page.evaluate((s) => { document.documentElement.style.fontSize = `${16 * s}px` }, scale)
          await page.waitForTimeout(options.wait)
          const result = await page.evaluate(findOverflow, options.allow)
          const label = `${url} @ ${viewport.width}x${viewport.height} scale ${scale}`
          if (options.shots) {
            const file = `${new URL(url).pathname.replace(/\W+/g, '_') || 'root'}-${viewport.width}-x${scale}.png`
            await page.screenshot({ path: path.join(options.shots, file), fullPage: true })
          }
          if (result.pageScroll) {
            failures++
            console.log(`COMPACT-1 ${label}: page scrolls horizontally (scrollWidth ${result.scrollWidth} > ${result.viewport})`)
          }
          for (const offender of result.offenders) {
            failures++
            console.log(`${offender.rule} ${label}: ${offender.kind} ${offender.el}`)
          }
          if (!result.pageScroll && !result.offenders.length) console.log(`COMPACT-1 COMPACT-2 COMPACT-7 ok ${label}`)
        }
      }
      await context.close()
    }
  } finally {
    await browser.close()
  }
  process.exit(failures ? 1 : 0)
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  main().catch((error) => {
    console.error(error)
    process.exit(70)
  })
}
