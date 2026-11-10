# List pages and pickers: one list component, two uses

**Rule:** every resource shown as a paginated list gets **one list component** (`<Resource>List`, e.g. `ProductList`) with search, filters, sorting, pagination, column toggling and all screen states. The same component serves:
1. **List page** — the resource's page (`/products`), with row actions and bulk actions.
2. **Picker** — an input that selects records of that resource (in a form or a filter of another list). Clicking it opens a modal containing the same list component; the user picks **one or many** depending on the input's props.

There is never a second, simplified list for picking: filters, columns and fixes are written once.

## Contents
1. Building blocks
2. List component API
3. Column rules (order, ID, actions, visibility)
4. Filter bar, sorting, pagination
5. State: URL query only (filters), localStorage only for columns
6. Picker input and modal
7. Screen states and mobile layout
8. API contract
9. Tests and checks

## 1. Building blocks

| Layer | Piece | Role |
|---|---|---|
| Core (`src/ui/core/`) | `UiDataList` | Generic list shell: filter bar slot, column chooser, table (cards on mobile), selection, `UiPagination`, states. Built on TanStack Table (`@tanstack/vue-table` / `@tanstack/react-table`) for column visibility, row selection and manual sorting — wrapped here, never imported by features |
| Core | `UiPickerInput` | Input that shows the selected value(s) and opens `UiDialog` (sheet below `md`) with the list inside |
| Core | `useListQuery()` | Filters, search, sort, page and page size; URL query (history state) when `syncUrl`, memory otherwise — never localStorage (section 5) |
| Core | `useColumnVisibility()` | Hidden columns per list in localStorage (section 3) |
| Feature (`src/features/<resource>/`) | `<Resource>List` | Columns, filters, fetch for one resource, built on `UiDataList` |
| Feature | `<Resource>Page` | Page header + `<Resource>List syncUrl` + row/bulk actions |
| Feature | `<Resource>Picker` | `UiPickerInput` preset with `<Resource>List` |

If the project already has its own table/list component or UI kit, keep it and implement the same contract (API, column rules, state, picker) on top of it.

## 2. List component API

```ts
interface ResourceListProps<Row> {
  selectionMode?: 'none' | 'single' | 'multiple' // 'none' on the page (bulk selection is separate)
  selected?: Row['id'][]                         // picker: preselected ids
  syncUrl?: boolean                              // page only: filters/sort/page in the URL query (never localStorage)
  fixedFilters?: Partial<Filters>                // picker: constraints from the caller (e.g. active only)
  excludeIds?: Row['id'][]                       // picker: rows that may not be chosen
  max?: number                                   // multiple: selection cap
}
// Events / callbacks: select(row) (single), selectionChange(rows) (multiple), failure(message)
// Slots / render props: rowActions(row), bulkActions(rows, clear), filters (extra filter fields)
// Exposed: reload(), resetFilters()
```

- Page mode (`selectionMode: 'none'`, `syncUrl`): active switch column, row actions, bulk actions and the status filter (Active / Inactive / Trash) following `ai-dev-team:technical-design` → `references/record-lifecycle.md`.
- Picker mode: no row or bulk actions, no Trash status (a trashed record cannot be chosen), status shown as a chip, `fixedFilters` applied and hidden from the filter bar, `excludeIds` rows disabled with a reason.

## 3. Column rules

**Order (left → right):** selection checkbox (when selecting) → **always-visible identifying columns** (title / name, with description or subtitle under it or next to it) → other data columns → **actions** → **ID**.

- **ID last**: when the resource has an auto-increment ID, it is the last column, right-aligned, sortable (it is the default sort, newest first), and toggleable.
- **Actions before ID**: one icon button (`⋮` / more icon, `aria-label="Actions"`) that opens a menu of row actions; the menu hides actions the user may not run. The column exists only when something can appear in it: on the page when there are row actions, in a single-select picker for the **Choose** button; otherwise it is omitted (no empty "Actions" column).
- **Always-visible columns**: columns marked `alwaysVisible` — the identifying ones such as title, name, description — plus selection and actions cannot be hidden and are not listed as toggleable in the column chooser.
- **Column chooser**: a columns button in the filter bar opens a checklist of toggleable columns with "Reset columns". Visibility is saved in localStorage per list:
  - key `list-columns:v1:<host>:<listKey>`, value = array of **hidden** column ids, so new columns appear with their default visibility;
  - unknown ids are ignored; reads/writes are wrapped in try/catch and fall back to defaults (private mode, blocked storage);
  - the picker uses its own key (`<listKey>:picker`) with narrower defaults, since the modal has less width than the page.
- Columns declare `id`, `header`, `cell`, `alwaysVisible?`, `defaultHidden?`, `sortKey?` (API field name; only these are sortable), `minWidth?`, `mobile: 'title' | 'subtitle' | 'meta' | 'hidden'` for the card layout.

## 4. Filter bar, sorting, pagination

