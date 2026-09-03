# Canada Publisher Canonical-Locator Evidence Acquisition 001

**Work order:** `OIC-CANADA-PUBLISHER-CANONICAL-LOCATOR-EVIDENCE-ACQUISITION-001`

**Status:** `PREREGISTERED_ACQUISITION_NOT_EXECUTED`

## Why this is the first real-evidence pilot

Real Authority Acquisition Design 001 produced six structurally sufficient
channel families.

This pilot does not choose a legal or institutional winner.

It applies a frozen research-efficiency criterion to the external families:

1. no internal delegation required;
2. no actor contact required for the discovery attempt;
3. real authority is not already established;
4. smallest synthetic changed-lever count;
5. lexical family ID only if tied.

That selects:

`PUBLISHER_CANONICAL_LOCATOR_DECLARATION`

for:

`source_locator`

The synthetic study required one changed fact lever:
`publisher_locator_decl`.

Publisher identity was already present in the frozen baseline.

## Research question

Does a **pre-existing publisher-issued canonical-locator declaration** already
exist in public official evidence for CA-3?

The pilot will not ask the publisher to create one.

## Evidence boundary

The future execution may inspect only two explicit declaration forms:

- HTTP `Link: ...; rel="canonical"`;
- HTML `<link rel="canonical" href="...">`.

The following are explicitly insufficient:

- acquisition URL;
- final URL;
- successful retrieval;
- redirects;
- publisher identity;
- page title;
- navigation links;
- sitemap membership;
- third-party sources;
- search-engine canonicalization;
- JSON-LD `@id`;
- OpenGraph URL.

## Navigation seed

The frozen Canada acquisition index is hash-bound only.

Its semantics are **not read during preregistration**.

After a static acquisition instrument is independently verified, it may read
only the CA-3 source ID, target URL, and final URL as network-navigation seed
metadata.

Those fields remain non-authoritative.

## Future network boundary

The later acquisition run will be one-shot because it consumes new real-world
evidence.

Before any request it must create a permanent STARTED lock.

Allowed:

- HTTPS;
- HEAD / GET;
- bounded response size;
- bounded redirects inside the seed registrable-domain boundary.

Forbidden:

- credentials;
- forms;
- actor contact;
- email/messages;
- JavaScript execution;
- cross-domain evidence hunting;
- provider/model calls.

## Possible outcomes

### ESTABLISHED

A unique preregistered canonical relation is emitted by the publisher-controlled
response and all six standing-evidence requirements pass.

### NOT ESTABLISHED

The bounded acquisition completes cleanly but no admissible canonical
declaration is found.

### INCOMPLETE

The run cannot make the bounded determination because of conflict, drift,
network failure, domain escape, malformed evidence, or another frozen gate.

## Claim ceiling

Even an ESTABLISHED result would establish only the external publisher
canonical-locator authority act for CA-3/source_locator.

It would **not**:

- populate a declaration value;
- authorize SOURCE_MANIFEST population;
- establish source_kind;
- establish rights or provenance;
- establish legal clearance;
- establish full manifest admissibility;
- generalize beyond CA-3.

## Current state

- execution performed: `FALSE`
- new real-world evidence acquired: `FALSE`
- network request made: `FALSE`
- external actor contacted: `FALSE`
- real authority established: `FALSE`
- declaration values created: `FALSE`
- SOURCE_MANIFEST.csv created/populated: `FALSE`

## Next authorized activity after independent verification

Implement and statically freeze the bounded navigation-seed reader,
domain-bound network acquisition instrument, raw-response evidence capture, and
canonical-declaration parser using synthetic/local fixtures only.

Do not make any real network request until that implementation is independently
verified.
