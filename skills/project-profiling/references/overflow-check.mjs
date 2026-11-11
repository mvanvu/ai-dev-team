#!/usr/bin/env node
// Layout overflow check and screenshot sweep for the ai-dev-team rules COMPACT-1 (no horizontal
// page scroll), COMPACT-2 (nothing sticks out of the viewport, no text clipped without an
// ellipsis), COMPACT-7 (horizontal scrollers draw no scrollbar on phones) and the COST sweep
// (every width x every theme in one browser launch, one contact sheet per url).
//
// Usage: node $TEAM_BIN/overflow-check.mjs [options] <url> [<url>...]
//   --widths <list>    comma-separated viewport widths (default 360,390; the sweep uses the profile's ui_widths)
//   --themes <list>    comma-separated themes, e.g. light,dark (default light)
//   --theme-set <js>   function body run in the page after load with `theme` in scope, for apps that
//                      switch theme by attribute or class instead of prefers-color-scheme
//   --scale <n>        also run phone widths (< 768) with the root font size multiplied by n (default 1.3; 1 disables)
//   --allow <selector> ignore elements matching this CSS selector and their descendants (repeatable)
//   --shots <dir>      save a full-page screenshot per url / width / theme / scale, and write
//                      <dir>/build-id.txt from `rule-checks.sh build-id` beside this script
//   --sheet            with --shots: also write <dir>/<url>-sheet.png, every width x theme of that url on one image
//   --storage <file>   Playwright storage state (logged-in session)
//   --init <file>      script run in every page before the app loads (Playwright addInitScript), e.g. to seed
//                      localStorage with worst-case content; the profile's ui_seed names it (repeatable)
//   --verbose          one line per offender per cell; by default offenders are grouped across cells
//   --wait <ms>        extra wait after the load event (default 300)
//   --ready <selector> after load, wait up to 15 s for this selector (apps that render after fetching);
//                      on timeout a warning line is printed and the check continues
// Exit: 0 clean, 1 offenders found, 2 Playwright is not installed, 64 usage error.
//
// Playwright is resolved from $PLAYWRIGHT_DIR (a directory containing node_modules), then the
// project in the current directory, then the shared QA tools folder (${XDG_STATE_HOME:-~/.local/state}/ai-dev-team/qa-tools).
// Horizontal scrollers: an element with overflow-x auto/scroll whose overflow-y is not auto/scroll
// (as written in the CSS), or any element with the data-scroll-row attribute; their content may be
// wider than the viewport. A vertical scroller (fixed-shell page body) is checked like the page:
// what sticks out of it is reported, and it is reported itself when it scrolls horizontally.
//
// Other engines (Playwright MCP, Claude in Chrome): evaluate the body of `findOverflow`
// in the page at each width; an empty `offenders` array and `pageScroll: false` pass.
import { createRequire } from 'node:module'
import { execFileSync } from 'node:child_process'
import { accessSync, constants, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

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
  const scrolls = (value) => value === 'auto' || value === 'scroll'
  const clips = (value) => value === 'hidden' || value === 'clip'
  // The computed overflow-y of `overflow-x: auto` alone is auto as well, so the authored value is
  // read by forcing overflow-x to visible for a moment (then overflow-y computes to what was written).
  const rowCache = new Map()
  const isScrollRow = (node) => {
    if (rowCache.has(node)) return rowCache.get(node)
    let row = node.hasAttribute('data-scroll-row')
    if (!row && scrolls(getComputedStyle(node).overflowX)) {
      const style = node.getAttribute('style')
      node.style.setProperty('overflow-x', 'visible', 'important')
      row = !scrolls(getComputedStyle(node).overflowY)
      if (style === null) node.removeAttribute('style')
      else node.setAttribute('style', style)
    }
    rowCache.set(node, row)
    return row
  }
  const ignored = (el) => {
    for (let node = el; node && node !== document.documentElement; node = node.parentElement) {
      if (allow.some((selector) => node.matches(selector))) return true
      if (node.getAttribute('aria-hidden') === 'true' || node.hasAttribute('inert')) return true
      const cs = getComputedStyle(node)
      if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') return true
      // Intended horizontal scrollers (chip rows, carousels, code blocks) may hold wider content.
      if (node !== el && isScrollRow(node)) return true
    }
    return false
  }
  // The part of `rect` left visible by ancestors that clip it (overflow hidden/clip), following the
  // containing-block chain: fixed boxes escape every ancestor without a transform, absolute boxes
  // escape static ones. html and body are not counted: what they cut off falls off the screen,
  // which is the defect itself.
  const visibleRect = (el, rect) => {
    let { left, right, top, bottom } = rect
    let position = getComputedStyle(el).position
    for (let node = el.parentElement; node && node !== document.body && node !== document.documentElement; node = node.parentElement) {
      const cs = getComputedStyle(node)
      const transformed = cs.transform !== 'none' || cs.filter !== 'none' || /paint|layout|strict|content/.test(cs.contain)
      if (position === 'fixed' && !transformed) continue
      if (position === 'absolute' && cs.position === 'static' && !transformed) continue
      const r = node.getBoundingClientRect()
      if (clips(cs.overflowX)) { left = Math.max(left, r.left); right = Math.min(right, r.right) }
      if (clips(cs.overflowY)) { top = Math.max(top, r.top); bottom = Math.min(bottom, r.bottom) }
      position = cs.position
    }
    return { left, right, top, bottom }
  }
  const offenders = []
  for (const el of document.querySelectorAll('body *')) {
    const rect = el.getBoundingClientRect()
    // Zero-size and 1px visually-hidden elements carry no visible layout.
    if (rect.width <= 2 || rect.height <= 2) continue
    // Entirely off-canvas (closed drawer, skip link at left:-9999px): nothing visible sticks out.
    if (rect.right <= 0 || rect.left >= vw) continue
    if (ignored(el)) continue
    const visible = visibleRect(el, rect)
    // Clipped away by an ancestor (inactive carousel slide, collapsed panel).
    if (visible.right - visible.left < 1 || visible.bottom - visible.top < 1) continue
    const cs = getComputedStyle(el)
    const scrollsX = scrolls(cs.overflowX) && el.scrollWidth > el.clientWidth + 1
    if (scrollsX && isScrollRow(el)) {
      if (cs.scrollbarWidth !== 'none' && getComputedStyle(el, '::-webkit-scrollbar').display !== 'none') {
        offenders.push({ rule: 'COMPACT-7', kind: 'visible-horizontal-scrollbar', el: describe(el) })
      }
    } else if (scrollsX) {
      // A vertical scroller (fixed-shell page) that also scrolls sideways: the page scrolls horizontally.
      offenders.push({ rule: 'COMPACT-1', kind: 'scroller-scrolls-horizontally', el: describe(el), right: el.scrollWidth })
    }
    if (visible.right > vw + 1 || visible.left < -1) {
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
    shots: null, sheet: false, storage: null, wait: 300, ready: null, urls: [], init: [], verbose: false,
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
    else if (arg === '--init') options.init.push(argv[++i])
    else if (arg === '--verbose') options.verbose = true
    else if (arg === '--wait') options.wait = Number(argv[++i])
    else if (arg === '--ready') options.ready = argv[++i]
    else if (arg.startsWith('--')) return null
    else options.urls.push(arg)
  }
  const valid = options.urls.length && options.scale > 0 && options.themes.length
    && options.widths.length && options.widths.every((w) => Number.isInteger(w) && w > 0)
    && Number.isFinite(options.wait) && options.wait >= 0 && (options.ready === null || Boolean(options.ready))
    && (!options.sheet || options.shots)
  return valid ? options : null
}

function loadChromium() {
  // Resolve from the project being tested (or its QA tools folder), not from this script's folder.
  const bases = [
    process.env.PLAYWRIGHT_DIR && path.resolve(process.env.PLAYWRIGHT_DIR),
    process.cwd(),
    path.join(process.env.XDG_STATE_HOME || path.join(os.homedir(), '.local', 'state'), 'ai-dev-team', 'qa-tools'),
  ].filter(Boolean)
  for (const base of bases) {
    const require = createRequire(path.join(base, 'package.json'))
    for (const name of ['playwright', '@playwright/test', 'playwright-core']) {
      try {
        return require(name).chromium
      } catch {
        // try the next package name or folder
      }
    }
  }
  return null
}

// File-name stem per url from path + query + hash, so hash routes and query strings do not collide.
function shotNames(urls) {
  const names = new Map()
  const used = new Set()
  urls.forEach((url, index) => {
    const parsed = new URL(url)
    let name = `${parsed.pathname}${parsed.search}${parsed.hash}`.replace(/\W+/g, '_').replace(/^_+|_+$/g, '').slice(0, 120)
    if (!name || used.has(name)) name = `${name ? `${name}-` : 'url'}${index + 1}`
    used.add(name)
    names.set(url, name)
  })
  return names
}

// Records which build the screenshots show, so later agents can tell whether a sweep is stale.
function writeBuildId(dir) {
  const script = path.join(path.dirname(fileURLToPath(import.meta.url)), 'rule-checks.sh')
  try {
    accessSync(script, constants.X_OK)
    const id = execFileSync(script, ['build-id'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim()
    if (id) writeFileSync(path.join(dir, 'build-id.txt'), `${id}\n`)
  } catch {
    // no script or no build id: the shots stay without one
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2))
  if (!options) {
    console.error('usage: overflow-check.mjs [--widths list] [--themes list] [--theme-set js] [--scale n] [--allow selector] [--shots dir [--sheet]] [--storage file] [--init file] [--wait ms] [--ready selector] [--verbose] <url>...')
    process.exit(64)
  }
  const chromium = loadChromium()
  if (!chromium) {
    console.error('COMPACT-1 COMPACT-2 COMPACT-7 not-run: playwright not found; install it in ~/.local/state/ai-dev-team/qa-tools (cd there && npm init -y && npm i -D playwright && npx playwright install chromium --only-shell), never in the project, or set PLAYWRIGHT_DIR')
    process.exit(2)
  }
  if (options.shots) mkdirSync(options.shots, { recursive: true })
  const fontScales = options.scale === 1 ? [1] : [1, options.scale]
  const names = shotNames(options.urls)
  const shotName = (url) => names.get(url)
  const sheetCells = new Map()
  const browser = await chromium.launch()
  let failures = 0
  // Grouped report: the same offender in many cells is one line listing the cells.
  const groups = new Map()
  const report = (key, label) => {
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(label)
  }
  let clean = 0
  try {
    for (const width of options.widths) {
      const phone = width <= PHONE_MAX
      const context = await browser.newContext({
        viewport: viewportFor(width), isMobile: phone, hasTouch: phone, deviceScaleFactor: phone ? 2 : 1,
        ...(options.storage ? { storageState: options.storage } : {}),
      })
      for (const file of options.init) await context.addInitScript({ path: file })
      const page = await context.newPage()
      for (const url of options.urls) {
        for (const theme of options.themes) {
          await page.emulateMedia({ colorScheme: theme === 'dark' ? 'dark' : 'light' })
          // 'load', not 'networkidle': pages that poll or stream never go idle.
          await page.goto(url, { waitUntil: 'load' })
          if (options.ready) {
            try {
              await page.waitForSelector(options.ready, { timeout: 15000 })
            } catch {
              console.log(`warning ${url} @ ${width}px ${theme}: --ready ${options.ready} not found after 15 s, checking anyway`)
            }
          }
          if (options.themeSet) {
            await page.evaluate(({ body, theme }) => new Function('theme', body)(theme), { body: options.themeSet, theme })
          }
          for (const scale of phone ? fontScales : [1]) {
            // Approximates the OS font scale for rem-based layouts.
            await page.evaluate((s) => { document.documentElement.style.fontSize = s === 1 ? '' : `${16 * s}px` }, scale)
            await page.waitForTimeout(options.wait)
            const result = await page.evaluate(findOverflow, options.allow)
            const label = `${url} @ ${width}px ${theme} scale ${scale}`
            const cell = `${width} ${theme}${scale === 1 ? '' : ` x${scale}`}`
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
              if (options.verbose) console.log(`COMPACT-1 ${label}: page scrolls horizontally (scrollWidth ${result.scrollWidth} > ${result.viewport})`)
              else report(`COMPACT-1 ${url}: page scrolls horizontally`, cell)
            }
            for (const offender of result.offenders) {
              failures++
              if (options.verbose) console.log(`${offender.rule} ${label}: ${offender.kind} ${offender.el}`)
              else report(`${offender.rule} ${url}: ${offender.kind} ${offender.el}`, cell)
            }
            if (!result.pageScroll && !result.offenders.length) {
              clean++
              if (options.verbose) console.log(`COMPACT-1 COMPACT-2 COMPACT-7 ok ${label}`)
            }
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
  if (!options.verbose) {
    for (const [key, cells] of groups) console.log(`${key} — ${cells.length} cell(s): ${cells.join(', ')}`)
    console.log(`summary: ${clean} clean cell(s), ${groups.size} distinct offender(s), ${failures} occurrence(s)`)
  }
  if (options.shots) writeBuildId(options.shots)
  process.exit(failures ? 1 : 0)
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  main().catch((error) => {
    console.error(error)
    process.exit(70)
  })
}
