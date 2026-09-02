# Canada Crosswalk Failure-Surface Characterization 001 — Post-Run Adjudication

**Final status:** `CLOSED_EXECUTED_FAILURE_SURFACE_CHARACTERIZED`

## Observation

The frozen descriptive characterization executed exactly once against the
preserved Crosswalk 001 receipt.

Observed disposition:

`FAILURE_SURFACE_CHARACTERIZED`

All eight unresolved fields reproduced their frozen Crosswalk 001 state/counts.

- profiles: `8/8`
- findings: `0`

## Established surface partition

Five fields are:

`ZERO_ADMISSIBLE_VALUE_SURFACE`

- `source_kind`
- `rights_basis`
- `rights_status`
- `provenance_status`
- `redistribution_status`

These fields had candidate vocabulary in Crosswalk 001, but zero target values
survived its frozen admissibility and nonpromotion rules.

Three fields are:

`MULTI_ADMISSIBLE_CONTRADICTION_SURFACE`

- `source_locator`
- `rights_evidence`
- `provenance_evidence`

These fields had multiple distinct admissible target values survive Crosswalk
001, with no precedence rule authorized.

## Per-field descriptive surface

- `source_kind`: 18 candidates; 3 support records; 2 keys; 2 artifacts; 1 exact raw-value fingerprint; 0 mapped values.
- `source_locator`: 144 candidates; 9 support records; 4 keys; 3 artifacts; 4 exact raw-value fingerprints; 4 mapped values.
- `rights_basis`: 66 candidates; 4 support records; 4 keys; 1 artifact; 4 exact raw-value fingerprints; 0 mapped values.
- `rights_evidence`: 118 candidates; 4 support records; 3 keys; 1 artifact; 4 exact raw-value fingerprints; 4 mapped values.
- `rights_status`: 37 candidates; 4 support records; 3 keys; 3 artifacts; 2 exact raw-value fingerprints; 0 mapped values.
- `provenance_evidence`: 39 candidates; 5 support records; 3 keys; 3 artifacts; 3 exact raw-value fingerprints; 3 mapped values.
- `provenance_status`: 107 candidates; 3 support records; 2 keys; 1 artifact; 3 exact raw-value fingerprints; 0 mapped values.
- `redistribution_status`: 44 candidates; 2 support records; 2 keys; 1 artifact; 2 exact raw-value fingerprints; 0 mapped values.

The tracked execution result preserves the exact frequency/fingerprint profiles.

## What this establishes

It establishes a descriptive distinction that Crosswalk 001 itself did not
express:

1. five fields failed because no admissible target value survived;
2. three fields failed because multiple admissible target values survived.

This distinction is now frozen observational evidence.

## What this does not establish

It does **not** establish causal root cause.

It does **not** establish which candidate is institutionally correct.

It does **not** establish a valid precedence relation.

It does **not** establish a valid normalization.

It does **not** establish that the schema or evidence should be modified.

It does **not** establish rights, provenance truth, legal clearance, or evidence
sufficiency.

The causal root cause remains:

`NOT_ESTABLISHED`

## One-shot state

- execution count consumed: `1/1`
- rerun authorized: `FALSE`
- winner selection performed: `FALSE`
- precedence assignment performed: `FALSE`
- normalization performed: `FALSE`
- schema mutation performed: `FALSE`
- SOURCE_MANIFEST.csv creation/population authorized: `FALSE`

## Inspection boundaries preserved

- real evidence reread: `FALSE`
- Inventory 001 receipt inspected: `FALSE`
- source XML inspected: `FALSE`
- corroborating Markdown inspected: `FALSE`
- network used: `FALSE`

## Downstream authorization

- Ontology 007R1: `FALSE`
- Q011: `FALSE`
- canonicalization: `FALSE`
- Institutional IR: `FALSE`
- OCE: `FALSE`
- Rego: `FALSE`
- runtime: `FALSE`

No successor normalization, precedence, or schema-resolution work is
automatically authorized.

## Evidence bindings

- authorization receipt SHA256: `fd5c44937d07596c18175ce707ccba95e4bf5e9c2d45e097f3fcd4675b03a38a`
- one-shot lock SHA256: `8fb29ff59f0f2b899593e6d0c78b751033e58a1c2d1bd939ee7a1464e0cd1f38`
- characterization receipt SHA256: `18c7297a769b28c56e755c31e533653de3d38e6675e41a4ccf9ba99eaa38ef47`
- stderr log SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- implementation freeze SHA256: `cbeb55b2d670f1d8a81490cc153fb66e3ec367e6209e22e219639be0f6448c00`
- instrument SHA256: `d22eac0a272dc014b427022c0f8c0fe46cc6a108fbceae79ef3d5c4dc815013d`
- characterization contract SHA256: `b84cdc8d59e189188898903392e45b2e38d8bcb3486d01c5f567ec0e3b46e26c`

## Next step

Independently verify this formal closure.

Do not rerun Failure-Surface Characterization 001.

Do not create `SOURCE_MANIFEST.csv`.

After closure verification, any successor resolution-hypothesis study should be
separately preregistered and preserve the observed distinction between
zero-admissible and contradiction surfaces.
