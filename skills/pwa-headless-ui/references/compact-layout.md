# Compact mobile layout: no wasted space, no overflowing text

**Rule:** on a phone — mobile web, the installed PWA, and the Capacitor, Flutter or native app — screen space is the scarcest resource. Every screen fits as much useful content as it can without hurting readability or touch targets, and no text ever leaves its container or the screen.

Applies below the `md` breakpoint (and on every phone-sized app screen). Desktop layouts keep their own spacing.

## Contents
1. Space rules
2. Buttons and actions
3. Icon-left / text-right rows
4. Text overflow
5. Where it lives in the architecture
6. Flutter and native
7. Checks

## 1. Space rules
- Screen gutter 16px (12px on dense list screens); never nest gutters — a card inside a padded page does not add a second full gutter on each side.
- Vertical rhythm comes from the template's spacing tokens: 8–12px between related items, 16–24px between sections. No spacer taller than 24px, no empty hero band above the content.
- A block whose content is short does not take a full row by default: pair short fields (city + zip, date + time, quantity + unit), label/value pairs and stat tiles two per row (`grid-cols-2`) when each still fits its longest realistic content.
- Label + short value go on one line (label left, value right) instead of two stacked lines; stack only when the value is long or editable multi-line.
- Section headers put their action ("See all", "Edit", "+ Add") on the same line as the title, not on a line below it.
- No decoration that only occupies space: oversized illustrations on screens that have content, repeated titles (app bar title + the same page heading), empty card headers, dividers plus margins doing the same job.
- Chrome stays small: one app bar row (≤ 56px), bottom nav ≤ 64px plus the safe area; secondary toolbars collapse on scroll or move into a menu or sheet.
- Space is never saved by shrinking touch targets below 44px / 48dp, body text below 14px (inputs stay 16px to avoid iOS zoom), or contrast.

## 2. Buttons and actions
- Two adjacent buttons share one row when both labels fit on one line: `grid grid-cols-2 gap-2` (equal width) or `flex gap-2` with the primary `flex-1`. Typical pairs: Cancel / Save, Back / Next, Decline / Accept, Reset / Apply.
- Stack them full-width only when a label would wrap or truncate at 360px in the longest supported locale. Decide with the real translated strings, not the English ones.
- Three or more actions: one primary button plus the rest in an overflow menu or sheet, or icon buttons with `aria-label` in one row. Never a column of three full-width buttons.
- A lone secondary or text action sits inline with related content (end of the row, in the section header) rather than on its own full-width line.
- Sticky bottom action bars hold a single row; they include the safe-area inset once.
- Filter chips, tabs and segmented controls stay on one horizontally scrollable row instead of wrapping to several lines.
- Horizontal scrollers on phones are swipe-only: the content scrolls by dragging and the scrollbar is never drawn (it costs height and looks like a desktop page). Hide it in the core component, not per feature:
  ```css
  .scroll-row {
    overflow-x: auto;
    scrollbar-width: none;            /* Firefox, current Chromium and Safari */
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-x: contain;   /* do not trigger swipe-back or page scroll chaining */
  }
  .scroll-row::-webkit-scrollbar { display: none; } /* older WebKit / Android WebView */
  ```
  Show that more content exists another way: let the last visible item be cut at the edge, or fade the edge. Items stay reachable by keyboard (focus scrolls them into view) and the row keeps `scroll-snap` optional. Desktop layouts (`md:` and up) may show the scrollbar again.

## 3. Icon-left / text-right rows
The pattern `[icon] title / description` wastes the left side of the screen when it is built carelessly. Review every such row:
- The icon column is only as wide as the icon: icon 20–24px (avatar/thumbnail 40px) + 12px gap. No fixed wide column, no padding around the icon beyond what its touch target needs when it is tappable.
- When the text block is much taller than the icon (3+ lines, or a title followed by a paragraph, fields or buttons), do not leave an empty strip under the icon: put the icon inline with the title on the first line and let the rest span the full width below. Indented text under an icon is acceptable only for 1–2 lines.
- Do not reserve the icon indent for rows that have no icon. In one list either every row has an icon or none does; if a few lack one, give them a fallback icon rather than a blank slot.
- Content below a row (helper text, error, nested actions, expanded details) aligns to the container edge, not to the text column, unless it is a single short line.
- The icon aligns to the first text line (`items-start` with the icon box matching the title line-height); it is centered only when the row is a single line.
- The text column is `min-w-0 flex-1`; trailing elements (value, chevron, switch, badge) are `shrink-0` and sit on the same line as the title.
- A decorative icon that adds no meaning and no scanning value is removed instead of kept as a space-consuming ornament.

```html
<!-- Short row: icon column as narrow as the icon, text takes the rest -->
<div class="flex items-start gap-3">
  <Icon class="size-5 shrink-0" />
  <div class="min-w-0 flex-1">
    <p class="truncate">Title</p>
    <p class="line-clamp-2 break-words">Description</p>
  </div>
  <span class="shrink-0">Value</span>
</div>

<!-- Tall block: icon inline with the title, body uses the full width -->
<div>
  <div class="flex items-center gap-2">
    <Icon class="size-5 shrink-0" />
    <h3 class="min-w-0 flex-1 truncate">Title</h3>
  </div>
  <p class="mt-2 break-words">Long body text, fields or buttons start at the container edge.</p>
</div>
```

