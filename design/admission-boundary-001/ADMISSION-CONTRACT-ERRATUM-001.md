# ERRATUM 001 — ADMISSION-CONTRACT-v0.1

Status: OWNER-AUTHORIZED CORRECTION
Issued UTC: 2026-09-08
Authorization: CAT-ALIGN-001B / Arkadiy Miteiko / 2026-09-08

## Predecessor identity

- Path: `design/admission-boundary-001/ADMISSION-CONTRACT-v0.1.md`
- Blob: `1128bdbcc42dc47a355551fa230bab6f7420accc`
- SHA-256: `ad4c656831b679a9396b15a8a9ae32448cf63707711916e4f3a8fa5ed34e8cd2`
- Recorded in `docs/capabilities/CAPABILITY_MATRIX.json` under `source_provenance`, with
  `source_commit` `3fcdec63b7e546d9b369e0e8664d5d67be6a3b54`

**The predecessor is not modified.** It is preregistered design evidence, its bytes are
digest-pinned by the capability matrix, and `VERSIONING.md` requires that admitted artifacts are
never mutated in place but superseded. This erratum is a successor record about the predecessor,
not permission to erase or rewrite it. The predecessor's own claim ceiling,
`independent_validation_claim = FALSE`, and `NOT SELF-ADJUDICATED` marker continue to apply to it
unchanged.

## The corrected statement

The predecessor contains, in its closing paragraph on downstream stages:

> A later OCE/runtime stage may compute consequences; OAM/ZTL may constrain operational
> authority; and VEIP may record or verify execution consequences. None is designed or
> implemented here.

**As to OAM, that sentence is no longer canonical.** It attributes to OAM a constraint on
operational authority. Under the owner disposition of 2026-09-08, OAM's canonical role is
examination-side, not control-side.

The canonical statement is:

> ZTL may constrain what is logically warranted for downstream reliance.
> VEIP/runtime enforcement may constrain whether an exact action may execute.
> OAM governs examination/audit disposition and may constrain later institutional reliance on
> examined results; OAM does not authorize exact runtime execution.

## Why the distinction matters here

Constraining operational authority and constraining later institutional reliance are not the same
act, and collapsing them collapses two distinct authority planes: the causal authority that
determines whether an action may execute, and the evidentiary authority that determines what an
examiner may later rely on. OAM sits on the second. Attributing the first to it would let an
examination workflow read as a runtime control, which is precisely the kind of authority inflation
this contract's own admission boundary exists to prevent.

## Scope of this correction

This erratum corrects the OAM attribution **only**.

Unchanged and unaffected:

- every other semantic in `ADMISSION-CONTRACT-v0.1.md`, including the admission states, the
  minimum successor bundle, and the rule that only `ADMITTED` may cross into Institutional IR
  construction;
- the statement that no other admission state is a denial of the underlying proposition;
- the roles attributed in the same sentence to a later OCE/runtime stage, to ZTL, and to VEIP;
- the predecessor's claim ceiling in full;
- `docs/capabilities/CAPABILITY_MATRIX.json`, including the recorded digest of the predecessor;
- every schema, test vector, and runtime behavior in `design/admission-boundary-001/`.

Nothing here is designed or implemented in this repository. This erratum records a category
correction; it does not establish legal validity, universal authority semantics, production
readiness, runtime safety, compliance, successful IR compilation, execution authorization, or
independent validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

## Provenance

- Canonical OAM role: `veraxis-protocol/institutional-continuity`, `THESIS.md` §8a, and the
  reconciliation record `OAM-ROLE-RECONCILIATION.md` in that repository.
- Canonical public home for the OAM definition: `veraxis-protocol/Open-Audit-Mission`.
- Conflict discovery: the CAT-ALIGN-001B census, which found this sentence and the ICI README's
  "standing/examination workflow" definition in material conflict.