- Soft-deleting resources have a status select (none / Active / Inactive / Trash — Trash only when the server-returned permissions allow viewing the trash), per `record-lifecycle.md` §6.
- Filter bar: search input (debounced ~300ms, grows to fill), **Filters** button opening a menu/sheet with the resource's filter fields (label shows the single active value or a count), **Reset filters** (only when something is set), **Reload**, **Columns**.
- Filter fields that select records of another resource use that resource's picker (`<Resource>Picker multiple`) — the same pattern recursively.
- Sorting is server-side: clicking a sortable header sets `order` (e.g. `name asc`); the table never re-sorts the current page locally.
- Pagination: `UiPagination` with the truncated range (`architecture.md` §4a), page-size selector (e.g. 10 / 25 / 50 / 100, capped by the API's maximum), total count ("1–25 of 342"). Changing filters, search or page size resets to page 1. A page past the end after a delete clamps to the last page.

## 5. State: URL query only (filters), localStorage only for columns

`useListQuery(defaults, { syncUrl })`:
- **Filters are never saved to localStorage** (or sessionStorage / IndexedDB). The URL query is their only home on a page.
- **Page (`syncUrl: true`)**: filters, search, order, page and page size are read from and written to the URL query params through the router's history (`router.replace` / `history.replaceState`), so the current view is a shareable link, survives reload, and is restored when the user comes back to the list with Back from a detail page. Using `replace` keeps typing and paging from piling up history entries.
- Only non-default values are written (`?status=active&page=3`, no `?page=1`); unknown or invalid params fall back to defaults and are dropped from the URL.
- Opening the list from the menu (no query) shows the defaults — the previous session's filters are not brought back.
- **Picker (`syncUrl: false`)**: everything stays in memory; opening a picker must never change the page's URL. Each opening starts from defaults + `fixedFilters`.
- Column visibility is the only list preference kept in localStorage (section 3).
- One state change → one request; in-flight requests are cancelled when the query changes (AbortController / TanStack Query keys).

## 6. Picker input and modal

```ts
interface ResourcePickerProps<Row> {
  modelValue: Row['id'] | Row['id'][] | null
  multiple?: boolean          // false → single select, true → multiple
  max?: number
  fixedFilters?: Partial<Filters>
  excludeIds?: Row['id'][]
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
}
```

- **Input**: shows the selected record's label (single) or chips (multiple, "+N" when they overflow), a clear button, and opens the modal on click, Enter or Space. It is a button-like control with `aria-haspopup="dialog"`, not a free-text field.
- **Labels for ids**: when the value holds ids without rows (from the URL or a saved form), the input fetches labels with `GET /<resource>?ids=1,2,3` and caches them.
- **Modal**: `UiDialog` (full-screen sheet below `md`) with a title ("Choose product"), the `<Resource>List` in picker mode, and:
  - **single**: clicking a row (or its **Choose** button) emits the value and closes the modal;
  - **multiple**: checkboxes; the selection is kept by id **across pages, searches and filters**; the footer shows "N selected" with a link to show only selected rows, **Clear**, **Cancel** and **Confirm**; `max` disables further checks with a hint; Confirm emits the ids and closes;
  - preselected values are checked when the modal opens; Cancel or Esc discards changes.
- Focus moves into the modal on open and returns to the input on close.

## 6a. Row actions and bulk actions

Row actions (the `⋮` menu), the active switch and the bulk bar follow `ai-dev-team:technical-design` → `references/record-lifecycle.md` (§2–§9: which actions appear where — Activate/Deactivate is the switch, never a row-menu item — permissions returned by the server, confirmations and undo, batch endpoint, partial failure, selection clearing). This file does not restate them.
- `UiDataList` provides the selection, the bulk bar shell and a `useBulkActions()` runner (one batch request, per-row result summary; the per-row fallback of record-lifecycle §9 when no batch endpoint exists); the page supplies the actions.

## 7. Screen states and mobile layout

- States: loading (skeleton rows matching columns), empty (with a create action on the page), **empty because of filters** (message + Reset filters), error (message + Retry), offline (`connectivity.md`).
- Below `md` the table becomes a card list: the `title` column as the heading, `subtitle` under it, `meta` columns as small key–value lines, actions as a `⋮` button at the card's top right, ID in the meta line. The column chooser applies to the card fields.
- Wide tables scroll horizontally inside the list container with the identifying column sticky on the left; the page itself never scrolls sideways.

## 8. API contract (plan)

Every list endpoint used by a list component provides: `limit` + `offset` (or `page` + `pageSize`) with a server-enforced maximum, `search`, `order` restricted to an allowlist of fields, the resource's filters, `ids` for resolving picker labels, and a response `{ items, total }`. The server returns the permission keys that apply — the user's permissions for the resource and, per item, the actions allowed on it — in the project's own naming, so the frontend does not guess.

## 9. Tests and checks

1. Unit: `useListQuery` (state read from and written to the URL query with `replace`, nothing written to any storage, defaults omitted from the URL, invalid params dropped, picker mode never touches the URL, reset), `useColumnVisibility` (always-visible columns cannot be hidden, unknown ids ignored, storage failure falls back), column order helper (actions before ID, ID last, empty actions column omitted).
2. Lifecycle: checks in `record-lifecycle.md` §10 for the row menu, active switch and bulk bar.
3. Component: picker single closes on choose and emits one id; picker multiple keeps the selection across pages and filters, respects `max`, Cancel discards; preselected ids are checked.
4. QA in the browser: list page filters/sort/page survive reload and Back via the URL query; localStorage holds no filter keys; opening the list from the menu shows defaults; column toggles survive reload; title/name columns cannot be hidden; opening the picker does not change the page URL; mobile shows cards.
