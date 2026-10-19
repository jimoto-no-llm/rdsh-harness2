---
name: js-cache-repair
description: Diagnose and fix TTL/LRU createCache implementations against spec and public tests, including expiry boundaries, falsy stored values, and LRU eviction rules.
---

## When to use

Task asks to repair a dependency-free ES module cache with capacity, TTL, injected `now`, and operations `set` / `get` / `has` / `size`.

## Read first

1. Task text for validation rules (`RangeError` for capacity and ttl), prune-before-every-op, and "reading does not extend deadline".
2. `src/expiry.mjs` and `src/cache.mjs`.
3. Public tests — they are the visible acceptance contract.

## Workspace facts (this ttl-lru-cache fixture)

- Public test **deadline itself is expired** sets `ttl: 5`, inserts at `time = 0`, then sets `time = 5` and expects `has('a') === false`. Expiry at the deadline counts as expired: `isExpired` must be true when `timestamp >= entry.deadline`, not only when `timestamp > entry.deadline`. The broken starter used strict `>`.
- Task requires storing any JavaScript value including **false, 0, null, and undefined**. A `get` that returns `undefined` when `!entry?.value` or when the value is falsy conflates misses with legitimate stored values; branch on whether an entry exists after prune, then return `entry.value`.
- **Updating a live key must not evict another key**; eviction runs only when inserting a new key while at capacity. Evict the **least recently used** live entry, not unconditionally the first Map key on every `set`.
- **All operations** (including `size`) remove expired entries first. `get`/`has` hits must update recency without extending TTL.

## Repair order (procedure)

1. Fix `isExpired` boundary (`>=` deadline) and re-run tests — one public test depends only on this.
2. Ensure every method calls shared prune using injected `now()` before other logic.
3. Fix `set`: refresh deadline on write; promote to most-rerecently-used; skip capacity eviction when the key already exists after prune.
4. Fix `get`: return stored value including falsy; promote LRU without changing deadline.
5. Fix `has`: presence after prune only; no recency change.
6. Add spec validation for capacity (positive integer) and ttl (finite, nonnegative) if missing.
7. Run **harness2_test**; investigate failures against the spec bullets above.

## LRU with `Map`

JavaScript `Map` orders keys by insertion. To mark a key most recently used, re-insert it (e.g. delete and set with the same entry payload) on successful `get` and on `set` update.
