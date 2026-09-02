# Canada Evidence-to-Manifest Crosswalk 001 — Post-Run Adjudication

**Final status:** `CLOSED_EXECUTED_CROSSWALK_INCOMPLETE_FAIL_CLOSED`

## Observation

The frozen crosswalk executed exactly once against the preserved Inventory 001
receipt.

Observed disposition:

`CROSSWALK_INCOMPLETE_FAIL_CLOSED`

Exactly four of twelve manifest fields were established:

- `source_id` — `ESTABLISHED_DIRECT`
- `local_path` — `ESTABLISHED_DIRECT`
- `content_hash` — `ESTABLISHED_DETERMINISTIC_DERIVATION`
- `acquired_or_generated_at` — `ESTABLISHED_DIRECT`

Eight fields were not established:

- `source_kind` — `MULTIPLE_CANDIDATES_NOT_ESTABLISHED`
- `source_locator` — `CONTRADICTORY_NOT_ESTABLISHED`
- `rights_basis` — `MULTIPLE_CANDIDATES_NOT_ESTABLISHED`
- `rights_evidence` — `CONTRADICTORY_NOT_ESTABLISHED`
- `rights_status` — `MULTIPLE_CANDIDATES_NOT_ESTABLISHED`
- `provenance_evidence` — `CONTRADICTORY_NOT_ESTABLISHED`
- `provenance_status` — `MULTIPLE_CANDIDATES_NOT_ESTABLISHED`
- `redistribution_status` — `MULTIPLE_CANDIDATES_NOT_ESTABLISHED`

Aggregate state counts:

- `ESTABLISHED_DIRECT`: 3
- `ESTABLISHED_DETERMINISTIC_DERIVATION`: 1
- `MULTIPLE_CANDIDATES_NOT_ESTABLISHED`: 5
- `CONTRADICTORY_NOT_ESTABLISHED`: 3

## Adjudication

The preregistered success rule requires all twelve fields to be established.

That condition was not met.

Therefore the final disposition is:

`CROSSWALK_INCOMPLETE_FAIL_CLOSED`

No discretionary precedence, candidate-key expansion, silent enum translation,
or semantic promotion is permitted after observation.

## What this establishes

It establishes that the frozen Crosswalk 001 contract can deterministically map
four target fields from the preserved Inventory 001 representation.

It also establishes that the same frozen contract does not establish the
remaining eight target fields.

## What this does not establish

It does **not** establish that the underlying evidence is absent.

It does **not** establish that the underlying rights or provenance position is
invalid.

It does **not** establish that any conflicting candidate is factually wrong.

It does **not** establish a complete manifest mapping.

It does **not** authorize weakening the frozen crosswalk rules.

The causal root cause of the unresolved evidence/manifest mismatch remains:

`NOT_ESTABLISHED`

## One-shot state

- execution count consumed: `1/1`
- rerun authorized: `FALSE`
- tracked crosswalk created: `FALSE`
- SOURCE_MANIFEST.csv creation authorized: `FALSE`
- SOURCE_MANIFEST.csv population authorized: `FALSE`
- rights established: `FALSE`
- provenance established: `FALSE`

## Inspection boundaries preserved

- real evidence reread: `FALSE`
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

No successor evidence-schema resolution or normalization work is automatically
authorized.

## Evidence bindings

- authorization receipt SHA256: `ee604084689f99ab6f0173ab84877be5b667b1ad2036c21262a13ef11c080bbb`
- one-shot lock SHA256: `608a1a0abf217ba8ef78e9bbdae5d9dd01cf902bc9dcfd58c6ee81e663fd9428`
- crosswalk receipt SHA256: `77d8a67a71e7eb073fa3f43825a1113a53effd948f69e7abee952e06767dbb92`
- stderr log SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- implementation freeze SHA256: `737d2e1096ae257b5ec74401d875da9d2d14b4aad8a9b7b09239cce20a9b9e53`
- instrument SHA256: `8116d22aa26b953eb0b355e2fb028c2bfa5e7d429d399b39818c956bc7c13d5b`
- crosswalk contract SHA256: `f4517e2a927784a6e231da788eaf128a3394cad7e399d5473bb42c54ba352df3`

## Next step

Independently verify this formal closure.

Do not rerun Crosswalk 001.

Do not create `SOURCE_MANIFEST.csv`.

After closure verification, a separately preregistered evidence-schema
resolution study may be considered.
