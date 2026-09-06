"""Offline reference path. Supplied synthetic evidence is not real authority."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from oic.admission import (
    AdmissionInputBoundaryError,
    AdmissionReceipt,
    AdmissionState,
    canonical_json,
    digest_of,
    evaluate_admission_bytes,
)
from oic.candidate_extraction import propose_candidate_units
from oic.frozen_synthetic_provider import FrozenSyntheticProvider
from oic.interpretation_proposal import (
    SLOT_VOCABULARY,
    AdmittedCandidateBinding,
    ProposalInputBoundaryError,
    propose_interpretation,
)
from oic.model_provider import ModelProvider
from oic.review_docket import AgreementState, build_review_docket

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "benchmarks/demo/bounded-semantic-path"
FIXTURE_SHA256 = "a16368c4080e73705f90b91899b89c3e057faac3f9530e41490184d50405fe62"
SOURCE_SHA256 = "bf741bb6f1b1945c45daad1d73f62bb72775088673c7236a5318dfea3e88455d"


def supplied_authority(candidate: dict[str, Any], source_digest: str) -> dict[str, Any]:
    """Bind an explicitly synthetic owner-supplied evidence template, never model output."""
    vectors = json.loads(
        (ROOT / "design/admission-boundary-001/TEST-VECTORS-v0.2.json").read_bytes()
    )
    document: dict[str, Any] = copy.deepcopy(vectors["vectors"][0]["executable_input"])
    document["candidate"] = candidate
    registration = document["source_registration"]
    registration.update(source_id="SYNTHETIC-DEMO", source_digest=source_digest)
    evidence = document["authority_evidence"][0]
    evidence.update(source_id="SYNTHETIC-DEMO", source_digest=source_digest)
    evidence["admission_warrant"].update(source_id="SYNTHETIC-DEMO", source_digest=source_digest)
    evidence.pop("evidence_digest")
    evidence["evidence_digest"] = digest_of(canonical_json(evidence))
    return document


def binding_for(receipt: AdmissionReceipt, candidate: dict[str, Any]) -> AdmittedCandidateBinding:
    """Build the public interpretation binding from an evaluated receipt."""
    if receipt.candidate_projection_digest != digest_of(canonical_json(candidate)):
        raise ValueError("candidate does not match evaluated receipt")
    return AdmittedCandidateBinding(
        admission_receipt_id=receipt.admission_receipt_id,
        admission_state=receipt.admission_state.value,
        candidate_unit_id=receipt.candidate_unit_id,
        candidate_projection_digest=receipt.candidate_projection_digest,
        candidate_span=candidate["candidate_span"],
    )


def demonstrate(provider: ModelProvider, source: str) -> dict[str, Any]:
    """Exercise public seams, preserving divergence and refusing unadmitted interpretation."""
    source_digest = digest_of(source.encode("utf-8"))
    anchor = {
        "anchor_id": "synthetic-demo-anchor",
        "source_id": "SYNTHETIC-DEMO",
        "node_id": "synthetic:1",
        "content_hash": source_digest,
        "quote": source,
        "page": None,
        "bbox": None,
    }
    extractions = [
        propose_candidate_units(source_text=source, source_anchor=anchor, provider=provider)
        for _ in range(2)
    ]
    if any(
        candidate["candidate_span"] not in source
        for extraction in extractions
        for candidate in extraction.candidates
    ):
        raise ValueError("demo requires exact literal source spans")
    docket = build_review_docket(extractions)
    if docket.agreement_state is not AgreementState.DIVERGENT or len(docket.proposal_sets) != 2:
        raise ValueError("demo must preserve two divergent review records")
    candidate = extractions[0].candidates[0]
    authority = supplied_authority(candidate, source_digest)
    receipt = evaluate_admission_bytes(canonical_json(authority))
    if receipt.admission_state is not AdmissionState.ADMITTED:
        raise ValueError("synthetic positive control was not admitted")
    proposal = propose_interpretation(
        binding=binding_for(receipt, candidate), provider=provider, proposer_id="synthetic-author"
    ).proposal
    assertions = proposal["proposed_assertions"]
    if {a["slot"] for a in assertions} != set(SLOT_VOCABULARY):
        raise ValueError("demo must expose all eleven provisional slots")
    if any(a["proposed_source_quote"] not in candidate["candidate_span"] for a in assertions):
        raise ValueError("synthetic example has an ungrounded proposed quote")
    references = proposal.get("proposed_unresolved_references")
    if references != [{"reference_text": "section SYN-9", "reference_kind": "INTERNAL_PROVISION"}]:
        raise ValueError("unresolved reference was lost or resolved")
    missing = copy.deepcopy(authority)
    missing["authority_evidence"] = []
    refused = evaluate_admission_bytes(canonical_json(missing))
    try:
        propose_interpretation(
            binding=binding_for(refused, candidate),
            provider=provider,
            proposer_id="synthetic-author",
        )
    except ProposalInputBoundaryError:
        pass
    else:
        raise ValueError("missing authority allowed interpretation")
    malformed = copy.deepcopy(authority)
    del malformed["authority_evidence"][0]["evidence_digest"]
    try:
        evaluate_admission_bytes(canonical_json(malformed))
    except AdmissionInputBoundaryError:
        pass
    else:
        raise ValueError("malformed authority was accepted")
    output = {
        "scope": "SYNTHETIC_BOUNDED_REFERENCE_IMPLEMENTATION",
        "source_sha256": source_digest,
        "review": docket.to_json(),
        "selection_basis": "explicit synthetic fixture choice; not a vote or consensus",
        "admission": receipt.to_json(),
        "proposal": proposal,
        "negative_path": {
            "missing_authority_state": refused.admission_state.value,
            "interpretation": "REFUSED_BEFORE_PROVIDER",
            "malformed_authority": "REFUSED_AT_INPUT_BOUNDARY",
        },
        "ceilings": {
            "provider_qualification": "NOT_QUALIFIED",
            "canada_redistribution": "UNRESOLVED",
            "production_compilation": "UNESTABLISHED",
            "runtime_authorization": "UNESTABLISHED",
            "independent_validation": False,
        },
    }
    output["evidence_sha256"] = digest_of(canonical_json(output))
    return output


def main() -> None:
    """Print canonical JSON only, without any repository write or machine-specific field."""
    source = (FIXTURES / "SOURCE.txt").read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError("synthetic source digest mismatch")
    provider = FrozenSyntheticProvider(
        FIXTURES / "PROVIDER-OUTPUT.json", expected_sha256=FIXTURE_SHA256
    )
    output = demonstrate(provider, source.decode("utf-8"))
    if provider.consumed != 3:
        raise ValueError("unexpected synthetic replay count")
    sys.stdout.buffer.write(canonical_json(output))


if __name__ == "__main__":
    main()
