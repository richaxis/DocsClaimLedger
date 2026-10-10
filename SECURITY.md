# Security

This is an experimental test-network release (Studio Next) and has not been independently audited. Do not use it to make production decisions.

- Documentation pages are untrusted data. The contract never executes or imports fetched content.
- A claim that holds in the docs does not mean the real service behaves that way. This ledger checks published text only.
- Shared model mistakes remain possible. The contract narrows this with quote grounding, anchor words and exact-match consensus on the observed value but cannot remove it. When the page states several different values for the topic, the model is told to return null, and the claim is then INCONCLUSIVE.
- Never commit a wallet key, password or token.

To report a problem, open a private security advisory on the GitHub repository, or an issue if that is unavailable.