## 4. Text overflow
No text may be clipped by its container without an ellipsis, overlap a neighbor, or push the page wider than the viewport.
- Every flex or grid child that holds text has `min-w-0` (flex items default to `min-width: auto` and refuse to shrink — the most common cause of overflow).
- Decide per text element and state it in the UI spec:
  - **Single line, identifying** (titles in rows, tabs, chips, buttons, app bar): `truncate`; the full value stays reachable (detail screen, expand on tap, or `title`/long-press).
  - **Multi-line, bounded** (descriptions, previews, notifications): `line-clamp-2` / `line-clamp-3`.
  - **Must be read in full** (errors, legal text, form labels, prices, totals): wrap, never truncate.
- Unbreakable strings — emails, URLs, IDs, tokens, file names, long words in German/Finnish-style locales — get `break-words` (`overflow-wrap: anywhere`) or middle truncation when both ends matter.
- Numbers and money are never truncated: use `tabular-nums`, `shrink-0`, `whitespace-nowrap`, and let the label next to them truncate instead. Compact notation (`1.2M`) when the full number cannot fit.
- Buttons: a label that does not fit on one line means the layout is wrong — shorten the copy, stack the pair (§2) or switch to an icon button; do not let it wrap to three lines or clip.
- Badges and chips have a `max-w-*` and truncate; table cells on mobile become cards (`list-page.md`) instead of a horizontally scrolling page.
- Fixed heights on text containers are forbidden (`h-10` on a block that can hold two lines); use `min-h-*` so a larger font scale or a longer translation grows the box.
- Test content is the worst realistic case: the longest supported locale, a 60-character name without spaces, a 7-digit amount, and OS font scale 130%.
- Only intended scrollers (chip row, carousel, code block) scroll horizontally; the page itself never does.

## 5. Where it lives in the architecture
- Density is a template concern: spacing tokens (`--space-*`, `--gutter`, `--row-gap`) in `tokens.css` and recipes; core components expose semantic props (`<UiButtonGroup>`, `<UiListItem icon title description trailing>`, `<UiField inline>`), not spacing classes.
- `UiScrollRow` (and every core component that scrolls horizontally: tabs, chip groups, carousels) owns the hidden scrollbar, edge fade and overscroll containment.
- `UiButtonGroup` owns the "one row when it fits, stacked otherwise" behavior so features never hand-roll it; `UiListItem` owns the icon column, `min-w-0` and truncation rules so every row gets them for free.
- Feature code that adds its own margins, fixed widths or a second wrapper with padding around a core component is a review finding.

## 6. Flutter and native
- Flutter: wrap text inside a `Row` in `Expanded`/`Flexible` and set `maxLines` + `overflow: TextOverflow.ellipsis` (or `softWrap: true` for must-read text); two buttons in a `Row` with `Expanded` children and an 8px gap, falling back to a `Column` through `LayoutBuilder` or `Wrap` when labels do not fit; horizontal lists (`ListView` / `SingleChildScrollView` with `scrollDirection: Axis.horizontal`) are not wrapped in a `Scrollbar` and use `ScrollConfiguration.of(context).copyWith(scrollbars: false)` on platforms that add one; `ListTile` with `dense: true`, `visualDensity: VisualDensity.compact`, `minLeadingWidth` sized to the icon and `horizontalTitleGap: 12`; no `SizedBox` spacers above 24. A `RenderFlex overflowed` message in debug or test output is a defect — it must never appear.
- SwiftUI: `lineLimit` + `truncationMode`, `minimumScaleFactor` only for single-line numbers, `layoutPriority` for the text that must stay whole, `ViewThatFits` to switch a button pair from `HStack` to `VStack`; support Dynamic Type.
- SwiftUI horizontal `ScrollView` uses `showsIndicators: false` (`.scrollIndicators(.hidden)`); Compose `LazyRow` / `horizontalScroll` draw no scrollbar by default — do not add one.
- Compose: `maxLines` + `TextOverflow.Ellipsis`, `Modifier.weight(1f)` on the text column, `FlowRow` or a measured fallback for button pairs; support font scale.

## 7. Checks
Run at 360×800 and 390×844, then with font scale 130% and the longest locale:
1. No horizontal page scroll: `document.documentElement.scrollWidth <= document.documentElement.clientWidth` (not `window.innerWidth`, which grows when a phone zooms out to fit overflowing content).
2. No element sticks out of the viewport and no text is clipped (horizontally or vertically) without an ellipsis or line clamp. Items 1 and 2 are decided by `node .claude/team/overflow-check.mjs <url>...` (Playwright; both viewports, then font scale 130%; `--allow <selector>` for a deliberate exception). On Playwright MCP or Claude in Chrome, evaluate the `findOverflow` function from that file in the page instead. Content inside an intended horizontal scroller is skipped automatically.
3. Adjacent button pairs whose labels fit share one row; no column of stacked full-width buttons where a row fits.
4. Icon/text rows: icon column no wider than icon + gap, no empty strip under the icon next to a tall text block, no blank icon slot on icon-less rows.
5. Short fields and label/value pairs that fit are paired on one row; section actions sit on the header line.
6. Long-content screenshot per screen (worst-case strings) attached to the task notes; Flutter test and debug output contains no `overflowed`.
7. Horizontal scrollers (chip rows, tabs, carousels, wide tables) scroll by swipe and draw no scrollbar on phone viewports — also reported by `overflow-check.mjs`.
