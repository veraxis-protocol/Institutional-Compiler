# OIC Owner Decision 004 — Bounded Semantic Code Start and NVIDIA NIM Provider

**Date:** 2026-08-29
**Owner:** Arkadiy Miteiko / Veraxis
**Status:** OWNER-AUTHORIZED — BOUNDED SEMANTIC IMPLEMENTATION
**Open Run experimental execution:** NOT AUTHORIZED

## Decision

Arkadiy Miteiko authorizes bounded OIC semantic implementation to proceed before Open
Run experimental testing, subject to the conditions below. This decision does not
convert repository readiness into a release claim and does not authorize Open Run
Library experiments.

## Pre-start condition

Before adding new semantic production paths, the exact repository head MUST run the
existing code-start prerequisite verifier and preserve its literal result. The verifier
result is a prerequisite receipt, not owner acceptance of semantic correctness.

## Authorized implementation scope

1. Introduce a provider-neutral model interface for candidate-generation assistance.
2. Add NVIDIA NIM as the first replaceable provider implementation.
3. Permit model-assisted candidate normative extraction only as candidate material.
4. Deterministically impose candidate identity, source anchor,
   `interpretation_state=extracted`, and `epistemic_state=uncertain` outside the model.
5. Reject model attempts to emit authority-controlled fields.
6. Add deterministic review-docket construction that exposes candidate
   agreement/divergence without voting, selecting, or admitting meaning.
7. Add engineering unit/contract tests required to validate implementation mechanics.
8. Continue the bounded source-to-control vertical slice only under separate reviewed
   work orders.

## Provider boundary

NVIDIA NIM is a replaceable implementation dependency at the candidate/proposal layer
only. A model provider may propose, extract, compare, or challenge candidate meaning.
It must not establish source authority or institutional admission, alter admitted
meaning, create authority, generate runtime authorization, decide its own conformance,
bypass deterministic validation, or invent or control OIC source anchors.

## Explicitly not authorized

- Open Run Library experimental execution;
- automatic institutional admission or model confidence as admission;
- model-authored source authority;
- Institutional IR or Open Control Envelope semantics not separately specified;
- live consequential runtime ALLOW/DENY execution;
- production, enterprise, compliance, superiority, certification, or independent
  validation claims; or
- changing frozen ZTL or VEIP semantics through the provider layer.

## Engineering tests vs Open Run experiments

Unit, contract, type, lint, build, connectivity, and CI checks are engineering
validation only and must not be represented as Open Run Library experimental evidence.

## Review state

`independent_validation_claim = FALSE`

The implementation remains producer output until separately validated.
