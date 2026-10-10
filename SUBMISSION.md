# Submission

**Category:** Intelligent Contracts

**Title:** DocsClaimLedger: challengeable, validator-checked claims about documentation

**Description:**

DocsClaimLedger is a ledger of machine-checkable documentation claims, such as "the API rate limit is at most 100 requests per minute", pinned to a docs URL. A claim is structured data: a kind (count, duration or rate), a comparator, a whole number and a unit. Registration only succeeds if validators confirm the claim holds against the pinned docs. Anyone can then challenge it by committing to the hash of the live page. The leader and every validator fetch the page themselves. The model may only return one number, one unit and a verbatim quote, and the contract rejects it unless the quote is in the page and contains the claim's anchor words, the number and the unit. Code, never the model, decides HOLDS or CONTRADICTED with unit-aware integer arithmetic. Validators must agree exactly on the observed value. Contradicted claims stay settled with the evidence. Reusable by any team that publishes docs.

**Repository:** _add your GitHub link_

**Deployed on Studio Next:** _add contract address and explorer link_

**Evidence:** `README.md`, `docs/CONSENSUS.md`, `docs/THREAT_MODEL.md`, `tests/`, `LIVE_PROOFS.md`
