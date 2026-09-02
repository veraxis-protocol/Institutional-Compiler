# Canada Evidence-Bundle Materialization 001 — Post-Run Adjudication

**Final status:** `CLOSED_EXECUTED_EVIDENCE_BUNDLES_MATERIALIZED_CA3`

## Observation

The frozen one-shot materializer executed exactly once against the preserved
Crosswalk 001 receipt.

Observed disposition:

`EVIDENCE_BUNDLES_MATERIALIZED_CA3`

- findings: `0`
- bundle candidates: `2/2`
- rights-evidence references preserved: `4/4`
- provenance-evidence references preserved: `3/3`

## Formal materialization

Formal closure copied the exact observed local bundle bytes into the frozen
tracked destinations.

### rights_evidence

- tracked path: `benchmarks/preflight/corpus-rights-provenance-001/evidence-bundles/CA-3/rights_evidence-bundle-v0.1.json`
- SHA256: `3460f97cfd179ac8a57c52059115fc15e62f0e591526ab7043c1add12aafb85b`
- distinct exact references: `4`

### provenance_evidence

- tracked path: `benchmarks/preflight/corpus-rights-provenance-001/evidence-bundles/CA-3/provenance_evidence-bundle-v0.1.json`
- SHA256: `25e2ab8a6f192c9247fa6dcd6e6eac27a63b720b8e5bc904ec9339e8adcced74`
- distinct exact references: `3`

No transformation occurred during closure.

## What is established

For CA-3 only:

1. the two evidence-reference bundles have been deterministically materialized;
2. each tracked bundle is byte-identical to the corresponding observed one-shot
   local candidate;
3. rights_evidence preserves all four exact mapped references;
4. provenance_evidence preserves all three exact mapped references;
5. no evidence-reference precedence was assigned;
6. no legal-sufficiency status was promoted.

## What is not established

This is representation infrastructure, not authority adjudication.

The following remain **not established**:

- rights;
- provenance truth;
- legal clearance;
- evidentiary priority;
- legal sufficiency;
- any of the six declaration-field values;
- Candidate 002 adoption;
- SOURCE_MANIFEST admissibility;
- cross-source generality;
- causal root cause.

The causal root cause remains:

`NOT_ESTABLISHED`

## Six declaration fields remain untouched

- `source_kind`
- `source_locator`
- `rights_basis`
- `rights_status`
- `provenance_status`
- `redistribution_status`

No value was inferred, created, or admitted for any of them.

## Inspection boundary

During the one-shot, the preserved Crosswalk receipt was inspected.

During formal closure, it was **not reopened**; closure used only:

- the preserved local materialization receipt;
- the STARTED lock and authorization receipt;
- the exact local candidate bundle bytes;
- frozen tracked control hashes.

Real underlying evidence was not reread.

## One-shot state

- execution count consumed: `1/1`
- rerun authorized: `FALSE`
- tracked bundle files created at closure: `TRUE`
- tracked bundle count: `2`
- declaration fields touched: `ZERO`
- Candidate 002 adopted: `FALSE`
- SOURCE_MANIFEST.csv created: `FALSE`

## Evidence bindings

- authorization receipt SHA256: `8bb1d31805443810e42e60ce2765eb97481cd5c57fd391a09be3f2aac3573ca1`
- STARTED lock SHA256: `e2a80ae059bfcfcf124d871f53f2a1953a8be018060b2149f60459e232961667`
- local materialization receipt SHA256: `b7eb57fe7b406d4ca5c47b3a75365d40ab4e059f29c4323588d2a5e61bc0f806`
- stderr log SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- source Crosswalk receipt SHA256: `77d8a67a71e7eb073fa3f43825a1113a53effd948f69e7abee952e06767dbb92`
- implementation freeze SHA256: `0ae04fdeba83204ee70bff26cf6b0d09e5ed47416b327147b6586dca192fc580`
- instrument SHA256: `7550b3599c0f1e46fd12259ed795c8efeedf3e67399fda1d9fc22c89baab6651`
- materialization contract SHA256: `72c387ba7d46d235432ce5fb8e41debd303c952064d808ae66c7521715a2aa07`

## Downstream authorization

- declaration-field admission: `FALSE`
- Candidate 002 adoption: `FALSE`
- SOURCE_MANIFEST population: `FALSE`
- Ontology 007R1: `FALSE`
- Q011: `FALSE`
- canonicalization: `FALSE`
- Institutional IR: `FALSE`
- OCE: `FALSE`
- Rego: `FALSE`
- runtime: `FALSE`

## Next step

Independently verify this formal closure.

Do not rerun Bundle Materialization 001.

The next scientific seam is the six declaration fields: who or what has
standing to establish each value. That requires a separately preregistered
authority/admission study before any SOURCE_MANIFEST row can be created.
