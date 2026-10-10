# Worked example: a rate-limit claim that drifts

This uses a docs file you control, so you can change it and watch a claim get contradicted.

## 1. Make the docs file

In a public GitHub repo, create `docs/limits.md`:

```
# Limits

The API rate limit is 100 requests per minute.
```

Commit it. Use the **raw main URL**, not a commit URL (a commit URL never changes, so there would be nothing to challenge):

```
https://raw.githubusercontent.com/<user>/<repo>/main/docs/limits.md
```

Note: raw.githubusercontent.com can cache a file for a few minutes after an edit. Wait before hashing and challenging.

## 2. Get the SHA-256 of the file as it is now

```
python scripts/hash_url.py https://raw.githubusercontent.com/<user>/<repo>/main/docs/limits.md
```

(No local Python? Paste the script into a free Google Colab cell.)

## 3. Deploy, then call the contract

| Step | Method | Arguments |
|---|---|---|
| 1 | `create_ledger` | `demo-docs`, `raw.githubusercontent.com` |
| 2 | `register_claim` | `demo-docs`, `rate-limit`, the raw URL, the sha256, `default API rate limit`, `rate`, `<=`, `100`, `minute`, `rate,limit`, `604800` |
| 3 | `get_claim` | `demo-docs`, `rate-limit` (expect `VERIFIED`) |

Step 2 means: "the documented rate limit is at most 100 per minute", and it must stay fresh for 7 days.

## 4. Make the docs drift, then challenge

Edit `limits.md` so the sentence says `200 requests per minute`, commit, wait a few minutes, then hash it again and call:

| Step | Method | Arguments |
|---|---|---|
| 4 | `challenge` | `demo-docs`, `rate-limit`, the new sha256 |
| 5 | `get_claim` | `demo-docs`, `rate-limit` |

Expected: step 4 returns `CONTRADICTED`; step 5 shows status `CONTRADICTED`, `contradicting` with value 200 and unit minute, and the challenge in `history`.

## 5. Other outcomes worth recording

- Register a second claim (`rate-limit-b`), change the file to still say 100 with a different surrounding sentence, hash and challenge: `RECONFIRMED`.
- Challenge with a hash that does not match the live file: `INCONCLUSIVE` with reason `docs_hash_mismatch`, nothing changes.
- Try to register a claim whose number is not in the docs: the call is rejected and nothing is stored.
