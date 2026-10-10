# Consensus design

## What every validator re-derives

`register_claim` and `challenge` run one function inside `gl.eq_principle.strict_eq`. That function:

1. fetches the docs page (status and raw bytes),
2. checks status 200, the 64 KiB cap, SHA-256 against the caller's commitment and UTF-8,
3. requires every anchor word to appear on the page, otherwise stops without calling the model,
4. asks the model for one whole number, one unit and one verbatim quote,
5. validates the answer in code,
6. computes HOLDS or CONTRADICTED by integer arithmetic,
7. returns the report as canonical JSON.

## What must match, and what does not

The compared report contains the docs hash, the claim parameters, the observed value and unit, the verdict and a reason code. The quote is validated by each validator but is not part of the compared report. Two validators may legitimately quote different sentences that state the same number, and that should not break agreement. Their observed value and unit must still be identical.

If any validator cannot ground its own answer, its report says UNKNOWN with a reason code and differs from a leader that did ground it. The transaction then fails and nothing is stored. The contract never turns disagreement into a verdict.

## Grounding rules (`validate_extraction`)

- The value is a whole number, written as digits, commas allowed, no decimals, up to 10^12.
- The unit must match the claim kind: empty for count, one of second, minute, hour, day for duration and rate.
- The quote is 8 to 300 characters and must occur in the page (whitespace collapsed).
- The quote must contain every anchor word, the number as a whole number (so 1000 does not satisfy 100 and 100.5 is rejected) and a word for the unit.
- The model is told to return null if the page states several different values (for example per plan), and the claim is then INCONCLUSIVE.

## Why not `prompt_comparative`

A comparative principle asks a model whether two answers are "close enough". Here the output is a number that decides a public status, so the contract compares an exact, code-validated report instead.

## Known limits

Anchor words and a quote make a wrong-sentence pick unlikely, not impossible. A page that states the number in a table or image is not supported. Only raw-text sources are supported. Shared model mistakes remain possible.
