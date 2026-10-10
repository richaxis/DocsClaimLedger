# Threat model

| Threat | Mitigation |
|---|---|
| Registering a claim that was never true | Registration succeeds only if validators confirm it holds against the pinned docs. |
| Prompt injection inside the docs page | The model output is never trusted. A quote that is not in the page, lacks the anchors, the number or the unit is rejected. The verdict is computed by code. A verdict field in the model answer is ignored. |
| Model picks the wrong number on the page | Anchor words must appear in the quote. Multiple values for the topic should return null. Unresolvable cases are INCONCLUSIVE. |
| Unit confusion (per minute vs per day) | Units are explicit and converted with integer arithmetic. |
| Decimal or look-alike numbers (1000 vs 100) | Whole-number matching in the quote. |
| Docs change between hashing and validation | SHA-256 commitment. A mismatch is INCONCLUSIVE and does not settle anything. |
| Pointing the ledger at an attacker's host | One host per ledger, compared exactly, https only, no port, query, fragment or credentials. |
| Oversized or binary pages | 64 KiB cap and strict UTF-8. |
| Re-rolling the model until it answers differently | One assessment per (claim, docs hash). Reopened only for a stale claim, once per freshness period. 5 minute cooldown. 32 challenges per claim. |
| A false CONTRADICTED from a bad model answer | The contradicting number must be grounded in a verbatim quote and agree across validators. Otherwise the result is INCONCLUSIVE. |
| Spam challenges | Cooldown and per-claim cap. Challenge cost is borne by the caller's transaction. |
| Owner hiding a contradicted claim | CONTRADICTED is settled and cannot be undone. Retiring does not erase history or the event log. |
| Unbounded storage | Bounded claims, challenges and history. |

Out of scope: whether the real service behaves as documented, trust in the docs publisher, JavaScript-rendered pages.
