# Live proofs (Studio Next)

Status: **not yet filled in.** Deploy the contract, run `examples/DEMO.md`, and record the real values below. Do not copy hashes from anywhere else.

- Network: Studio Next, RPC `https://studio-next.genlayer.com/api`, chain ID `61997`
- Explorer: https://explorer-studio-dev.genlayer.com/
- Contract address: _TODO_
- Deployment transaction: _TODO_

| Scenario | Method | Transaction hash | Receipt status (leader / consensus) | Result in `get_claim` |
|---|---|---|---|---|
| Ledger created | `create_ledger` | _TODO_ | _TODO_ | n/a |
| Claim registered (baseline holds) | `register_claim` | _TODO_ | _TODO_ | VERIFIED |
| Claim with a false number rejected | `register_claim` | _TODO_ | expected ERROR | no claim stored |
| Docs drift contradicts the claim | `challenge` | _TODO_ | _TODO_ | CONTRADICTED, contradicting value stored |
| Unchanged meaning reconfirms | `challenge` | _TODO_ | _TODO_ | VERIFIED, reconfirmed 1 |
| Wrong hash is inconclusive | `challenge` | _TODO_ | _TODO_ | INCONCLUSIVE in history |
| Same docs re-submitted rejected | `challenge` | _TODO_ | expected ERROR | unchanged |

Label expected rejections as ERROR. They are not successful settlements.
