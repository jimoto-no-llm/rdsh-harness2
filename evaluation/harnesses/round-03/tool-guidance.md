## Skills for this domain

- **js-ttl-lru-cache-repair** — Analyze starter cache/expiry against the task brief and visible tests; apply the known starter defects and LRU/TTL checklist before running tests.

## Procedure

1. Read allowed sources and `test/public.test.mjs` before writing code.
2. Diff mental model against the task spec: expiry rule, falsy stored values, LRU recency, capacity eviction on insert vs update, prune-before-op, and injected `now()`.
3. Fix `expiry.mjs` boundary first (`>=`), then `cache.mjs` (shared `prune()` on every method, falsy-safe `get`, `has` without touch, `set` with update-vs-insert eviction rules, MRU on `get`/`set`).
4. Limit edits to files the task allows.
5. Run tests; if one fails, map the assertion to a single bug, then re-run (do not scatter speculative fixes).

## TTL/LRU checks

- Reconcile expiry with **now() >= deadline** against `isExpired` — off-by-one at the deadline is a frequent miss.
- `get` must not treat stored `false`, `0`, `null`, or `undefined` as a miss; only a missing key is a miss.
- `has` distinguishes stored `undefined` from absent keys and must not promote recency.
- JavaScript `Map` LRU: insertion order is recency; **promote** by `delete(key)` then `set(key, entry)` on hits and updates.
- On `set`, evict least-recently-used **only when adding a new key** at capacity; updating an existing live key must not evict a different key.
- `size()` counts live entries only — prune expired entries first, same as other operations.
