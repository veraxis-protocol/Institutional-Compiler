# Interpretation Proposal Characterization 001 — post-run audit

Status: **AMEND — INTERPRETATION PROPOSAL ARCHITECTURE RETAINED; CURRENT
MODEL/PROMPT SEMANTICS NOT FREEZE-READY**

This is a measurement-layer successor to Characterization 001. It does not replace or
alter the live receipt. The source receipt was read only after its SHA-256 matched
`29217e29207f7a1a5e32ae28bc7ae28cd9d33cc7acc591a9fb4aa0f38d59b7f5`; the exact
instrument commit is `213ef5988f16f13cbf0b2e691b1873a740034a82` and the exact corpus
SHA-256 is `462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817`.

The frozen run made 87 planned and attempted requests. It produced 86 accepted proposals,
one provider error, and no boundary rejection. All 323 non-null source quotes were
literally grounded; none was ungrounded. These are observations over one synthetic run,
not population error rates.

## Corrected interpretation

Historical Metric F reported six `alternatives_preserved` observations. Those bytes remain
unchanged in the historical metric snapshot, but all six are reclassified here as
`ALTERNATIVES_CONJOINED_OR_COLLAPSED`: each IIR-017 run returned one bearer string joining
the department and contractor, and each IIR-018 run returned one action string joining
notify and file. No run surfaced the alternatives as separate assertions.

The source-text/semantic-role taxonomy is deliberately separate. `UNGROUNDED_SOURCE_TEXT`
means the quote is absent from the admitted span. `UNSUPPORTED_SEMANTIC_ASSIGNMENT` means
grounded words were assigned where the gold role was unavailable or the asserted meaning
was unsupported. `WRONG_ROLE_ASSIGNMENT` means grounded material belonging to another
canonical role was put in the asserted role. `SUPPORTED_ROLE_ASSIGNMENT` means the grounded
assignment is compatible with that role. The live audit found 0, 36, 21, and 266
respectively across 323 value-bearing, non-null quoted assertions. Thus the run showed no
text hallucination while still showing semantic invention and role error.

The successor strengthening audit distinguishes disappearance from relocation. It records:

- six `THRESHOLD_BROADENED_BY_COMPARATOR_LOSS` instances (IIR-012 and IIR-031, all runs);
- six condition omissions and one condition moved to another role;
- four exceptions moved to condition rather than disappearing;
- one temporal omission and nine temporal qualifiers moved to condition; and
- three recipient-to-bearer promotions.

The established-slot headline remains 365 expected observations: 260 compatible, 83
omitted, and 22 incompatible. All nine expected references were surfaced; four had the
correct kind and five the wrong kind, with no omission, invention, or semantic resolution.

Repeat stability is reported over 29 specimens. Six had exact semantic-hash stability, 27
had force stability, and 12 had slot-set stability. Per-slot counts are in `AUDIT.json`.
IIR-032 had two provider-successful runs; all other specimens had three. Deterministic OIC
binding is provenance stability and is not reported as model-semantic stability.

## Disposition and boundary

The proposal boundary worked, source quoting was completely grounded in this run, force
discrimination outside constitutive definitions was strong, and advisory/permission force
strengthening was absent. Semantic-role assignment, material placement, constitutive
definitions, ambiguity handling, and repeat stability are not freeze-ready. No
canonicalization runtime is authorized by this audit.

This audit does not establish semantic correctness, canonical institutional meaning,
model authority, production readiness, cross-model generalization, successful
canonicalization, Institutional IR runtime, legal interpretation, or independent
validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO NEW MODEL CALL WAS MADE.**
**NO CANONICALIZATION WAS IMPLEMENTED.**
**NO INSTITUTIONAL IR RUNTIME WAS IMPLEMENTED.**
