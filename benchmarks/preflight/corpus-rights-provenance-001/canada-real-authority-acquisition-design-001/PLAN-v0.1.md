# Canada Real Authority Acquisition Design 001

**Work order:** `OIC-CANADA-REAL-AUTHORITY-ACQUISITION-DESIGN-001`

**Status:** `PREREGISTERED_DESIGN_NOT_EXECUTED`

## Starting point

Synthetic Authority-Act Sufficiency 001 is formally closed.

The frozen standing discriminator recognized all `9/9` lowest-gap synthetic
authority constructions, and all independently added fact levers were
load-bearing under bounded ablation.

That closes structural recognizability.

The remaining problem is real institutional standing.

## Research question

**What real-world actor class, authority-basis evidence, completed-act
evidence, and scope evidence would be required to instantiate each
structurally sufficient channel family without OIC issuing or inventing
authority?**

## Successful channel families

### `EXPLICIT_SOURCE_ORIGIN_DECLARATION`

- actor origin: `EXTERNAL`
- required actor class: `SOURCE_PUBLISHER_OR_CONTENT_ISSUER`
- realization mode: `EXTERNAL_DECLARATION_ACT`
- structurally supported fields: `source_kind`

### `EXTERNAL_RIGHTS_AUTHORITY_DECLARATION`

- actor origin: `EXTERNAL`
- required actor class: `QUALIFIED_EXTERNAL_RIGHTS_AUTHORITY`
- realization mode: `EXTERNAL_RIGHTS_DISPOSITION_ACT`
- structurally supported fields: `redistribution_status`, `rights_basis`

### `INSTITUTIONAL_ADMISSION_DECLARATION`

- actor origin: `INTERNAL_INSTITUTIONAL`
- required actor class: `AUTHORIZED_INTERNAL_MANIFEST_ADMISSION_ACTOR`
- realization mode: `PREEXISTING_DELEGATION_PLUS_COMPLETED_INTERNAL_ACT`
- structurally supported fields: `source_kind`

### `INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION`

- actor origin: `INTERNAL_INSTITUTIONAL`
- required actor class: `AUTHORIZED_INTERNAL_PROVENANCE_ADMISSION_ACTOR`
- realization mode: `PREEXISTING_DELEGATION_PLUS_COMPLETED_INTERNAL_ACT`
- structurally supported fields: `provenance_status`

### `INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION`

- actor origin: `INTERNAL_INSTITUTIONAL`
- required actor class: `AUTHORIZED_INTERNAL_RIGHTS_ADJUDICATOR`
- realization mode: `PREEXISTING_DELEGATION_PLUS_COMPLETED_INTERNAL_ACT`
- structurally supported fields: `redistribution_status`, `rights_basis`, `rights_status`

### `PUBLISHER_CANONICAL_LOCATOR_DECLARATION`

- actor origin: `EXTERNAL`
- required actor class: `SOURCE_PUBLISHER`
- realization mode: `EXTERNAL_CANONICAL_LOCATOR_DECLARATION_ACT`
- structurally supported fields: `source_locator`

## Two real-world acquisition path classes

### External actor path

- `EXPLICIT_SOURCE_ORIGIN_DECLARATION`
- `EXTERNAL_RIGHTS_AUTHORITY_DECLARATION`
- `PUBLISHER_CANONICAL_LOCATOR_DECLARATION`

Requires an authority act whose identity and authority basis are established
outside the OIC evaluator.

### Internal governance path

- `INSTITUTIONAL_ADMISSION_DECLARATION`
- `INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION`
- `INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION`

Requires a pre-existing organizational delegation/charter/policy plus a
completed act by the delegated actor. The evaluator may verify those
artifacts but may not create the authority it then verifies.

## Minimum field-cover surface

The mechanically computed minimum is `4` channel families to cover all six fields.

There are `2` tied minimum cover set(s).

### Cover set 1

- `EXPLICIT_SOURCE_ORIGIN_DECLARATION`
- `INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION`
- `INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION`
- `PUBLISHER_CANONICAL_LOCATOR_DECLARATION`

### Cover set 2

- `INSTITUTIONAL_ADMISSION_DECLARATION`
- `INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION`
- `INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION`
- `PUBLISHER_CANONICAL_LOCATOR_DECLARATION`

This is a set-cover fact only.

It does not imply legal preference, authority, lower institutional risk, or
authorization to instantiate any family.

## Real-authority admission boundary

- actor identity must be explicit and attributable
- authority basis must be established independently of the OIC evaluator
- authority basis must cover the act class
- authority basis must cover CA-3 or an explicitly applicable source class
- completed act must explicitly cover the target manifest field or fields
- act evidence must be durably bound by digest or equivalent integrity reference
- no OIC evaluator may issue, invent, or self-authorize the authority act
- synthetic specimen output may not be promoted into real authority evidence

## What this work does not do

- contact an external authority;
- create an internal delegation or charter;
- create a real authority act;
- treat repository ownership as authority;
- create a declaration value;
- populate `SOURCE_MANIFEST.csv`.

## Next authorized activity after independent verification

Implement and statically freeze a deterministic acquisition-design
characterizer that reproduces the six family requirements, two acquisition
path classes, and all minimum field-cover sets from the frozen synthetic
closure.

Only after that design is executed and independently closed may a separate
work order authorize acquisition of new real-world authority evidence.
