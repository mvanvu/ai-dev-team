# Query performance: no N+1, no per-row round trips

**Rule:** the number of database queries and network requests a piece of code makes must not grow with the number of rows it handles. Loading a page of 50 records costs the same number of queries as loading a page of 5.

Applies to backend data access (ORM, query builder, raw SQL, GraphQL resolvers, serializers, background jobs) and to clients (web and mobile) that fetch data per row.

## Contents
1. What N+1 looks like
2. How to fix it
3. Proving it
4. Checks

## 1. What N+1 looks like
- A query, ORM call or repository method inside a loop, `map`/`forEach`, a template loop, or a recursive function.
- Lazy-loaded relations touched while iterating: `order.customer.name` for each order, `post.comments.length`, a computed property or accessor that queries.
- Serializers, API resources, transformers and view models that load related data per item; GraphQL field resolvers that query per parent.
- Per-row `COUNT`, `EXISTS`, `SUM` or permission lookups instead of one grouped query.
- Per-row writes: `save()` / `INSERT` / `UPDATE` / `DELETE` in a loop for bulk actions and imports.
- Hidden per-row work: model events, observers, audit hooks, cache lookups or authorization checks that query for each record.
- Client side: one request per list row (`GET /users/:id` for each row, a query hook inside a row component), or sequential awaits in a loop where a batch endpoint exists.

## 2. How to fix it
- **Eager-load** the relations the response needs in the same query plan: join, or a second query with `WHERE id IN (...)` (`with`/`include`/`preload`/`select_related`/`prefetch_related`/`JOIN FETCH`/entity graph — whatever the ORM calls it). Declare them at the query, driven by what the endpoint returns.
- **Batch by key**: collect IDs, run one query, group the result in memory by key. GraphQL uses a per-request DataLoader (or the framework's batching) for every relation resolver.
- **Aggregate in SQL**: one `GROUP BY` (or a subquery/window function) for per-row counts and sums.
- **Set-based writes**: one `UPDATE ... WHERE id IN (...)`, bulk insert, or upsert; chunk large sets (e.g. 500–1000 rows) inside a transaction. When per-row rules must run (permissions, lifecycle checks), load all rows in one query, decide in memory, then write in bulk.
- **Authorization in bulk**: load the caller's permissions once per request; compute per-row permission keys from data already loaded.
- **Clients**: one list request returns everything a row renders; related labels come embedded or from one batch request (`?ids=1,2,3`), never one request per row. Query hooks live at the list level, not in row components.
- Keep the rest of the query healthy while fixing it: select only the columns used, paginate with a server maximum, and make sure filter, sort and foreign-key columns are indexed.
- Do not fix an N+1 by caching each row lookup — the cold path still makes N queries.

## 3. Proving it
A query-count test is the evidence: run the code path with 2 rows and with 20 rows and assert the count is equal (or assert an exact small number).
- Laravel: `DB::enableQueryLog()` / `assertQueryCount`; Symfony/Doctrine: the profiler's `DoctrineDataCollector` or a SQL logger middleware; Django: `assertNumQueries`; Rails: `ActiveRecord` query assertions or `bullet`; TypeORM/Prisma: a logger or `$on('query')` counter; SQLAlchemy: an `after_cursor_execute` event counter; Go: a counting driver wrapper or `sqlmock` expectations; GraphQL: count queries for a nested list query.
- Lazy-loading guards in tests turn silent N+1 into failures where the stack has them (Laravel `Model::preventLazyLoading()`, Rails `strict_loading`, Django `django-zen-queries`, Hibernate statistics).
- Clients: a test or network log showing the number of requests for a list does not grow with the number of rows.

## 4. Checks
1. No query, ORM call or repository call inside a loop, iterator callback, template loop or per-item serializer / resolver in the changed code.
2. Every relation and aggregate the response uses is loaded by eager loading, a keyed batch or a grouped query — no lazy load during iteration.
3. Bulk actions, imports and background jobs write with set-based statements (chunked, in a transaction); per-row rules are evaluated on rows loaded in one query. Only exception: a UI bulk action on ≤ 20 selected rows may call the single-row routes per row while no batch endpoint exists yet (`ai-dev-team:technical-design` → `references/record-lifecycle.md` §9).
4. Each list, detail-with-children, export and bulk code path the task adds or changes has a query-count test proving the count does not grow with the row count (2 rows vs 20 rows, or an exact number).
5. Clients make a fixed number of requests per screen: no request per row, no query hook inside a row component, no sequential await loop where a batch endpoint exists. Same single exception as check 3: a bulk action on ≤ 20 selected rows with no batch endpoint yet.
6. List queries are paginated with a server maximum, select only the needed columns, and their filter, sort and foreign-key columns are indexed (migration in the same task when the index is missing).
