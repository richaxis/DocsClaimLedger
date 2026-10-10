# DocsClaimLedger

A reusable GenLayer ledger of machine-checkable documentation claims. A project registers a claim such as "the API rate limit is at most 100 requests per minute", pinned to one docs URL. Anyone can later challenge it with the hash of the docs as they look now. Validators fetch the page themselves and settle the claim as HOLDS, CONTRADICTED or UNKNOWN.

## Problem and why GenLayer

Documentation drifts. A limit, a timeout or a page size changes, the docs are edited, and the claim a project made last quarter is quietly false. Nobody can prove that without trusting one person's reading of a web page. DocsClaimLedger turns that into a public record where the check is done by independent validators, and where a false claim stays on the ledger as CONTRADICTED with the number that contradicted it.

```
register_claim: docs URL + sha256 + a structured claim
   kind: count | duration | rate     comparator: == | <= | >=
   expected integer + unit           anchor words (1 to 3)
        |
        v   leader and every validator fetch the page and check status, size, sha256, UTF-8
   model reads the page and returns ONE number, ONE unit, ONE verbatim quote
   contract rejects it unless the quote is in the page, holds every anchor word,
   the number and the unit
        |
        v   comparison is integer arithmetic in code (no floats, units converted)
   registration succeeds only if the claim HOLDS against the pinned docs
        |
challenge: anyone, with the sha256 of the docs right now
        |
        v   same fetch + grounding + arithmetic, exact match on the observed value
   RECONFIRMED (fresh again)  |  CONTRADICTED (settled, evidence kept)  |  INCONCLUSIVE (nothing changes)
```

## What is different from a thin LLM wrapper

- A claim is structured data, not a sentence. The verdict is computed by code from a number and a unit, never chosen by the model.
- The model can only quote the page. An answer is rejected unless the quote exists in the fetched text, contains the claim's anchor words, the number and the unit.
- Unit mistakes are caught by arithmetic: "100 per day" and "100 per minute" are different rates and are compared as such.
- A model answer that cannot be grounded is INCONCLUSIVE, never a verdict, so a bad answer can neither confirm nor kill a claim.
- Validators must agree exactly on the observed value, unit and verdict, otherwise nothing is stored.

## Claim states

```
registered (baseline must HOLD) -> VERIFIED
VERIFIED -> challenge HOLDS        -> VERIFIED (freshness reset, reconfirmed + 1)
VERIFIED -> challenge CONTRADICTED -> CONTRADICTED (settled, contradicting value stored)
VERIFIED -> challenge unclear      -> VERIFIED (INCONCLUSIVE recorded in history)
VERIFIED or CONTRADICTED -> owner retires -> RETIRED
```

`get_claim` returns `fresh_until` (last verification time plus the claim's max age, 1 to 365 days). After that time the claim should be treated as stale until a later challenge reconfirms it. Reconfirming unchanged docs is allowed only once the claim is stale. Otherwise the same docs hash cannot be assessed twice, so a result cannot be re-rolled.

Bounds: 64 claims per ledger, 32 challenges per claim, 5 minutes between challenges on one claim, 16 history entries kept per claim (the full log is in the event list), 64 KiB docs, https URLs on the ledger's exact host only.

## API

| Method | Who | What it does |
|---|---|---|
| `create_ledger(ledger_id, docs_host)` | anyone | Pins the one host the ledger may read. Caller is the owner. |
| `register_claim(ledger_id, claim_id, docs_url, docs_sha256, topic, kind, comparator, expected, expected_unit, anchors, max_age_seconds)` | owner | Registers a claim after validators confirm it holds. |
| `challenge(ledger_id, claim_id, docs_sha256)` | anyone | Re-checks the live docs. Returns RECONFIRMED, CONTRADICTED or INCONCLUSIVE. |
| `retire_claim(ledger_id, claim_id)` | owner | Retires a claim. |
| `get_ledger`, `get_claim`, `event_count`, `get_event` | view | Auditable state. |

Units: for `duration`, `expected_unit` is second, minute, hour or day. For `rate`, it is the period (100 requests per minute is expected 100, unit minute). For `count`, it is the empty string. `anchors` is a comma list such as `rate,limit`.

Docs sources: the page is read as raw text, so use sources that are plain text, Markdown, or JSON/YAML (for example raw.githubusercontent.com files). Pages that only render in a browser with JavaScript are not supported.

## Repository layout

```
contracts/DocsClaimLedger.py    the Intelligent Contract
docs/                           architecture, consensus design, threat model
scripts/hash_url.py             prints the sha256 commitment for a URL body
scripts/check_contract.py       static header / structure checks
tests/unit/                     arithmetic, grounding and report logic
tests/direct/                   lifecycle tests against a fake runtime
examples/DEMO.md                a worked example you can reproduce
LIVE_PROOFS.md                  Studio Next receipts (fill in after real runs)
SUBMISSION.md                   title, short description, evidence links
```

## Validate

```
python -m pip install -r requirements-dev.txt
python scripts/check_contract.py
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/direct -v
```

The tests mock web, model and clock calls, and use a small fake GenLayer runtime (`tests/fake_genlayer.py`). They do **not** simulate validator agreement. Real consensus evidence belongs in `LIVE_PROOFS.md`.

## Deploy on Studio Next

- Network: Studio Next, RPC `https://studio-next.genlayer.com/api`, chain ID `61997`
- Explorer: https://explorer-studio-dev.genlayer.com/
- Migration notes: https://docs.genlayer.com/developers/consensus-v06-migration#test-on-studio-dev-first

Deploy `contracts/DocsClaimLedger.py` with no constructor arguments, then follow `examples/DEMO.md`.

## Known assumptions to confirm on the live network

The contract relies on `gl.nondet.web.get(url)` returning `.status` and raw `.body`, on `gl.message_raw["datetime"]` for the transaction time, and on `hashlib` and `urllib.parse` being available in GenVM. These are the first places to check if a call fails after deploy.

This is an experimental test-network release and has not been independently audited.
