# Canada Real Authority Acquisition Design 001 — Post-Run Adjudication

**Final status:** `CLOSED_EXECUTED_REAL_AUTHORITY_ACQUISITION_SURFACE_DESIGNED_CA3`

## Observation

The deterministic acquisition-design characterizer executed against only the
frozen Synthetic Authority-Act Sufficiency 001 closure.

Observed disposition:

`REAL_AUTHORITY_ACQUISITION_SURFACE_DESIGNED_CA3`

- successful synthetic specimens represented: `9`
- successful channel families characterized: `6/6`
- target fields covered: `6/6`
- external actor families: `3`
- internal governance families: `3`
- findings: `0`

## Channel-family acquisition surface

- `EXPLICIT_SOURCE_ORIGIN_DECLARATION` — `EXTERNAL` / `SOURCE_PUBLISHER_OR_CONTENT_ISSUER`; fields: `source_kind`
- `EXTERNAL_RIGHTS_AUTHORITY_DECLARATION` — `EXTERNAL` / `QUALIFIED_EXTERNAL_RIGHTS_AUTHORITY`; fields: `redistribution_status`, `rights_basis`
- `INSTITUTIONAL_ADMISSION_DECLARATION` — `INTERNAL_INSTITUTIONAL` / `AUTHORIZED_INTERNAL_MANIFEST_ADMISSION_ACTOR`; fields: `source_kind`
- `INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION` — `INTERNAL_INSTITUTIONAL` / `AUTHORIZED_INTERNAL_PROVENANCE_ADMISSION_ACTOR`; fields: `provenance_status`
- `INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION` — `INTERNAL_INSTITUTIONAL` / `AUTHORIZED_INTERNAL_RIGHTS_ADJUDICATOR`; fields: `redistribution_status`, `rights_basis`, `rights_status`
- `PUBLISHER_CANONICAL_LOCATOR_DECLARATION` — `EXTERNAL` / `SOURCE_PUBLISHER`; fields: `source_locator`

Every family requires the same six evidence categories before it can be treated
as real standing:

1. actor identity evidence;
2. authority-basis evidence independent of the OIC evaluator;
3. completed-act evidence;
4. CA-3 scope evidence;
5. target-field scope evidence;
6. act-integrity/digest binding.

## Minimum family-cover result

The exact minimum field-cover cardinality is:

`4` channel families.

There are exactly `2` tied minimum cover sets:

- cover set 1: `EXPLICIT_SOURCE_ORIGIN_DECLARATION`, `INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION`, `INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION`, `PUBLISHER_CANONICAL_LOCATOR_DECLARATION`
- cover set 2: `INSTITUTIONAL_ADMISSION_DECLARATION`, `INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION`, `INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION`, `PUBLISHER_CANONICAL_LOCATOR_DECLARATION`

This is a descriptive set-cover result only.

It does not establish that either set is:

- legally correct;
- institutionally preferred;
- lower risk;
- cheaper;
- easier to acquire;
- authorized for execution.

## External versus internal paths

The six families divide exactly into:

- `3` external-actor families;
- `3` internal-governance families.

External paths require evidence of authority outside the OIC evaluator.

Internal paths require a **pre-existing** delegation, charter, policy, or other
authority basis plus a completed act by the delegated actor.

OIC may verify those facts. It may not create the authority and then verify its
own creation as though externally established.

## What was established

This closes the design question:

**What evidence surface would be required to turn each structurally sufficient
synthetic channel family into a candidate real authority channel?**

That acquisition surface is now explicit and machine-checkable.

## What was not established

No real authority evidence was acquired.

No external actor was contacted.

No internal delegation was created.

No real authority act was created.

No authority channel was selected.

No declaration value was created.

No rights/provenance/legal conclusion was established.

`SOURCE_MANIFEST.csv` remains unauthorized.

## Replay

The deterministic design analysis was replayed once.

The replay was byte-for-byte identical to the tracked result.

No new observational evidence was consumed.

## Evidence bindings

- static implementation commit: `b8a05e3b44fcff75ea97dcb0c124539b5b8fb3ea`
- source Synthetic Sufficiency result SHA256: `0335208b2fae5d4ad7be72d258ff31132f8debf6d8806f343c0042d212546721`
- Real Authority Acquisition Design result SHA256: `52a3290276e79c49690b3e39ddff388e1f7c1cc830deabfa7e031b27c52f92d4`

## State preserved

- real authority evidence acquired: `FALSE`
- real authority established: `FALSE`
- real authority act created: `FALSE`
- external actor contacted: `FALSE`
- internal delegation created: `FALSE`
- declaration values created: `FALSE`
- authority channel selected: `FALSE`
- new real derivation rule created: `FALSE`
- Candidate 002 adopted: `FALSE`
- SOURCE_MANIFEST.csv created: `FALSE`
- SOURCE_MANIFEST population authorized: `FALSE`
- rights established: `FALSE`
- provenance established: `FALSE`
- legal clearance established: `FALSE`
- causal root cause: `NOT_ESTABLISHED`

## Next scientific seam

The structural/design work is now complete enough that the next useful step
would consume **new real-world authority evidence**.

That must be a separately preregistered acquisition work order.

Before any contact or internal governance act, that work order should choose a
bounded acquisition objective by an explicit criterion such as:

- verify whether a pre-existing external authority act already exists;
- verify whether a pre-existing internal delegation already exists;
- request a bounded external disposition from a qualified authority actor.

The selection criterion must be frozen before new evidence is acquired.

No authority path should be chosen merely because it belongs to a minimum
four-family cover set.
