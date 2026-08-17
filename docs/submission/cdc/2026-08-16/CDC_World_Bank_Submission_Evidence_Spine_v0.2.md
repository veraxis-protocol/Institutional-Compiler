# CDC / World Bank Submission Evidence Spine v0.2

**Date:** 2026-08-16  
**Purpose:** Control what the submission may claim, what exact evidence supports each claim, and what remains unproven after RUN-003 owner claim freeze.

> **Controlling doctrine:** Evaluation establishes the property; issuance creates the reliance. Currentness, authority, propagation, and reliance are separate properties and transitions.

> **Owner freeze:** `CDC_RUN003_OWNER_CLAIM_FREEZE_001`, SHA-256 `79ae91418bdcbd4076a8e1dec28094a459cd3492293c831f28c62784d50be1f0`.

## 1. Evidence & Claim Matrix

| # | Continuity layer / evaluator question | Current status | Evidence / observation | Claim permitted now | Boundary / not established |
|---|---|---|---|---|---|
| 1 | **Frozen governed inputs.** Can the mission operate against identified, immutable inputs rather than an unbounded prompt/context? | SUPPORTING EVIDENCE | Mission package and Stage-1/Stage-2 artifacts were frozen and hash-addressed; historical evidence archives remain preserved. | The bounded demonstration used frozen, identity-bound mission inputs and preserved execution evidence. | Does not establish source-fidelity or semantic-conservation correctness for arbitrary CDC documents. |
| 2 | **Candidate formation / Stage-1.** Can bounded candidate state be carried forward with provenance? | SUPPORTING / NOT STANDALONE CLAIM | Stage-1 state is preserved and consumed by later bounded stages rather than silently recomputed. | A frozen candidate/evidence state can be preserved and consumed by a later bounded stage. | Do not infer general policy-to-meaning correctness or institutional meaning preservation. |
| 3 | **Human disposition / transition evaluation.** Is human judgment separate from machine observation? | HISTORICAL EVIDENCE + NEGATIVE FINDING | Original Mission-001 remains FAIL: M11 = SEMANTIC_VIOLATION; M12 = INCOMPLETE_OBSERVATION. Human-disposition records remain separately bound. | Human dispositions were represented as separately bound inputs in the synthetic mission execution. | Disposition is not official CDC issuance or reliance. Mission-001 history is immutable. |
| 4 | **Correction successor construction.** Can correction create a successor without mutating the predecessor? | FUNCTIONAL EVIDENCE OBTAINED | Successor `EBAWU-P-001-C-TENDER-01-CORR-002` was constructed once under single-use authority; predecessor preserved; five outputs identified as affected. | Bounded correction-successor construction and successor-side impact determination were functionally observed. | Does not itself create institutional propagation or official reliance. |
| 5 | **Historical preservation across correction.** Can historical records remain valid history while present eligibility changes? | MEASURED INTERNAL TECHNICAL DEMONSTRATION | Currentness Slice preserved five historical output digests. RUN-003 T-CASE-L additionally preserved an issued historical reliance record byte-for-byte while a later attempt was refused after correction. | `HISTORICAL_ARTIFACT_PRESERVATION_DURING_CURRENTNESS_CHANGE` and `HISTORICAL_RELIANCE_RECORD_PRESERVATION` = `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION`. | Historical preservation is not current eligibility and does not mean historical records announce their own obsolescence. |
| 6 | **Currentness resolution.** Can present-use eligibility be recomputed independently of immutable history? | MEASURED INTERNAL TECHNICAL DEMONSTRATION | Currentness Slice: 44/44 internal technical criteria; five real outputs SUPERSEDED/R2 and denied; adversarial and digest evidence preserved. | `EXECUTABLE_CURRENTNESS_RESOLUTION = MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION`. | Positive CURRENT path was synthetic; real unaffected CDC output CURRENT remains not established. |
| 7 | **Stale present-use refusal.** Does supersession prevent present use? | MEASURED INTERNAL TECHNICAL DEMONSTRATION | Five real outputs resolved SUPERSEDED/R2 and were refused before authority evaluation. | `STALE_OUTPUT_PRESENT_USE_REFUSAL = MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION`. | Only invoking paths are measured; bypass resistance is not established. |
| 8 | **Fail-closed currentness under adversarial conditions.** | MEASURED INTERNAL TECHNICAL DEMONSTRATION | Frozen adversarial currentness universe refused unsupported, ambiguous, stale, forged, mis-bound and caller-supplied currency assertions; UNKNOWN remained DENY. | Bounded fail-closed currentness behavior may be claimed within the frozen universe. | Internal conformance to self-designed semantics, not independent assurance. |
| 9 | **Currentness → authority/admissibility.** Does CURRENT merely permit a separate authority evaluation? | **MEASURED INTERNAL TECHNICAL DEMONSTRATION** | RUN-003 evidence commit `53a62648…`; adjudication transport `5dda5f2d…`; five real stale outputs terminated before authority; synthetic CURRENT subject entered a distinct authority/admissibility procedure. | `CURRENTNESS_TO_AUTHORITY_INTEGRATION = MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION`. | Authority content is synthetic. Real CDC authority and full authority-procedure branch coverage are not established. |
| 10 | **Governed propagation.** Can governed state cross a serialized boundary to a separate consumer? | **PARTIALLY SUPPORTED INTERNAL TECHNICAL DEMONSTRATION** | T-POS-03 materialized the envelope; T-POS-04 established distinct OS processes and path-only consumer input; T-POS-05 revalidated content. T-POS-04 lacked full consumer run/trace identity and persisted-envelope file binding. | RUN-003 observed one serialized process boundary and consumer validation of propagated content. | `GOVERNED_STATE_PROPAGATION_TO_RELIANCE_BOUNDARY` is only partially supported; complete consumer-side execution binding, external bypass resistance, distributed and cross-institution propagation are not established. |
| 11 | **Reliance-time revalidation.** Are currentness and authority re-established at the moment of reliance? | **MEASURED INTERNAL TECHNICAL DEMONSTRATION** | T-CASE-K: CURRENT→SUPERSEDED, epoch moved, reliance refused I2. T-CASE-P: artifact remained CURRENT and decision fresh, authority basis revoked, reliance-time authority denied A10, reliance refused I11. | `POST_EVALUATION_CORRECTION_PREVENTS_STALE_RELIANCE` and `POST_EVALUATION_AUTHORITY_REVOCATION_PREVENTS_RELIANCE` = `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION`. | Synthetic bounded workflow only; no real CDC institutional reliance. |
| 12 | **Reliance issuance.** Is reliance a distinct issued transition? | **MEASURED INTERNAL TECHNICAL DEMONSTRATION** | T-POS-06 observed I1/ISSUED; authorization→attempt→reliance digest bindings reproduce. The null `attempt_state` in the projected observation is cured by the exact frozen bound attempt artifact. | `RELIANCE_ISSUANCE_GATED_BY_CURRENTNESS_AND_AUTHORITY = MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION`. | Synthetic bounded reliance only. Official CDC issuance, legal effect and production reliance remain not established. |
| 13 | **Institutional propagation.** Does changed state automatically reach every downstream consumer? | NOT ESTABLISHED | RUN-003 measures one process boundary on one machine only. | None beyond the bounded process-boundary observation in row 10. | `institutional_currentness_propagation`, `distributed_reliance_consistency`, `cross_institution_propagation` = NOT_ESTABLISHED. |
| 14 | **Institutional reliance / officiality.** Has a real institution officially issued, adopted or relied on generated output? | NOT ESTABLISHED / OUTSIDE DEMONSTRATION CEILING | Positive authority and reliance objects are explicitly synthetic; technical adjudication is internal and non-independent. | None. | Real CDC authority/reliance, official issuance, CDC acceptance, legal effect and production conformance remain NOT_ESTABLISHED. |

