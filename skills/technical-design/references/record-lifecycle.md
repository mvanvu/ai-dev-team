# Record lifecycle: active, inactive, trash — for single rows and bulk actions

**Scope is a design decision, made per entity.** The lifecycle applies by default to user-managed master data — customers, products, staff, categories, suppliers and the like. It does not apply to child / line rows (order lines, addresses owned by a parent), join tables, settings, audit and event logs, messages, or data governed by erasure or retention rules. The design lists, for every entity it adds or changes, whether the lifecycle applies (full, trash only, active only, or none); when the request did not say, it records an open question with "lifecycle" as the proposed default for master data. The same rules govern an action on **one row** (toggle, row menu) and on **many rows** (bulk bar) — a bulk action is the single-row action applied to each selected row, never a different code path with looser rules.

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
- **Unique constraints and the trash**: a trashed row must not block a new live row with the same natural key. Make each unique constraint a partial unique index over non-trashed rows (e.g. `UNIQUE (tenant_id, code) WHERE deleted_at IS NULL`, or the database's equivalent), or the design states how duplicates are handled (restore refused with `409 DUPLICATE` naming the live row, or the trashed row's key is changed on trashing).

## 2. Moving to the trash (soft delete)

- The action, its confirmation title and its button say **"Move to trash"**, never "Delete" — nothing is destroyed; it sets `deletedAt` and `deletedBy`.
- **No confirmation question** — the action is reversible. It runs at once and the toast says "Moved to the trash" with an **Undo** action (Undo restores it as it was, including `active`). No explanation of soft-delete mechanics; the trash filter shows where it went.
- One rule for every confirmation in the app: reversible actions (move to trash, deactivate) run immediately with an undo toast; irreversible ones (delete permanently, hard delete on a table without trash) ask for confirmation with a warning (section 5).
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
- foreign keys pointing at a purgeable table default to `RESTRICT`; the API maps the violation to `409 IN_USE` naming the referencing records (type and label, or a count), never a 500. `CASCADE` only for owned child rows that mean nothing without the parent; `SET NULL` only for optional links. The design decides this per foreign key.
- retention: when the design or a regulation sets a trash retention period, a scheduled job purges trashed rows older than it under the same foreign-key rules. Personal-data erasure requests are not satisfied by moving to the trash — the design says how erased data is purged or anonymized, including backups and logs where they apply.
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

- The `active` column is a **switch**, saved on click without confirmation: `PATCH /<entities>/:id { active }` → toast naming the result (with Undo after a deactivation) → list reloads.
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
- **Same confirmations**: Activate, Deactivate, Move to trash and Restore run without a confirmation question; Deactivate and Move to trash show an undo toast with the count ("3 moved to the trash · Undo"); Delete permanently warns it cannot be undone.
- **Batch endpoint by default**: one request per bulk action (e.g. `POST /<entities>/bulk { action, ids }`, or one route per action). The server loads all ids in one query, runs the single-row permission and state checks per row in memory, writes each outcome group with one set-based statement in a transaction, writes audit/activity entries in bulk, caps the number of ids (≤ the list's maximum page size), and returns a per-row result (`id`, `ok`, error code). This satisfies `ai-dev-team:code-review-checklist` → `references/query-performance.md` (QUERY-3, QUERY-5).
- **Exception**: while no batch endpoint exists yet, a selection of **≤ 20 rows** may run one request per row on the single-row routes (`PATCH`, `DELETE`, `/restore`, `/permanent`), a few at a time (concurrency ~4). Larger selections need the batch endpoint.
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

Design and data:
7. The design lists per entity whether the lifecycle applies; an unstated case is an open question with "lifecycle" proposed for master data.
8. Bulk actions use a batch endpoint (one id-load query, per-row checks in memory, set-based writes, per-row result) — per-row requests only for selections ≤ 20 rows while no batch endpoint exists.
9. Unique constraints on soft-deleting tables are partial over non-trashed rows, or the design states how duplicates are handled.
10. Foreign keys into purgeable tables are `RESTRICT` unless the design chose `CASCADE` (owned child rows) or `SET NULL` (optional links); a blocked purge returns `409 IN_USE` naming the referencing records.
11. Move to trash and deactivate run without a confirmation question and offer Undo; purge and hard delete confirm with a warning.
