# Record lifecycle: active, inactive, trash — for single rows and bulk actions

Applies to every CRUD entity people manage. No task needs to ask for it: a new entity, endpoint or list page is unfinished without it. The same rules govern an action on **one row** (toggle, row menu) and on **many rows** (bulk bar) — a bulk action is the single-row action applied to each selected row, never a different code path with looser rules.

## Contents
1. Status model
2. Moving to the trash (soft delete)
3. Trash permissions
4. Restore
5. Delete permanently (purge)
6. Status filter
7. Active toggle
8. Permissions returned by the server
9. Bulk actions
10. Checks

## 1. Status model

- `active` (boolean) beside the soft-delete pair `deletedAt` / `deletedBy`.
- **An inactive or trashed row has no effect**: an inactive account cannot sign in; an inactive or trashed role grants nothing; a trashed record is not a valid target for a new reference (cannot be assigned or linked) and drops out of responses that embed it.
- Tables without soft delete use a hard delete (section 5's warning applies directly); tables without `active` skip the activate/deactivate parts.

## 2. Moving to the trash (soft delete)

- The action, its confirmation title and its button say **"Move to trash"**, never "Delete" — nothing is destroyed; it sets `deletedAt` and `deletedBy`.
- The confirmation is one short question naming the record ("Move "Acme Ltd" to the trash?"). No explanation of soft-delete mechanics; the trash filter shows where it went. The result toast says "Moved to the trash".
- A trashed row takes no edit and no second soft delete: the server returns no edit or move-to-trash permission for it.

## 3. Permissions

Every lifecycle action is guarded by a permission: view the trash, restore, delete permanently, edit (incl. activate/deactivate), move to trash. **This guide names no permission keys** — the project's own permission scheme defines them, and the **server returns the permission keys that apply** (section 8); the frontend never hard-codes or derives them.

- Seeing the trash never implies changing it: restore and delete permanently each need their own permission **and** the view-trash permission — a caller who cannot see the trash cannot act in it. Missing permission → `403`.
- The entity's other visibility rules still apply inside the trash.
- The UI hides the Trash filter option when the returned permissions do not include viewing the trash (hidden, not disabled); the API refuses regardless.

## 4. Restore

`POST /<entities>/:id/restore`:
- requires the restore and view-trash permissions, and **only a trashed row** (`400 NOT_IN_TRASH` otherwise);
- clears `deletedAt` **and** `deletedBy`; writes `updatedBy`;
- sets `active = false` where the column exists — restoring undoes the delete, not the decision to enable the record; someone turns it on deliberately afterwards.
- UI: offered when the server returns the restore permission for the row, **no confirmation** (nothing is lost); the toast says the record came back inactive.

## 5. Delete permanently (purge)

`DELETE /<entities>/:id/permanent`:
- requires the delete-permanently and view-trash permissions, and **only a trashed row** (`400 NOT_IN_TRASH`) — nothing is destroyed in one step;
- before adding it to a table, check every foreign key pointing at it is `SET NULL` or `CASCADE` (decided per table); a `RESTRICT` turns a purge into a 500.
- UI: offered when the server returns the delete-permanently permission for the row; the confirmation is the **one place that warns**: it cannot be undone. A hard delete on a table without soft delete confirms with the same warning.

## 6. Status filter

Every soft-deleting list has a status select in its filter bar:

| Option | Query | Who sees it |
|---|---|---|
| (none) | live rows, active or not | everyone |
| Active | `?active=true` | everyone |
| Inactive | `?active=false` | everyone |
| Trash | `?trash=true` | users whose returned permissions include viewing the trash |

The frontend keeps one `status` value (`active | inactive | trash`) in the list query state (URL on the page) and maps it to these parameters. Pickers offer Active/Inactive only — a trashed record cannot be chosen — and usually fix `active=true` through `fixedFilters`.

## 7. Active toggle

- The `active` column is a **switch**, saved on click without confirmation: `PATCH /<entities>/:id { active }` → toast naming the result → list reloads.
- Enabled only when the server returns the edit permission for the row and nothing else would be refused (e.g. one's own account, a root/owner record); a disabled switch has a tooltip saying why.
- In the trash view the column shows a "Trash" chip instead of the switch; in a picker it shows a status chip (choosing is not the place to change status).
- Activate/Deactivate is not repeated in the row's actions menu — the switch is that action.

## 8. Permissions returned by the server

The server returns the permission keys that apply, in the project's own naming: the current user's permissions for the entity (e.g. with the session or the list response) and, per row, the actions this user may take on that row. The UI shows or enables every action — single row and bulk alike — only from what the server returned; the API re-checks every request. Never hard-code permission names in components beyond mapping the returned keys to actions in one place per entity.

## 9. Bulk actions

The page's table has a checkbox per row and a select-all in the header that selects **the rows of the current page**. While anything is selected, a bulk bar appears above the table: selected count, one button per action, and Clear.

| Viewing | Actions | Each applies to the selected rows whose returned permissions include |
|---|---|---|
| live rows | Activate · Deactivate · Move to trash | edit permission and inactive · edit permission and active · move-to-trash permission |
| trash | Restore · Delete permanently | restore permission · delete-permanently permission |

Entity without `active` → trash actions only; without soft delete → its hard Delete with the warning.

Same rules as a single row:
- **Applicability from each row's returned permissions**: every button shows how many selected rows it would act on — "Move to trash (3/5)" — and is disabled at 0. Only applicable rows are sent; the toggle's refusal rules (own account, root) apply per row.
- **Same confirmations**: Move to trash asks one short question with the count ("Move 3 items to the trash?"); Delete permanently warns it cannot be undone; Activate, Deactivate and Restore have no confirmation.
- **Same routes and checks**: by default one request per row on the single-row routes (`PATCH`, `DELETE`, `/restore`, `/permanent`), a few at a time (concurrency ~4), so permissions, audit/activity logs and cache invalidation are identical. A batch endpoint is allowed only when the design defines one; it must run the same per-row checks, cap the number of ids (≤ the list's maximum page size), and return a per-row result.
- **Partial failure**: a failing row does not stop the others; one summary toast reports succeeded/failed counts, with the failure reasons available (expand or details).
- **Same results**: restored rows come back inactive (the toast says so); trashed rows leave the live view.
- **Selection clears** on page change, filter/search change, reload and after every bulk action — rows off screen are never acted on.
- **Ownership**: the list exposes its selection through a bulk-actions slot / render prop and the page fills it, as it fills the row actions menu. A picker fills nothing, so it has no bulk bar; a multiple-select picker uses its checkboxes for choosing only.

## 10. Checks

API (per soft-deleting entity):
1. `?trash=true` without the view-trash permission → 403; with it → trashed rows only.
2. Restore/purge with only the action permission, or only the view-trash permission → 403; with both → success.
3. Purge or restore of a live row → `400 NOT_IN_TRASH`; restored row has `active=false`, `deletedAt`/`deletedBy` cleared.
4. Trashed rows come back without edit or move-to-trash permissions; trashed records are rejected as new references.

UI (single row and bulk):
5. Status filter shows Trash only when the returned permissions allow it; trash view swaps the switch for a chip.
6. Bulk buttons show applicable counts from the returned permissions and are disabled at 0; confirmations match the single-row ones; a partial failure reports both counts; selection clears after the action and on paging/filtering.
