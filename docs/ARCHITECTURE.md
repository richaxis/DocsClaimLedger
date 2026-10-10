# Architecture

## State

| Field | Type | Meaning |
|---|---|---|
| `ledgers` | `TreeMap[str, str]` | JSON per ledger: owner, the one allowed docs host, claim ids |
| `claims` | `TreeMap[str, str]` | JSON per claim, keyed `ledger:claim`: structured claim, status, times, assessed hashes, bounded history |
| `events` | `TreeMap[str, str]` | Append-only log (`LEDGER_CREATED`, `CLAIM_REGISTERED`, `CHALLENGE_*`, `CLAIM_RETIRED`) |
| `event_total` | `u256` | Event counter |

Records are canonical JSON strings (`sort_keys=True`) so every node serializes identically.

## The claim is data

`kind` (count, duration, rate), `comparator` (==, <=, >=), `expected` (whole number), `expected_unit`, and 1 to 3 `anchors`. The comparison is cross-multiplied integer arithmetic (`satisfies`), so no division and no floats are involved, and units are converted exactly (second, minute, hour, day).

## Why the pure helpers live in the same file

GenVM loads one contract file. Arithmetic, grounding checks and report building are plain module-level functions with no `gl` calls, so the tests import them directly and a reviewer can read the whole decision path in one place.

## Lifecycle

1. `register_claim` runs the consensus block against the owner's baseline hash. It stores the claim only if the verdict is HOLDS, so the ledger never contains a claim that was false on day one.
2. `challenge` runs the same block against the challenger's hash of the live page.
3. The outcome updates status, freshness and a bounded history. INCONCLUSIVE changes nothing except the history and the cooldown clock.
4. Views never read the clock. `get_claim` returns `fresh_until` and the caller compares it with the time.

## What is not here

No funds, bonds or rewards, no external calls, no proof that the real service matches the docs.
