# TTL/LRU cache repair (this workspace)

Fix only `src/cache.mjs` and `src/expiry.mjs`. Keep `createCache` export and the dependency-free ES module layout. Before editing, read the task brief, every listed source file, and `test/public.test.mjs`. Ground each change in a spec clause or a failing test assertion. After edits, run the project test command and treat a non-zero exit code as blocking.

## Spec anchors (task brief)

- Expiry: an entry is dead when `now() >= entry.deadline` (equality counts). `ttl=0` means immediate expiry after set.
- Every public method prunes expired entries first. Reads do **not** extend deadlines.
- `get`: miss → `undefined`; a hit promotes the key to most recently used. Must return stored **falsy** values when present.
- `has`: true iff a live entry exists; must **not** change LRU order.
- `set`: refresh deadline to `now()+ttl`, promote to MRU; inserting a **new** key at capacity evicts the LRU live key; updating an **existing** live key must not evict a different key.
- `size`: count live entries only (prune first).
- Invalid `capacity` or `ttl` throw `RangeError` per task brief.

## Workspace facts (starter source + visible tests)

- Starter `get` uses `if (!entry?.value) return undefined`, which mis-handles falsy stored values even though the task allows them.
- Starter `isExpired` uses `timestamp > entry.deadline`; test **"deadline itself is expired"** sets `time = 5` after `set('a', 1)` with `ttl: 5` and requires `has('a') === false` at the deadline instant.
- Starter `set` evicts `entries.keys().next().value` whenever `size >= capacity` before write, without skipping eviction for an in-place update of an existing live key.
- Starter does not promote keys on `get`; visible test **"stores values and evicts oldest inserted key"** uses insert-only sequence at capacity 2.
- Visible tests do not exercise falsy storage, `get`-hit LRU, or update-without-evict; the task brief still requires them when aligning to spec.

When stuck on LRU representation, use the **js-ttl-lru-cache-repair** skill.
