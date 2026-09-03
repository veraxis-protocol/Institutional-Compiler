# Canada External Rights Disposition Acquisition 001

**Work order:** `OIC-CANADA-EXTERNAL-RIGHTS-DISPOSITION-ACQUISITION-001`

**Status:** `PREREGISTERED_EXTERNAL_CONTACT_NOT_AUTHORIZED`

## Why this path is next

The three structurally sufficient external families were:

1. publisher canonical-locator declaration;
2. explicit source-origin declaration;
3. external rights-authority declaration.

The first two are now closed `NOT_ESTABLISHED` under their bounded evidence
contracts.

The remaining external family is therefore:

`EXTERNAL_RIGHTS_AUTHORITY_DECLARATION`

This is a research-sequence fact, not a legal preference.

## Required actor

The frozen design requires:

`QUALIFIED_EXTERNAL_RIGHTS_AUTHORITY`

Qualification cannot be asserted by OIC.

Before any disposition can count, independent evidence must establish the
actor's relevant professional or institutional authority.

Examples of potentially qualifying classes are frozen in the acquisition
contract, but no actor is selected during preregistration.

## Two-field disposition

The family structurally covers:

- `rights_basis`
- `redistribution_status`

The acquisition requests one completed written act covering both fields.

This minimizes external contact without merging unrelated authority domains.

## Frozen values

### rights_basis

- `public_domain`
- `open_license`
- `permission`
- `synthetic_owned`
- `other_documented_basis`

### redistribution_status

- `permitted`
- `not_permitted`
- `unknown`

Normalization is `NONE`.

No answer is preselected.

`unknown` remains an admissible external disposition even though it does not
satisfy the manifest's eventual pass condition.

## Required real-authority evidence

A qualifying disposition must contain or be accompanied by:

1. explicit actor identity;
2. independently established qualification/authority basis;
3. completed attributable written act;
4. explicit CA-3 scope;
5. explicit `rights_basis` scope;
6. explicit `redistribution_status` scope;
7. SHA-256 or equivalent durable integrity binding.

A pending request is not a disposition.

A scheduling message is not a disposition.

An OIC-generated legal analysis is not external authority.

## What success would and would not do

A successful acquisition could establish externally declared values for
`rights_basis` and `redistribution_status`.

It would **not** establish `rights_status`.

It would not establish source_kind, source_locator, provenance, general legal
clearance, full manifest admissibility, causal root cause, or generality.

It would not authorize automatic `SOURCE_MANIFEST.csv` population.

## Current authorization boundary

This preregistration does not authorize:

- selecting an external actor;
- contacting an actor;
- sending the request;
- ingesting a response as authority;
- creating declaration values;
- creating or populating `SOURCE_MANIFEST.csv`.

## Next step after independent verification

Statically freeze:

- actor qualification evidence schema/checker;
- bounded outbound request packet generator;
- received-disposition schema;
- authority/admissibility evaluator;
- synthetic positive/negative/conflict fixtures.

Only after that static freeze is independently verified may a separate explicit
authorization permit external contact.
