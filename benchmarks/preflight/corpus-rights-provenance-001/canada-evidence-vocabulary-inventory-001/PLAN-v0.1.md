# Canada Evidence Vocabulary Inventory 001

**Work order:** `OIC-CANADA-EVIDENCE-VOCABULARY-INVENTORY-001`

**Status:** `PREREGISTERED_NOT_EXECUTED`

## Rationale

Canada Corpus Evidence Reconciliation 001 closed
`EVIDENCE_INSUFFICIENT_FAIL_CLOSED` because the frozen exact-key/no-alias
algorithm resolved only two of twelve required manifest fields.

That result did **not** establish:

- absence of underlying rights evidence;
- absence of provenance evidence;
- a vocabulary mismatch;
- a causal explanation for the mismatch.

Therefore a crosswalk is not yet authorized.

The next bounded question is descriptive:

> What vocabulary and structural key paths actually exist in the already frozen
> machine-readable evidence surface?

## Scope

Population remains exactly:

- `CA-3`

Future inventory execution may inspect only the **primary machine-readable**
artifacts already frozen in the existing evidence allowlist.

It may not inspect:

- corroborating Markdown;
- `CA-3.xml`;
- unlisted files;
- network resources.

## Frozen inventory method

For every allowlisted primary JSON artifact, traverse the complete parsed JSON
tree in deterministic document order and record:

- artifact path;
- frozen Git blob identity;
- JSON pointer;
- exact object key;
- value type;
- array length where applicable;
- scalar representation under the frozen capture rule.

Scalar strings of at most 256 characters may be recorded exactly.

Longer strings must be represented only by SHA-256 and UTF-8 byte length.

No key normalization.

No synonym generation.

No alias generation.

No semantic interpretation.

No mapping to `SOURCE_MANIFEST.csv`.

No legal or rights conclusion.

## Decision rule

`INVENTORY_COMPLETE` only if every frozen primary machine-readable evidence
artifact matches its frozen identity, parses successfully under the frozen
duplicate-key policy, and is exhaustively inventoried.

Otherwise:

`INVENTORY_INCOMPLETE_FAIL_CLOSED`

## Scientific boundary

This inventory is descriptive, not inferential.

Even a complete inventory does not establish that any observed key corresponds
to any manifest field.

A future crosswalk would require its own separately justified and preregistered
work order **after** this inventory is closed and independently verified.

## Current authorization state

- closed reconciliation rerun: **FALSE**
- evidence contents inspected by this preregistration: **FALSE**
- source XML access: **FALSE**
- SOURCE_MANIFEST.csv creation: **FALSE**
- crosswalk creation: **FALSE**
- rights/provenance established: **FALSE**
- provider/model/network calls: **ZERO**
- 007R1 / Q011 / canonicalization / IR / OCE / Rego / runtime: **FALSE**
