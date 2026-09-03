# Canada Source-Origin Declaration Evidence Reanalysis 001

**Work order:** `OIC-CANADA-SOURCE-ORIGIN-DECLARATION-EVIDENCE-REANALYSIS-001`

**Status:** `PREREGISTERED_REANALYSIS_NOT_EXECUTED`

## Starting point

The publisher canonical-locator acquisition is formally closed
`NOT_ESTABLISHED`.

Its one-shot is permanently consumed and will not be rerun.

That run nevertheless acquired one real, SHA-256-bound publisher response for
CA-3. The raw response is preserved under `.local`.

## Why secondary analysis comes before another fetch

The next external family under the frozen research-efficiency ordering is:

`EXPLICIT_SOURCE_ORIGIN_DECLARATION`

Target field:

`source_kind`

Its synthetic construction required three independent fact levers:

- `source_origin_decl`
- `source_origin_identity`
- `source_origin_basis`

The remaining external-rights family requires four.

Rather than acquire new bytes, this study asks a new preregistered question
against the already-frozen publisher response.

## Frozen source_kind semantics

The Source Manifest Contract allows only:

- `public`
- `synthetic`

Normalization is `NONE`.

The reanalysis therefore tests both values and preselects neither.

## Admissible evidence

Only an explicit publisher/content-issuer declaration keyed specifically as
`source_kind`, `source-kind`, or `sourceKind` is eligible.

The declaration value must be literally `public` or `synthetic` after only
outer-whitespace trimming and case-folding.

Accepted surfaces are narrowly preregistered:

1. explicit HTTP `Source-Kind` / `X-Source-Kind` header;
2. explicit markup element;
3. explicit markup attribute;
4. explicit HTML meta field;
5. exact `source_kind: public|synthetic`-style label/value statement.

## Non-inference boundary

The following do **not** establish `source_kind=public`:

- government hosting;
- `.xml`;
- XML serialization;
- HTTP Content-Type;
- successful retrieval;
- public accessibility;
- final URL;
- publisher identity alone;
- document title;
- `Regulation` root element;
- words such as official, law, statute, government, or Canada.

There is no mapping from `official` to `public` and no mapping from
government-hosted to `public`.

## Cardinality

- zero admissible declarations → `NOT_ESTABLISHED`
- exactly one → evaluate six standing requirements
- multiple, duplicate, or conflicting declarations → fail closed

## No new evidence acquisition

This study performs no publisher network request.

The prior response bytes are hash-bound now but their semantics remain unread
until an independently verified static reanalysis instrument is frozen.

Because no new observational evidence is consumed, this reanalysis is
deterministically replayable and does not require a new one-shot lock.

## Claim ceiling

Even an `ESTABLISHED` result would establish only the externally declared
`source_kind` value for CA-3 under this bounded authority contract.

It would not authorize `SOURCE_MANIFEST.csv` population and would establish
nothing about source_locator, rights, provenance, redistribution, legal
clearance, full manifest admissibility, causal root cause, or other sources.