## 2. Evaluator-facing scenario: correction without rewriting history

### Demonstrated now

1. A bounded mission operates against frozen, hash-addressed inputs and preserves raw execution evidence.
2. Human dispositions remain separately represented. The original Mission-001 failure is preserved rather than sanitized.
3. A separately authorized correction creates a successor without mutating the predecessor.
4. Historical artifacts remain byte-identical while present-use eligibility changes.
5. Currentness is recomputed separately from history; stale real outputs are refused before authority evaluation.
6. A synthetic CURRENT subject enters a separate authority/admissibility procedure; currentness does not create authority.
7. A durable envelope is materialized and crosses to a distinct OS consumer process using paths rather than producer in-memory state. The full projected consumer-side identity binding is incomplete and remains disclosed.
8. At reliance time, currentness is re-resolved and authority/admissibility is re-evaluated independently.
9. If a correction becomes operative after evaluation, stale reliance is refused (`I2`).
10. If authority is revoked while the artifact remains CURRENT and the propagated decision remains fresh, reliance is refused (`I11`).
11. A bounded synthetic reliance record is issued only after the contemporaneous gating chain; the authorization→attempt→reliance digest chain reproduces.
12. A later correction does not rewrite the earlier issued reliance record; new reliance eligibility is evaluated separately.

### Still explicitly not claimed

- real CDC institutional authority or institutional reliance;
- official CDC issuance or official-record formation;
- production enforcement or legal effect;
- external consumer bypass resistance;
- distributed reliance consistency;
- cross-institution propagation;
- full authority-procedure branch coverage;
- independently validated assurance.

