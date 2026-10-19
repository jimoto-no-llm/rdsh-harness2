---
name: js-ttl-lru-repair
description: Repair TTL/LRU Map caches in JavaScript — falsy hits, inclusive expiry, prune-on-every-op, and LRU touch without extending TTL on read.
---

# js-ttl-lru-repair

## When to use

Task asks to fix `createCache` / TTL / LRU in ES modules with an injected `now()` clock.

## Spec → code checklist

| Requirement | Common bug | Fix |
|-------------|------------|-----|
| Expire when `now() >= deadline` | `timestamp > deadline` | Use `>=` in `isExpired` |
| `get` returns stored falsy values | `!entry?.value` | Return `entry.value` after confirming `entries.has(key)` / entry exists post-prune |
| Hit updates recency, read does not extend TTL | No delete+reinsert on get | After read hit, `delete(key)` then `set(key, entry)` same `{value, deadline}` |
| Update live key must not evict another | Evict whenever `size >= capacity` | If key already present, update only; evict LRU only when inserting a **new** key at capacity |
| `has` vs miss for `undefined` | Same as get falsy bug | After prune, use `entries.has(key)`; do not use truthiness on `value` |
| `size()` live count only | Raw `entries.size` | Call the same prune helper first |
| Invalid `capacity` / `ttl` | Silent accept | Throw `RangeError` per task text |

## Map LRU mechanics

JavaScript `Map` iterates keys in insertion order. Least recently used is the first key unless hits reorder via delete+set.

## Verify

Run the task test command until exit code 0. Re-read any failing assertion and walk the corresponding method with the checklist above.
