---
name: js-ttl-lru-cache-repair
description: Repair TTL/LRU createCache in src/cache.mjs and isExpired in src/expiry.mjs against task spec and node:test public tests.
---

# JS TTL/LRU cache repair

## When to use

Task is to fix `createCache` TTL + LRU behavior in this repo's two source files with tests in `test/public.test.mjs`.

## Read order

1. Task brief (capacity/ttl/now validation, prune-before-op, MRU rules).
2. `test/public.test.mjs` — covers (a) capacity-2 insert eviction and (b) expiry at the deadline instant.
3. `src/expiry.mjs` then `src/cache.mjs`.

## Workspace-specific starter defects

| Location | Bug | Correct rule |
|----------|-----|----------------|
| `expiry.mjs` | `timestamp > entry.deadline` | Use `timestamp >= entry.deadline` |
| `cache.mjs` `get` | `!entry?.value` guard | Miss only when entry absent after prune; return `entry.value` including falsy |
| `cache.mjs` `set` | Always evict one slot when `size >= capacity` | If key already live after prune, update in place (no extra eviction); else evict LRU then insert |
| `cache.mjs` LRU | No touch on `get` | After successful `get`, move key to MRU (e.g. delete+set on Map) |
| `cache.mjs` `has` | (verify) | Must not reorder; only prune + membership |
| `cache.mjs` `size` | May skip prune | Prune expired before returning count |

## Implementation checklist

- [ ] Shared `prune()` using `isExpired(entry, now())` on every method.
- [ ] `set`: set deadline `now()+ttl`; promote entry to MRU.
- [ ] `get`: promote on hit; do not extend deadline.
- [ ] Capacity eviction targets least recently used **live** key only on new inserts.
- [ ] Throw `RangeError` for invalid `capacity` or `ttl` when the task brief requires it.

## Verify

Run the project test target after edits. Re-read failing assertion names against the checklist above.
