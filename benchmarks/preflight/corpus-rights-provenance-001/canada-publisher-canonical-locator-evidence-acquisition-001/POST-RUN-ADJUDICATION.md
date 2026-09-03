# Canada Publisher Canonical-Locator Evidence Acquisition 001 — Post-Run Adjudication

**Final status:** `CLOSED_EXECUTED_PUBLISHER_CANONICAL_LOCATOR_AUTHORITY_EVIDENCE_NOT_ESTABLISHED_CA3`

## Terminal outcome

`PUBLISHER_CANONICAL_LOCATOR_AUTHORITY_EVIDENCE_NOT_ESTABLISHED_CA3`

The one-shot is permanently consumed.

- rerun authorized: `FALSE`
- publisher network request made: `TRUE`
- real response records received: `1`
- new real-world evidence acquired: `TRUE`
- external actor contacted by email/message/form: `FALSE`

## What was actually observed

The frozen CA-3 navigation projection resolved to:

- `source_id`: `CA-3`
- `target_url`: `None`
- `final_url`: `https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml`

One real publisher response was received and preserved with SHA-256-bound raw
headers/body/evaluation evidence.

The preregistered acquisition accepted only:

1. HTTP `Link` with `rel=canonical`; or
2. HTML `<link rel=canonical>`.

The observed response produced:

- admissible canonical declarations: `0`
- acquisition findings: `0`

Therefore the frozen success rule did not pass.

## Standing-requirement result

- CA-3 scope evidence: `TRUE`
- act integrity/digest binding: `TRUE`
- actor identity evidence from an admissible canonical act: `FALSE`
- external authority-basis evidence: `FALSE`
- completed canonical declaration act: `FALSE`
- target-field canonical declaration scope: `FALSE`

The last four requirements remain unestablished because no admissible canonical
declaration act was observed.

## Critical non-inference boundary

The real final URL:

`https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml`

is **navigation metadata, not a source_locator declaration value**.

The following remain non-admissible as canonical authority evidence:

- the final URL itself;
- successful retrieval;
- redirect destination;
- publisher identity alone;
- XML content or document identity;
- reviewer judgment.

OIC must not convert any of those facts into `source_locator`.

## What this result establishes

Only this:

**The bounded public publisher evidence acquisition did not find either
preregistered canonical-declaration form for CA-3/source_locator.**

## What this result does not establish

It does not establish:

- that no canonical-locator authority act exists elsewhere;
- a source_locator declaration value;
- real authority for source_locator;
- source_kind;
- rights or provenance;
- redistribution permission;
- legal clearance;
- SOURCE_MANIFEST admissibility;
- causal root cause;
- cross-source generality.

## Evidence binding

Tracked execution-result SHA256:

`f796371b8ec92ad491d0f5bd2b8163e25974fbc1fc80cd117c427407d639a775`

Local one-shot evidence remains preserved under `.local` and must not be
deleted or modified.

## Scientific interpretation

This is a genuine negative real-evidence result, not an execution failure.

The synthetic work showed that a publisher canonical-locator declaration would
be structurally sufficient if present. The real bounded acquisition then tested
whether that declaration already existed in the two frozen public forms and
found none.

That narrows the uncertainty surface:

- structural recognizability: `SUPPORTED`;
- bounded public publisher canonical declaration: `NOT_ESTABLISHED`;
- real source_locator authority: `NOT_ESTABLISHED`.

## Next seam

Do not rerun this acquisition.

A successor work order may examine another preregistered real-authority path,
but it must use a new acquisition objective and new evidence contract. The
absence of a canonical declaration here is not permission to substitute the
final URL or engineer a declaration value.