## 3. Submission architecture figure

```text
[FROZEN GOVERNED INPUTS]                         SUPPORTING
          |
          v
[CANDIDATE / HUMAN DISPOSITION / STAGE-2]        HISTORICAL; ORIGINAL FAIL PRESERVED
          |
          v
[CORRECTION SUCCESSOR]                           FUNCTIONAL
          |
          +---------------------> [HISTORICAL RECORD PRESERVED]   MEASURED
          |
          v
[CURRENTNESS RESOLVER]                           MEASURED INTERNAL TECHNICAL DEMO
          |
          v
[PRESENT-USE GATE]                               MEASURED
   stale / unknown / ineligible -> DENY
   CURRENT
          |
          v
[AUTHORITY / ADMISSIBILITY]                      MEASURED INTERNAL TECHNICAL DEMO
          |
          v
[DURABLE PROPAGATION ENVELOPE]                   PARTIALLY SUPPORTED
          |
          v
[SEPARATE CONSUMER PROCESS]
   re-resolve currentness + re-evaluate authority MEASURED
          |
          v
[RELIANCE ISSUANCE / REFUSAL]                    MEASURED INTERNAL TECHNICAL DEMO

REAL CDC AUTHORITY / OFFICIAL ISSUANCE / INSTITUTIONAL RELIANCE /
DISTRIBUTED OR CROSS-INSTITUTION PROPAGATION      NOT ESTABLISHED
```

## 4. Submission authoring rules

1. Never convert an internal technical demonstration into an independent-validation claim.
2. Never shorten `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` to bare `MEASURED` when the assurance qualifier matters.
3. Never rewrite Mission-001 or RUN-001/RUN-002 history.
4. Never infer currentness from immutability.
5. Never infer authority from currentness, propagation from authority, or reliance from propagation.
6. Never describe the partial T-POS-04 result as full governed-propagation evidence closure.
7. Never convert synthetic authority/reliance mechanics into real CDC authority/reliance.
8. Never claim full authority-procedure branch coverage.
9. Gate refusal does not establish external bypass resistance.
10. Official CDC authority, issuance, acceptance, legal effect, production conformance, distributed consistency and cross-institution propagation remain outside the present claim ceiling.
11. Measured CDC productivity uplift remains prohibited until B0/B3 human-time comparison with blind quality review is executed.

## 5. Evidence anchors

- Currentness evidence: commit `77652fd25991c83c4690b7e888e24d77a0887d86`.
- Currentness internal technical adjudication: commit `0c9410395ef8f1f1de1b75a36f6fdc991ef884a1`; artifact SHA-256 `c8b682c7505354907a602a74a6c312c3d420c53877ec59c6ad3386c6980def01`.
- Integration RUN-003 issuance SHA-256: `8384217cf97d3c6a836685c9c278c216f0d25238ab345fd12565a9383f0f387c`.
- Integration RUN-003 evidence commit/tree: `53a62648c51be9745785252a2e76b950817e907a` / `42beb7f790e4a84a9e381b111dbf238bc0f77838`.
- RUN-003 raw package SHA-256: `3b3db405b613e81844a8bab47559efa8c74bca363b8551021e75c12bd26f8086`.
- RUN-003 criterion ledger SHA-256: `2ad338f4c7aef3ce2e1c10c1cdd83c388dc3cd676d554606f7646191f87d8368`.
- RUN-003 technical adjudication: ZTL commit `6bbc0aef9be0d845be8e7a7eeaafeab022bb07cf`; artifact SHA-256 `095a5c1f367b901e5ce3e71c3b44108c75ad0babaca7f111969e0f1dd41e2fb1`; Institutional-Compiler transport commit `5dda5f2d224079fdf102b5dd281b7999fffc0f54`.
- Owner claim freeze: `CDC_RUN003_OWNER_CLAIM_FREEZE_001`, local artifact SHA-256 `79ae91418bdcbd4076a8e1dec28094a459cd3492293c831f28c62784d50be1f0`.

## 6. Current critical path

1. Treat RUN-003 as frozen complete and Integration Slice 001 as `CLOSED_WITH_PROPAGATION_EVIDENCE_LIMITATION`.
2. Do not execute RUN-004 for the present submission claim set.
3. Apply the owner-frozen evidence deltas to the submission claim register.
4. Reconcile the submission against TDD-OAM-001 v1.1 / SAR-OAM-001 v1.0, keeping productivity, offline/no-egress and benchmark claims at their separately earned evidence classes.
5. Final submission claim audit: remove or downgrade any sentence that exceeds this spine.

---
**Control status:** Owner-reconciled submission-control artifact. It is not itself execution evidence or independent adjudication.
