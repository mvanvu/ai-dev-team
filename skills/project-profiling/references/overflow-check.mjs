#!/usr/bin/env node
// Layout overflow check and screenshot sweep for the ai-dev-team rules COMPACT-1 (no horizontal
// page scroll), COMPACT-2 (nothing sticks out of the viewport, no text clipped without an
// ellipsis), COMPACT-7 (horizontal scrollers draw no scrollbar on phones) and the COST sweep
// (every width x every theme in one browser launch, one contact sheet per url).
//
// Usage: node .claude/team/overflow-check.mjs [options] <url> [<url>...]
//   --widths <list>    comma-separated viewport widths (default 360,390; the sweep uses the profile's ui_widths)
//   --themes <list>    comma-separated themes, e.g. light,dark (default light)
//   --theme-set <js>   function body run in the page after load with `theme` in scope, for apps that
//                      switch theme by attribute or class instead of prefers-color-scheme
//   --scale <n>        also run phone widths (< 768) with the root font size multiplied by n (default 1.3; 1 disables)
//   --allow <selector> ignore elements matching this CSS selector and their descendants (repeatable)
//   --shots <dir>      save a full-page screenshot per url / width / theme / scale
//   --sheet            with --shots: also write <dir>/<url>-sheet.png, every width x theme of that url on one image
//   --storage <file>   Playwright storage state (logged-in session)
//   --wait <ms>        extra wait after load (default 300)
// Exit: 0 clean, 1 offenders found, 2 Playwright is not installed in this project, 64 usage error.
//
// Other engines (Playwright MCP, Claude in Chrome): evaluate the body of `findOverflow`
// in the page at each width; an empty `offenders` array and `pageScroll: false` pass.
import { createRequire } from 'node:module'
import { mkdirSync, readFileSync } from 'node:fs'
import path from 'node:path'

const PHONE_MAX = 767

function viewportFor(width) {
  if (width <= PHONE_MAX) return { width, height: width < 380 ? 800 : 844 }
  return { width, height: width < 1200 ? 900 : 1000 }
}

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
  const options = {
    widths: [360, 390], themes: ['light'], themeSet: null, scale: 1.3, allow: [],
    shots: null, sheet: false, storage: null, wait: 300, urls: [],
  }
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    if (arg === '--widths') options.widths = argv[++i].split(',').map(Number)
    else if (arg === '--themes') options.themes = argv[++i].split(',').map((t) => t.trim()).filter(Boolean)
    else if (arg === '--theme-set') options.themeSet = argv[++i]
    else if (arg === '--sheet') options.sheet = true
    else if (arg === '--scale') options.scale = Number(argv[++i])
    else if (arg === '--allow') options.allow.push(argv[++i])
    else if (arg === '--shots') options.shots = argv[++i]
    else if (arg === '--storage') options.storage = argv[++i]
    else if (arg === '--wait') options.wait = Number(argv[++i])
    else if (arg.startsWith('--')) return null
    else options.urls.push(arg)
  }
  const valid = options.urls.length && options.scale > 0 && options.themes.length
    && options.widths.length && options.widths.every((w) => Number.isInteger(w) && w > 0)
    && (!options.sheet || options.shots)
  return valid ? options : null
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
    console.error('usage: overflow-check.mjs [--widths list] [--themes list] [--theme-set js] [--scale n] [--allow selector] [--shots dir [--sheet]] [--storage file] [--wait ms] <url>...')
    process.exit(64)
  }
  const chromium = loadChromium()
  if (!chromium) {
    console.error('COMPACT-1 COMPACT-2 COMPACT-7 not-run: playwright is not installed in this project (npm i -D playwright && npx playwright install chromium --only-shell)')
    process.exit(2)
  }
  if (options.shots) mkdirSync(options.shots, { recursive: true })
  const fontScales = options.scale === 1 ? [1] : [1, options.scale]
  const shotName = (url) => new URL(url).pathname.replace(/\W+/g, '_') || 'root'
  const sheetCells = new Map()
  const browser = await chromium.launch()
  let failures = 0
  try {
    for (const width of options.widths) {
      const phone = width <= PHONE_MAX
      const context = await browser.newContext({
        viewport: viewportFor(width), isMobile: phone, hasTouch: phone, deviceScaleFactor: phone ? 2 : 1,
        ...(options.storage ? { storageState: options.storage } : {}),
      })
      const page = await context.newPage()
      for (const url of options.urls) {
        for (const theme of options.themes) {
          await page.emulateMedia({ colorScheme: theme === 'dark' ? 'dark' : 'light' })
          await page.goto(url, { waitUntil: 'networkidle' })
          if (options.themeSet) {
            await page.evaluate(({ body, theme }) => new Function('theme', body)(theme), { body: options.themeSet, theme })
          }
          for (const scale of phone ? fontScales : [1]) {
            // Approximates the OS font scale for rem-based layouts.
            await page.evaluate((s) => { document.documentElement.style.fontSize = s === 1 ? '' : `${16 * s}px` }, scale)
            await page.waitForTimeout(options.wait)
            const result = await page.evaluate(findOverflow, options.allow)
            const label = `${url} @ ${width}px ${theme} scale ${scale}`
            if (options.shots) {
              const file = path.join(options.shots, `${shotName(url)}-${width}-${theme}-x${scale}.png`)
              await page.screenshot({ path: file, fullPage: true })
              if (scale === 1) {
                if (!sheetCells.has(url)) sheetCells.set(url, [])
                sheetCells.get(url).push({ width, theme, file, ok: !result.pageScroll && !result.offenders.length })
              }
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
      }
      await context.close()
    }
    if (options.sheet) {
      // One image per url, one block per theme: phone widths at 1:1 CSS pixels so text stays
      // readable, wider ones at half size; a red frame marks a cell with offenders.
      const sheetContext = await browser.newContext({ viewport: { width: 2000, height: 1000 } })
      const sheetPage = await sheetContext.newPage()
      for (const [url, cells] of sheetCells) {
        const blocks = options.themes.map((theme) => `<h2>${theme}</h2><div class="row">${cells.filter((c) => c.theme === theme).map((c) =>
          `<figure class="${c.ok ? '' : 'bad'}"><figcaption>${c.width}px${c.ok ? '' : ' — offenders'}</figcaption><img style="width:${c.width <= PHONE_MAX ? c.width : Math.round(c.width / 2)}px" src="data:image/png;base64,${readFileSync(c.file).toString('base64')}"></figure>`).join('')}</div>`).join('')
        await sheetPage.setContent(`<style>body{margin:8px;font:14px sans-serif;background:#888}h2{margin:8px 0 4px;font-size:16px}.row{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start}figure{margin:0;background:#fff;padding:4px}figure.bad{outline:4px solid red}img{display:block}</style><p>${url}</p>${blocks}`)
        await sheetPage.screenshot({ path: path.join(options.shots, `${shotName(url)}-sheet.png`), fullPage: true })
      }
      await sheetContext.close()
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
