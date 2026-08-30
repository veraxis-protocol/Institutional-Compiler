#!/usr/bin/env python3
"""Build the frozen Institutional IR 001 design corpus.

Design tooling, not IR runtime. It constructs each vector's admission input, runs the
*frozen* Admission Runtime 001 evaluator over the real byte boundary to obtain a real
receipt, assembles the provisional interpretation proposal and the expected canonical IR
unit, validates everything against the design schemas, and writes the corpus and its
freeze. It computes no institutional meaning of its own: every canonical assertion here
is authored, and every one is checked to be literally supported by the admitted span.

Nothing in this script is imported by ``oic``. Re-running it must reproduce the frozen
corpus byte-for-byte; the contract suite re-derives every admission receipt independently.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jsonschema.validators import Draft202012Validator  # noqa: E402 - path prepared above
from referencing import Registry, Resource  # noqa: E402 - path prepared above
from referencing.jsonschema import DRAFT202012  # noqa: E402 - path prepared above

from oic.admission import (  # noqa: E402 - path is prepared above
    canonical_json,
    digest_of,
    evaluate_admission_bytes,
)

DESIGN = ROOT / "design/institutional-ir-001"
CORPUS_PATH = DESIGN / "TEST-VECTORS-v0.1.json"
FREEZE_PATH = DESIGN / "TEST-VECTORS-FREEZE-v0.1.json"

CORPUS_ID = "OIC-INSTITUTIONAL-IR-001-TEST-VECTORS-v0.1"
IR_SCHEMA_ID = "OIC-INSTITUTIONAL-IR-001-v0.1"
PROPOSAL_SCHEMA_ID = "OIC-INTERPRETATION-PROPOSAL-v0.1"
INTERPRETATION_RULESET_ID = "OIC-INTERPRETATION-RULESET-001"

EVALUATION_TIME = "2026-06-01T00:00:00Z"
INTERPRETATION_TIME = "2026-06-02T00:00:00Z"
EFFECTIVE_FROM = "2026-01-01T00:00:00Z"
ADOPTED_AT = "2025-12-01T00:00:00Z"
PUBLISHED_AT = "2025-12-15T00:00:00Z"
ISSUED_AT = "2025-12-20T00:00:00Z"

SLOTS = (
    "normative_force",
    "bearer",
    "action",
    "object",
    "counterparty",
    "condition",
    "exception",
    "temporal_qualifier",
    "quantum",
    "definiendum",
    "definiens",
)

FORCE_NAMES = {
    "OBL": "OBLIGATION",
    "PRO": "PROHIBITION",
    "PER": "PERMISSION",
    "DEF": "CONSTITUTIVE_DEFINITION",
    "DEL": "DELEGATION",
    "ADV": "ADVISORY",
}

BASIS = {
    "D": "DETERMINISTIC_NORMALIZATION",
    "R": "REGISTERED_INTERPRETATION_RULE",
    "W": "INSTITUTIONAL_INTERPRETATION_WARRANT",
    "N": "NONE",
}

ESTABLISHED = "ESTABLISHED"
AMBIGUOUS = "AMBIGUOUS"
NOT_ESTABLISHED = "NOT_ESTABLISHED"
NOT_APPLICABLE = "NOT_APPLICABLE"


def est(
    value: str,
    *,
    quote: str | None = None,
    basis: str = "R",
    qualifiers: tuple[tuple[str, str], ...] = (),
    normalization: tuple[str, str, str] | None = None,
) -> dict[str, Any]:
    return {
        "status": ESTABLISHED,
        "value": value,
        "quote": quote if quote is not None else value,
        "basis": basis,
        "qualifiers": list(qualifiers),
        "normalization": normalization,
    }


def amb(alternatives: tuple[str, ...]) -> dict[str, Any]:
    return {"status": AMBIGUOUS, "alternatives": list(alternatives)}


def unknown() -> dict[str, Any]:
    return {"status": NOT_ESTABLISHED}


# ---------------------------------------------------------------------------
# Vector specifications
# ---------------------------------------------------------------------------
# Only the slots the source actually supplies are written. Everything else is filled in
# from the frozen per-force applicability table, so an unwritten slot is a deliberate
# NOT_ESTABLISHED or NOT_APPLICABLE rather than an authoring oversight.

VECTORS: tuple[dict[str, Any], ...] = (
    {
        "id": "IIR-001",
        "title": "simple mandate",
        "category": "core_force",
        "threats": ["baseline_positive"],
        "text": "The Records Officer must retain each closed file for seven years.",
        "unit_type": "mandate",
        "applicability": "records",
        "force": "OBL",
        "slots": {
            "bearer": est("The Records Officer"),
            "action": est("retain"),
            "object": est("each closed file"),
            "temporal_qualifier": est(
                "for seven years",
                basis="D",
                normalization=("DURATION", "for seven years", "P7Y"),
            ),
        },
        "falsifier": (
            "A mandate whose bearer, action, object or duration is absent from canonical IR, or "
            "whose duration normalizes to a different span."
        ),
    },
    {
        "id": "IIR-002",
        "title": "prohibition",
        "category": "core_force",
        "threats": ["baseline_positive", "negation_preservation"],
        "text": "No employee may disclose client identifiers to an external party.",
        "unit_type": "prohibition",
        "applicability": "disclosure",
        "force": "PRO",
        "slots": {
            "bearer": est("No employee", qualifiers=(("NEGATION", "No"),)),
            "action": est("disclose"),
            "object": est("client identifiers"),
            "counterparty": est("an external party"),
        },
        "falsifier": (
            "The prohibition is recorded as a permission, or the negation carried by 'No employee' "
            "is dropped."
        ),
    },
    {
        "id": "IIR-003",
        "title": "permission",
        "category": "core_force",
        "threats": ["baseline_positive"],
        "text": "A department head may approve travel outside the standard schedule.",
        "unit_type": "permission",
        "applicability": "travel",
        "force": "PER",
        "slots": {
            "bearer": est("A department head"),
            "action": est("approve"),
            "object": est("travel outside the standard schedule"),
        },
        "falsifier": (
            "'may' is recorded as an obligation, or the permission acquires a duty on its bearer."
        ),
    },
    {
        "id": "IIR-004",
        "title": "advisory",
        "category": "core_force",
        "threats": ["baseline_positive", "advisory_wording"],
        "text": "Teams are encouraged to review vendor documentation before renewal.",
        "unit_type": "advisory",
        "applicability": "vendors",
        "force": "ADV",
        "slots": {
            "bearer": est("Teams"),
            "action": est("review", qualifiers=(("HEDGE", "are encouraged to"),)),
            "object": est("vendor documentation"),
            "temporal_qualifier": est("before renewal"),
        },
        "falsifier": "Advisory force is recorded as OBLIGATION, or 'are encouraged to' disappears.",
    },
    {
        "id": "IIR-005",
        "title": "constitutive definition",
        "category": "definition",
        "threats": ["baseline_positive", "definition_source_loss"],
        "text": "Closed file means a file for which no further action is pending.",
        "unit_type": "definition",
        "applicability": "records",
        "force": "DEF",
        "slots": {
            "definiendum": est("Closed file"),
            "definiens": est("a file for which no further action is pending"),
        },
        "falsifier": (
            "The definiens is replaced by an ordinary-language meaning, or the definition acquires "
            "a bearer."
        ),
    },
    {
        "id": "IIR-006",
        "title": "delegation",
        "category": "core_force",
        "threats": ["baseline_positive", "incomplete_delegation"],
        "text": "The Board delegates approval of exceptions to the Risk Committee.",
        "unit_type": "delegation",
        "applicability": "exceptions",
        "force": "DEL",
        "slots": {
            "bearer": est("The Board"),
            "action": est("delegates"),
            "object": est("approval of exceptions"),
            "counterparty": est("the Risk Committee"),
        },
        "falsifier": (
            "The delegate becomes the delegating authority, or the delegation is recorded without "
            "a counterparty."
        ),
    },
    {
        "id": "IIR-007",
        "title": "evidence duty representable without a dedicated slot",
        "category": "representability",
        "threats": ["slot_minimality"],
        "text": "The custodian must retain proof of destruction for each disposed record.",
        "unit_type": "evidence_duty",
        "applicability": "records",
        "force": "OBL",
        "slots": {
            "bearer": est("The custodian"),
            "action": est("retain"),
            "object": est("proof of destruction for each disposed record"),
        },
        "falsifier": (
            "An evidence duty needs a slot outside the frozen eleven, or is not representable as "
            "an obligation over an evidence-producing action."
        ),
    },
    {
        "id": "IIR-008",
        "title": "review duty representable without a dedicated slot",
        "category": "representability",
        "threats": ["slot_minimality", "review_becomes_approval"],
        "text": "The committee must review each granted exception every quarter.",
        "unit_type": "review_duty",
        "applicability": "exceptions",
        "force": "OBL",
        "slots": {
            "bearer": est("The committee"),
            "action": est("review"),
            "object": est("each granted exception"),
            "temporal_qualifier": est("every quarter"),
        },
        "falsifier": (
            "A review duty is recorded as an approval, or needs a slot outside the frozen eleven."
        ),
    },
    {
        "id": "IIR-009",
        "title": "temporal trigger",
        "category": "temporal",
        "threats": ["temporal_preservation", "vague_temporal_phrase"],
        "text": "Upon receipt of a complaint, the office must open a case file within two business days.",  # noqa: E501 - corpus source fragment, kept as one exact literal
        "unit_type": "temporal_trigger",
        "applicability": "complaints",
        "force": "OBL",
        "slots": {
            "bearer": est("the office"),
            "action": est("open"),
            "object": est("a case file"),
            "condition": est("Upon receipt of a complaint"),
            "temporal_qualifier": est("within two business days"),
        },
        "falsifier": (
            "The trigger is dropped, or 'business days' is normalized to calendar days without the "
            "institutional definition of a business day."
        ),
    },
    {
        "id": "IIR-010",
        "title": "explicit condition",
        "category": "condition",
        "threats": ["condition_preservation"],
        "text": "If the request exceeds the delegated limit, the manager must escalate it.",
        "unit_type": "condition",
        "applicability": "requests",
        "force": "OBL",
        "slots": {
            "bearer": est("the manager"),
            "action": est("escalate"),
            "condition": est("If the request exceeds the delegated limit"),
        },
        "falsifier": "The condition disappears and the obligation becomes unconditional.",
    },
    {
        "id": "IIR-011",
        "title": "explicit exception",
        "category": "exception",
        "threats": ["exception_preservation", "closed_world"],
        "text": "All transfers must be countersigned, except transfers between internal accounts.",
        "unit_type": "exception",
        "applicability": "transfers",
        "force": "OBL",
        "slots": {
            "action": est("countersigned"),
            "object": est("All transfers"),
            "exception": est("except transfers between internal accounts"),
        },
        "falsifier": (
            "The exception is dropped, or exception_closure becomes CLOSED_BY_WARRANT with no "
            "interpretation instrument."
        ),
    },
    {
        "id": "IIR-012",
        "title": "quantitative threshold",
        "category": "quantum",
        "threats": ["threshold_preservation"],
        "text": "Purchases above 5000 units require a second approval.",
        "unit_type": "mandate",
        "applicability": "purchases",
        "force": "OBL",
        "slots": {
            "action": est("require"),
            "object": est("a second approval"),
            "condition": est("Purchases above 5000 units"),
            "quantum": est(
                "above 5000 units",
                basis="D",
                qualifiers=(("COMPARATOR", "above"),),
                normalization=("NUMBER", "5000", "5000"),
            ),
        },
        "falsifier": "The threshold is broadened, rounded, or its comparator is lost.",
    },
    {
        "id": "IIR-013",
        "title": "currency amount",
        "category": "quantum",
        "threats": ["threshold_preservation", "currency_preservation"],
        "text": "An invoice of $10,000 or more must be approved by the controller.",
        "unit_type": "mandate",
        "applicability": "invoices",
        "force": "OBL",
        "slots": {
            "bearer": est("the controller"),
            "action": est("approved"),
            "object": est("An invoice"),
            "quantum": est(
                "$10,000 or more",
                basis="D",
                qualifiers=(("CURRENCY", "$"), ("COMPARATOR", "or more")),
                normalization=("CURRENCY", "$10,000", "USD 10000"),
            ),
        },
        "falsifier": (
            "The currency is dropped or guessed, or 'or more' silently becomes 'more than'."
        ),
    },
    {
        "id": "IIR-014",
        "title": "deadline",
        "category": "temporal",
        "threats": ["temporal_preservation"],
        "text": "The report must be filed no later than 2026-03-31T00:00:00Z.",
        "unit_type": "mandate",
        "applicability": "filings",
        "force": "OBL",
        "slots": {
            "action": est("filed"),
            "object": est("The report"),
            "temporal_qualifier": est(
                "no later than 2026-03-31T00:00:00Z",
                basis="D",
                normalization=(
                    "TIMESTAMP",
                    "2026-03-31T00:00:00Z",
                    "2026-03-31T00:00:00Z",
                ),
            ),
        },
        "falsifier": (
            "The deadline disappears from canonical IR or normalizes to a different instant."
        ),
    },
    {
        "id": "IIR-015",
        "title": "passive voice with no actor",
        "category": "unknown",
        "threats": ["invented_actor", "unknown_as_false"],
        "text": "Records shall be retained for the applicable period.",
        "unit_type": "mandate",
        "applicability": "records",
        "force": "OBL",
        "slots": {
            "action": est("retained"),
            "object": est("Records"),
            "temporal_qualifier": est("for the applicable period"),
        },
        "falsifier": "A bearer appears in canonical IR although the source names none.",
    },
    {
        "id": "IIR-016",
        "title": "recipient distinct from actor",
        "category": "role_separation",
        "threats": ["recipient_becomes_actor"],
        "text": "The vendor must submit the certificate to the compliance office.",
        "unit_type": "mandate",
        "applicability": "vendors",
        "force": "OBL",
        "slots": {
            "bearer": est("The vendor"),
            "action": est("submit"),
            "object": est("the certificate"),
            "counterparty": est("the compliance office"),
        },
        "falsifier": "The compliance office is recorded as the bearer of the duty.",
    },
    {
        "id": "IIR-017",
        "title": "ambiguous actor",
        "category": "ambiguity",
        "threats": ["ambiguity_guessed_away", "ambiguous_pronoun"],
        "text": "The department and its contractor must maintain the register; it must be updated monthly.",  # noqa: E501 - corpus source fragment, kept as one exact literal
        "unit_type": "mandate",
        "applicability": "registers",
        "force": "OBL",
        "slots": {
            "bearer": amb(("The department", "its contractor")),
            "action": est("maintain"),
            "object": est("the register"),
            "temporal_qualifier": est("monthly"),
        },
        "falsifier": (
            "One of the two candidate bearers becomes ESTABLISHED without an interpretation "
            "warrant."
        ),
    },
    {
        "id": "IIR-018",
        "title": "ambiguous condition attachment",
        "category": "ambiguity",
        "threats": ["ambiguity_guessed_away", "unclear_exception_scope"],
        "text": "The officer must notify the registrar and file the report if the amount is disputed.",  # noqa: E501 - corpus source fragment, kept as one exact literal
        "unit_type": "condition",
        "applicability": "reports",
        "force": "OBL",
        "slots": {
            "bearer": est("The officer"),
            "action": amb(("notify", "file")),
            "condition": est("if the amount is disputed"),
        },
        "falsifier": (
            "The condition is silently attached to one conjunct, or the second conjunct is dropped."
        ),
    },
    {
        "id": "IIR-019",
        "title": "material qualifier preservation",
        "category": "material",
        "threats": ["qualifier_loss", "discretion_marker"],
        "text": "The registrar may, at its sole discretion, waive the filing fee for hardship applicants.",  # noqa: E501 - corpus source fragment, kept as one exact literal
        "unit_type": "discretion",
        "applicability": "fees",
        "force": "PER",
        "slots": {
            "bearer": est("The registrar"),
            "action": est("waive", qualifiers=(("DISCRETION", "at its sole discretion"),)),
            "object": est("the filing fee"),
            "counterparty": est("hardship applicants"),
        },
        "falsifier": (
            "'at its sole discretion' disappears, or the permission becomes an obligation to waive."
        ),
    },
    {
        "id": "IIR-020",
        "title": "source-standing-independent admitted proposition",
        "category": "admission_independence",
        "threats": ["standing_leaks_into_meaning"],
        "text": "Pilot participants must record each design evaluation session.",
        "unit_type": "mandate",
        "applicability": "design-evaluation-only",
        "jurisdiction": "pilot",
        "source_standing": "DRAFT",
        "force": "OBL",
        "slots": {
            "bearer": est("Pilot participants"),
            "action": est("record"),
            "object": est("each design evaluation session"),
        },
        "falsifier": (
            "DRAFT source standing changes the semantic content or weakens the recorded force, "
            "rather than remaining an admission fact only."
        ),
    },
    {
        "id": "IIR-021",
        "title": "source version change",
        "category": "identity",
        "threats": ["version_collapse"],
        "text": "The officer must publish the schedule each January.",
        "unit_type": "mandate",
        "applicability": "schedules",
        "force": "OBL",
        "slots": {
            "bearer": est("The officer"),
            "action": est("publish"),
            "object": est("the schedule"),
            "temporal_qualifier": est("each January"),
        },
        "second_unit": {"kind": "version", "source_version": "v5"},
        "falsifier": (
            "Two versions of the same source produce one IR unit identity, or their semantic "
            "equivalence stops being observable."
        ),
    },
    {
        "id": "IIR-022",
        "title": "supersession lineage without mutation",
        "category": "temporal_identity",
        "threats": ["silent_mutation"],
        "text": "Emergency access must be logged within one hour.",
        "unit_type": "mandate",
        "applicability": "emergency-access",
        "force": "OBL",
        "slots": {
            "action": est("logged"),
            "object": est("Emergency access"),
            "temporal_qualifier": est("within one hour"),
        },
        "second_unit": {"kind": "supersession", "source_version": "v2"},
        "falsifier": (
            "A predecessor IR unit is mutated when later evidence arrives, instead of a successor "
            "unit being created that names it."
        ),
    },
    {
        "id": "IIR-023",
        "title": "local definition",
        "category": "definition",
        "threats": ["definition_source_loss", "definition_scope_loss"],
        "text": "For the purposes of this policy, business day means a day on which the head office is open.",  # noqa: E501 - corpus source fragment, kept as one exact literal
        "unit_type": "definition",
        "applicability": "definitions",
        "force": "DEF",
        "slots": {
            "definiendum": est("business day"),
            "definiens": est("a day on which the head office is open"),
            "condition": est("For the purposes of this policy"),
        },
        "falsifier": (
            "The local scope marker is dropped, or the term is resolved by ordinary-language "
            "meaning."
        ),
    },
    {
        "id": "IIR-024",
        "title": "unresolved external definition",
        "category": "definition",
        "threats": ["definition_invention", "undefined_term"],
        "text": "Eligible institution has the meaning given in the Framework Agreement.",
        "unit_type": "definition",
        "applicability": "definitions",
        "force": "DEF",
        "slots": {
            "definiendum": est("Eligible institution"),
            "definiens": unknown(),
        },
        "references": [("the Framework Agreement", "DEFINITION")],
        "falsifier": (
            "The definiens is filled in from general knowledge or from an unadmitted document."
        ),
    },
    {
        "id": "IIR-025",
        "title": "cross-reference identified but unresolved",
        "category": "cross_reference",
        "threats": ["reference_expansion"],
        "text": "Approvals are granted subject to section 4 of this policy.",
        "unit_type": "condition",
        "applicability": "approvals",
        "force": "PER",
        "slots": {
            "action": est("granted"),
            "object": est("Approvals"),
        },
        "references": [("section 4 of this policy", "INTERNAL_PROVISION")],
        "falsifier": (
            "The referenced provision's content is inlined without CROSS_REFERENCE_EXPANSION "
            "evidence."
        ),
    },
    {
        "id": "IIR-026",
        "title": "unresolved external cross-reference inside an exception",
        "category": "cross_reference",
        "threats": ["reference_expansion", "reference_loss"],
        "text": "Except as provided in Policy B, all requests must be logged.",
        "unit_type": "exception",
        "applicability": "requests",
        "force": "OBL",
        "slots": {
            "action": est("logged"),
            "object": est("all requests"),
            "exception": est("Except as provided in Policy B"),
        },
        "references": [("Policy B", "EXTERNAL_DOCUMENT")],
        "falsifier": (
            "The reference disappears, or Policy B's content is supplied without admission and "
            "expansion evidence."
        ),
    },
    {
        "id": "IIR-027",
        "title": "advisory-to-obligation strengthening attack",
        "category": "attack",
        "threats": ["force_strengthening"],
        "text": "Departments should consider quarterly reconciliation of suspense accounts.",
        "unit_type": "advisory",
        "applicability": "accounts",
        "force": "ADV",
        "slots": {
            "bearer": est("Departments"),
            "action": est("consider", qualifiers=(("HEDGE", "should"),)),
            "object": est("quarterly reconciliation of suspense accounts"),
        },
        "attack": {"kind": "force", "proposed_force": "OBLIGATION"},
        "forbidden": ["OBLIGATION"],
        "falsifier": "Canonical IR records OBLIGATION where the source says 'should consider'.",
    },
    {
        "id": "IIR-028",
        "title": "permission-to-obligation strengthening attack",
        "category": "attack",
        "threats": ["force_strengthening"],
        "text": "The reviewer may request additional documentation.",
        "unit_type": "permission",
        "applicability": "reviews",
        "force": "PER",
        "slots": {
            "bearer": est("The reviewer"),
            "action": est("request"),
            "object": est("additional documentation"),
        },
        "attack": {"kind": "force", "proposed_force": "OBLIGATION"},
        "forbidden": ["OBLIGATION"],
        "falsifier": "'may' becomes 'must' in canonical IR without an interpretation warrant.",
    },
    {
        "id": "IIR-029",
        "title": "model-invented actor attack",
        "category": "attack",
        "threats": ["invented_actor"],
        "text": "The register shall be reconciled at each period end.",
        "unit_type": "mandate",
        "applicability": "registers",
        "force": "OBL",
        "slots": {
            "action": est("reconciled"),
            "object": est("The register"),
            "temporal_qualifier": est("at each period end"),
        },
        "attack": {"kind": "add_slot", "slot": "bearer", "value": "the finance team"},
        "forbidden": ["the finance team"],
        "falsifier": (
            "A bearer that appears nowhere in the admitted source becomes ESTABLISHED in canonical "
            "IR."
        ),
    },
    {
        "id": "IIR-030",
        "title": "model-dropped exception attack",
        "category": "attack",
        "threats": ["exception_preservation"],
        "text": "All withdrawals require dual approval, except withdrawals under an approved standing order.",  # noqa: E501 - corpus source fragment, kept as one exact literal
        "unit_type": "exception",
        "applicability": "withdrawals",
        "force": "OBL",
        "slots": {
            "action": est("require"),
            "object": est("dual approval"),
            "condition": est("All withdrawals"),
            "exception": est("except withdrawals under an approved standing order"),
        },
        "attack": {"kind": "drop_slot", "slot": "exception"},
        "falsifier": (
            "Canonical IR records the rule with no exception although the source states one."
        ),
    },
    {
        "id": "IIR-031",
        "title": "model-dropped threshold attack",
        "category": "attack",
        "threats": ["threshold_preservation"],
        "text": "Transactions over 250 units must be reviewed by a second officer.",
        "unit_type": "mandate",
        "applicability": "transactions",
        "force": "OBL",
        "slots": {
            "bearer": est("a second officer"),
            "action": est("reviewed"),
            "object": est("Transactions"),
            "quantum": est(
                "over 250 units",
                basis="D",
                qualifiers=(("COMPARATOR", "over"),),
                normalization=("NUMBER", "250", "250"),
            ),
        },
        "attack": {"kind": "drop_slot", "slot": "quantum"},
        "falsifier": (
            "Canonical IR records the obligation without its threshold, reaching every transaction."
        ),
    },
    {
        "id": "IIR-032",
        "title": "model-added business convention attack",
        "category": "attack",
        "threats": ["invented_condition"],
        "text": "The notice must be sent to the registered address.",
        "unit_type": "mandate",
        "applicability": "notices",
        "force": "OBL",
        "slots": {
            "action": est("sent"),
            "object": est("The notice"),
            "counterparty": est("the registered address"),
        },
        "attack": {
            "kind": "add_slot",
            "slot": "condition",
            "value": "during normal business hours",
        },
        "forbidden": ["during normal business hours"],
        "falsifier": "An implied business convention becomes a canonical condition.",
    },
    {
        "id": "IIR-033",
        "title": "two semantically similar propositions from different source instances",
        "category": "identity",
        "threats": ["instance_collapse"],
        "text": "The auditor must sign the closing statement.",
        "unit_type": "mandate",
        "applicability": "audit",
        "force": "OBL",
        "slots": {
            "bearer": est("The auditor"),
            "action": est("sign"),
            "object": est("the closing statement"),
        },
        "second_unit": {"kind": "other_source", "source_id": "policy-iir-033-b"},
        "falsifier": (
            "Identical wording from two authoritative source instances collapses into one "
            "institutional instance, or their semantic similarity stops being observable."
        ),
    },
    {
        "id": "IIR-034",
        "title": "same proposition under a different interpretation instrument",
        "category": "interpretation_authority",
        "threats": ["warrant_independence"],
        "text": "The agency and the operator must maintain the incident log.",
        "unit_type": "mandate",
        "applicability": "incidents",
        "force": "OBL",
        "slots": {
            "bearer": amb(("The agency", "the operator")),
            "action": est("maintain"),
            "object": est("the incident log"),
        },
        "second_unit": {
            "kind": "warrant",
            "slot": "bearer",
            "value": "The agency",
        },
        "falsifier": (
            "Canonical meaning does not change when the interpretation instrument changes, or an "
            "ambiguity resolves without one."
        ),
    },
    {
        "id": "IIR-035",
        "title": "explicit NOT_ESTABLISHED semantic slot",
        "category": "unknown",
        "threats": ["unknown_as_false"],
        "text": "Approval is required before disposal.",
        "unit_type": "mandate",
        "applicability": "disposal",
        "force": "OBL",
        "slots": {
            "action": est("required"),
            "object": est("Approval"),
            "temporal_qualifier": est("before disposal"),
        },
        "falsifier": (
            "A NOT_ESTABLISHED slot is read as a finding that the slot is empty, or as false."
        ),
    },
)

# Boundary vectors. Each carries a real, non-ADMITTED receipt from the frozen evaluator.
BOUNDARY_VECTORS: tuple[dict[str, Any], ...] = (
    {
        "id": "IIR-036",
        "title": "non-admitted receipt rejected at the IR boundary: MISSING_AUTHORITY_EVIDENCE",
        "expected_admission_state": "MISSING_AUTHORITY_EVIDENCE",
        "break": "no_evidence",
        "text": "The office must archive the file.",
        "unit_type": "mandate",
        "applicability": "archive",
    },
    {
        "id": "IIR-037",
        "title": "non-admitted receipt rejected at the IR boundary: OUT_OF_SCOPE",
        "expected_admission_state": "OUT_OF_SCOPE",
        "break": "out_of_scope",
        "text": "Contractors must complete the induction module.",
        "unit_type": "mandate",
        "applicability": "employees",
    },
    {
        "id": "IIR-038",
        "title": "non-admitted receipt rejected at the IR boundary: REVOKED",
        "expected_admission_state": "REVOKED",
        "break": "revoked",
        "text": "Emergency access may be granted by the duty officer.",
        "unit_type": "permission",
        "applicability": "emergency-access",
    },
    {
        "id": "IIR-039",
        "title": "non-admitted receipt rejected at the IR boundary: CONFLICTING_AUTHORITY",
        "expected_admission_state": "CONFLICTING_AUTHORITY",
        "break": "conflict",
        "text": "Exceptions may be approved locally.",
        "unit_type": "permission",
        "applicability": "exceptions",
    },
    {
        "id": "IIR-040",
        "title": "non-admitted receipt rejected at the IR boundary: ADMISSION_NOT_ESTABLISHED",
        "expected_admission_state": "ADMISSION_NOT_ESTABLISHED",
        "break": "suspended",
        "text": "Local practice controls the review order.",
        "unit_type": "mandate",
        "applicability": "reviews",
    },
)

CLAIM_CEILING = (
    "Design-contract behavior only. This corpus does not establish semantic correctness, "
    "a universal institutional ontology, legal interpretation, production interpretation "
    "authority, cross-model reliability, successful IR construction, OCE compilation, "
    "runtime authorization, compliance, production readiness, or independent validation."
)


# ---------------------------------------------------------------------------
# Admission side
# ---------------------------------------------------------------------------


def _source_digest(text: str) -> str:
    return digest_of(text.encode("utf-8"))


def _candidate_unit_id(vector_id: str, span: str, source_id: str) -> str:
    projection = {"candidate_span": span, "source_id": source_id, "vector_id": vector_id}
    return "cnu-" + hashlib.sha256(canonical_json(projection)).hexdigest()[:24]


def _candidate(vector: dict[str, Any], source_id: str, digest: str) -> dict[str, Any]:
    span = vector["text"]
    return {
        "unit_id": _candidate_unit_id(vector["id"], span, source_id),
        "candidate_span": span,
        "unit_type": vector["unit_type"],
        "interpretation_state": "extracted",
        "epistemic_state": "uncertain",
        "source_anchors": [
            {
                "anchor_id": f"anchor-{vector['id'].lower()}-01",
                "source_id": source_id,
                "node_id": f"scenario:{vector['id']}:1",
                "quote": span,
                "page": None,
                "bbox": None,
                "content_hash": digest,
            }
        ],
    }


def _evidence(
    vector_id: str,
    source_id: str,
    version: str,
    digest: str,
    scope: list[str],
    jurisdiction: str,
    standing: str,
    *,
    suffix: str = "01",
    basis: str = "charter:design",
    status: str = "ACTIVE",
    revoked_at: str | None = None,
) -> dict[str, Any]:
    body = {
        "evidence_id": f"AE-{vector_id}-{suffix}",
        "issued_at": ISSUED_AT,
        "source_id": source_id,
        "source_version": version,
        "source_digest": digest,
        "issuer_id": f"synthetic-fixture-issuer-{vector_id.lower()}-{suffix}",
        "authority_basis_ref": basis,
        "jurisdiction": jurisdiction,
        "applicability_scope": scope,
        "source_standing": standing,
        "adopted_at": ADOPTED_AT,
        "effective_from": EFFECTIVE_FROM,
        "effective_until": None,
        "superseded_at": None,
        "revoked_at": revoked_at,
        "admission_warrant": {
            "warrant_id": f"AW-{vector_id}-{suffix}",
            "admission_authority_id": (
                f"synthetic-fixture-admission-authority-{vector_id.lower()}-{suffix}"
            ),
            "delegation_basis_ref": f"synthetic-fixture-delegation:AW-{vector_id}-{suffix}",
            "source_id": source_id,
            "source_version": version,
            "source_digest": digest,
            "jurisdiction": jurisdiction,
            "applicability_scope": scope,
            "effective_from": EFFECTIVE_FROM,
            "effective_until": None,
            "revoked_at": revoked_at,
            "status": status,
        },
    }
    body["evidence_digest"] = digest_of(canonical_json(body))
    return body


def _admission_input(
    vector: dict[str, Any],
    *,
    source_id: str,
    version: str,
    evidence: list[dict[str, Any]],
    registered: bool = True,
    revoked_at: str | None = None,
    evaluation_scope: dict[str, str] | None = None,
) -> dict[str, Any]:
    digest = _source_digest(vector["text"])
    jurisdiction = vector.get("jurisdiction", "enterprise")
    applicability = vector["applicability"]
    scope = [applicability]
    evidence = sorted(evidence, key=lambda item: (item["evidence_id"], item["evidence_digest"]))
    return {
        "candidate": _candidate(vector, source_id, digest),
        "source_registration": {
            "source_id": source_id,
            "source_version": version,
            "source_digest": digest,
            "registered": registered,
            "registry_observation": {
                "registry_boundary_id": "institution-controlled-authority-registry",
                "observation_id": f"registry-observation-{vector['id'].lower()}",
                "availability": "AVAILABLE",
                "freshness": "FRESH",
            },
            "source_standing": vector.get("source_standing", "ADOPTED"),
            "jurisdiction": jurisdiction,
            "applicability_scope": scope,
            "adopted_at": ADOPTED_AT,
            "published_at": PUBLISHED_AT,
            "effective_from": EFFECTIVE_FROM,
            "effective_until": None,
            "superseded_at": None,
            "revoked_at": revoked_at,
        },
        "authority_evidence": evidence,
        "evaluation_time": EVALUATION_TIME,
        "evaluation_scope": evaluation_scope
        or {"jurisdiction": jurisdiction, "applicability": applicability},
        "evaluator": {
            "evaluator_id": "oic-admission-reference-evaluator",
            "evaluator_version": "0.1-preregistered",
        },
        "ruleset": {
            "ruleset_id": "OIC-ADMISSION-BOUNDARY-001",
            "ruleset_digest": (
                "sha256:794ff36a702964ef32b3bc7b68cc9286e06665e20744975db5f4ef692e685b6c"
            ),
        },
    }


def _admit(document: dict[str, Any]) -> dict[str, Any]:
    return evaluate_admission_bytes(canonical_json(document)).to_json()


# ---------------------------------------------------------------------------
# Interpretation side
# ---------------------------------------------------------------------------


def _interpretation_evidence(
    vector_id: str, source_id: str, version: str, digest: str, kind: str
) -> dict[str, Any]:
    registered = kind == "rule"
    body = {
        "interpretation_evidence_id": (f"IE-{'RULE' if registered else 'WARRANT'}-{vector_id}"),
        "issued_at": ISSUED_AT,
        "interpretation_authority_id": (
            f"synthetic-fixture-interpretation-authority-{vector_id.lower()}"
        ),
        "basis_kind": (
            "REGISTERED_INTERPRETATION_RULE"
            if registered
            else "INSTITUTIONAL_INTERPRETATION_WARRANT"
        ),
        "basis_ref": (
            f"synthetic-fixture-interpretation-rule:{vector_id}"
            if registered
            else f"synthetic-fixture-interpretation-warrant:{vector_id}"
        ),
        "applies_to": {
            "source_id": source_id,
            "source_version": version,
            "source_digest": digest,
            "slots": list(SLOTS),
        },
        "permitted_operations": (
            ["FORCE_ASSIGNMENT", "ROLE_ASSIGNMENT"] if registered else ["ROLE_ASSIGNMENT"]
        ),
        "effective_from": EFFECTIVE_FROM,
        "effective_until": None,
        "revoked_at": None,
        "status": "ACTIVE",
    }
    body["evidence_digest"] = digest_of(canonical_json(body))
    return body


def _support(anchor: dict[str, Any], quote: str) -> dict[str, Any]:
    return {
        "anchor_id": anchor["anchor_id"],
        "quote": quote,
        "content_hash": anchor["content_hash"],
    }


def _applicable_slots(force: str, ruleset: dict[str, Any]) -> set[str]:
    return set(ruleset["slot_applicability_by_force"][force]) | {"normative_force"}


def _assertion(
    slot: str,
    spec: dict[str, Any] | None,
    *,
    anchor: dict[str, Any],
    span: str,
    applicable: set[str],
    rule_ref: str,
    warrant_ref: str | None = None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "assertion_id": f"iia-{slot}",
        "slot": slot,
        "interpretation_status": NOT_ESTABLISHED,
        "value": None,
        "alternatives": [],
        "source_support": None,
        "interpretation_basis": "NONE",
        "interpretation_evidence_refs": [],
        "material_qualifiers": [],
        "normalization": None,
    }
    if spec is None:
        if slot not in applicable:
            base["interpretation_status"] = NOT_APPLICABLE
        return base

    if spec["status"] == AMBIGUOUS:
        base["interpretation_status"] = AMBIGUOUS
        base["alternatives"] = [
            {"value": value, "source_support": _support(anchor, value)}
            for value in spec["alternatives"]
        ]
        for alternative in spec["alternatives"]:
            if alternative not in span:
                raise AssertionError(f"{slot}: alternative not in admitted span: {alternative!r}")
        return base

    if spec["status"] == NOT_ESTABLISHED:
        # An applicable slot the source does not supply. Explicitly unknown, never false.
        return base

    quote = spec["quote"]
    if quote not in span:
        raise AssertionError(f"{slot}: quote not in admitted span: {quote!r}")
    basis = spec["basis"]
    refs: list[str] = []
    if basis == "R":
        refs = [rule_ref]
    elif basis == "W":
        if warrant_ref is None:
            raise AssertionError(f"{slot}: warrant basis with no warrant reference")
        refs = [warrant_ref]
    base.update(
        {
            "interpretation_status": ESTABLISHED,
            "value": spec["value"],
            "source_support": _support(anchor, quote),
            "interpretation_basis": BASIS[basis],
            "interpretation_evidence_refs": refs,
        }
    )
    for kind, text in spec["qualifiers"]:
        if text not in span:
            raise AssertionError(f"{slot}: qualifier not in admitted span: {text!r}")
        base["material_qualifiers"].append(
            {"qualifier_kind": kind, "text": text, "source_support": _support(anchor, text)}
        )
    if spec["normalization"] is not None:
        kind, raw, normalized = spec["normalization"]
        if raw not in span:
            raise AssertionError(f"{slot}: normalization source not in admitted span: {raw!r}")
        base["normalization"] = {
            "kind": kind,
            "raw_source_text": raw,
            "normalized_value": normalized,
        }
    return base


def _semantic_projection(unit: dict[str, Any]) -> dict[str, Any]:
    """The meaning alone: no admission binding, no source instance, no evidence."""
    return {
        "assertions": [
            {
                "slot": assertion["slot"],
                "interpretation_status": assertion["interpretation_status"],
                "value": assertion["value"],
                "alternatives": [item["value"] for item in assertion["alternatives"]],
                "material_qualifiers": [item["text"] for item in assertion["material_qualifiers"]],
                "normalized_value": (
                    assertion["normalization"]["normalized_value"]
                    if assertion["normalization"]
                    else None
                ),
            }
            for assertion in unit["assertions"]
        ],
        "exception_closure": unit["exception_closure"],
        "unresolved_reference_texts": sorted(
            item["reference_text"] for item in unit["unresolved_references"]
        ),
    }


def _build_unit(
    vector: dict[str, Any],
    receipt: dict[str, Any],
    admission_input: dict[str, Any],
    ruleset: dict[str, Any],
    ruleset_digest: str,
    *,
    slot_overrides: dict[str, dict[str, Any]] | None = None,
    supersedes: str | None = None,
) -> dict[str, Any]:
    force = FORCE_NAMES[vector["force"]]
    span = vector["text"]
    anchor = admission_input["candidate"]["source_anchors"][0]
    applicable = _applicable_slots(force, ruleset)
    rule_ref = f"IE-RULE-{vector['id']}"
    warrant_ref = f"IE-WARRANT-{vector['id']}"

    slots = dict(vector["slots"])
    if slot_overrides:
        slots.update(slot_overrides)
    slots["normative_force"] = est(force, quote=span, basis="R")

    assertions = [
        _assertion(
            slot,
            slots.get(slot),
            anchor=anchor,
            span=span,
            applicable=applicable,
            rule_ref=rule_ref,
            warrant_ref=warrant_ref,
        )
        for slot in SLOTS
    ]

    references = [
        {
            "reference_id": f"iref-{vector['id'].lower()}-{index + 1:02d}",
            "reference_text": text,
            "reference_kind": kind,
            "resolution_status": "UNRESOLVED",
            "source_support": _support(anchor, text),
            "resolved_target": None,
        }
        for index, (text, kind) in enumerate(vector.get("references", []))
    ]
    for reference in references:
        if reference["reference_text"] not in span:
            raise AssertionError(f"reference not in admitted span: {reference['reference_text']!r}")

    unit: dict[str, Any] = {
        "ir_schema_id": IR_SCHEMA_ID,
        "interpretation_ruleset": {
            "ruleset_id": INTERPRETATION_RULESET_ID,
            "ruleset_digest": ruleset_digest,
        },
        "admission": {
            "admission_receipt_id": receipt["admission_receipt_id"],
            "admission_state": receipt["admission_state"],
            "candidate_unit_id": receipt["candidate_unit_id"],
            "candidate_projection_digest": receipt["candidate_projection_digest"],
            "source_id": receipt["source_id"],
            "source_version": receipt["source_version"],
            "source_digest": receipt["source_digest"],
            "authority_evidence_refs": receipt["authority_evidence_refs"],
            "authority_evidence_digests": receipt["authority_evidence_digests"],
            "evaluation_time": receipt["evaluation_time"],
            "evaluation_scope": receipt["evaluation_scope"],
            "ruleset_id": receipt["ruleset_id"],
            "ruleset_digest": receipt["ruleset_digest"],
            "evaluator_id": receipt["evaluator_id"],
            "evaluator_version": receipt["evaluator_version"],
        },
        "interpretation_time": INTERPRETATION_TIME,
        "assertions": assertions,
        "exception_closure": "OPEN",
        "closed_world_evidence_refs": [],
        "unresolved_references": references,
        "supersedes_ir_unit_id": supersedes,
        "claim_ceiling": CLAIM_CEILING,
    }
    unit["semantic_equivalence_key"] = digest_of(canonical_json(_semantic_projection(unit)))
    # Identity binds the whole unit: the semantic projection, the admission receipt, the
    # source instance, the interpretation ruleset and the interpretation evidence refs.
    unit["ir_unit_id"] = "iir-" + digest_of(canonical_json(unit))
    return unit


def _build_proposal(vector: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    """The provisional proposal, including whatever the attack vectors get wrong."""
    force = FORCE_NAMES[vector["force"]]
    attack = vector.get("attack", {})
    proposed: list[dict[str, Any]] = []

    proposed_force = attack.get("proposed_force", force) if attack.get("kind") == "force" else force
    proposed.append(
        {
            "slot": "normative_force",
            "proposed_value": proposed_force,
            "proposed_source_quote": vector["text"],
        }
    )

    dropped = attack.get("slot") if attack.get("kind") == "drop_slot" else None
    for slot in SLOTS:
        if slot == "normative_force" or slot == dropped:
            continue
        spec = vector["slots"].get(slot)
        if spec is None:
            continue
        if spec["status"] == AMBIGUOUS:
            proposed.append(
                {
                    "slot": slot,
                    "proposed_value": spec["alternatives"][0],
                    "proposed_source_quote": spec["alternatives"][0],
                }
            )
            continue
        if spec["status"] != ESTABLISHED:
            continue
        entry: dict[str, Any] = {
            "slot": slot,
            "proposed_value": spec["value"],
            "proposed_source_quote": spec["quote"],
        }
        if spec["qualifiers"]:
            entry["proposed_material_qualifiers"] = [text for _, text in spec["qualifiers"]]
        proposed.append(entry)

    if attack.get("kind") == "add_slot":
        proposed.append(
            {
                "slot": attack["slot"],
                "proposed_value": attack["value"],
                "proposed_source_quote": None,
            }
        )

    proposal = {
        "proposal_id": f"iip-{vector['id'].lower()}",
        "proposal_schema_id": PROPOSAL_SCHEMA_ID,
        "admission_receipt_id": receipt["admission_receipt_id"],
        "candidate_unit_id": receipt["candidate_unit_id"],
        "candidate_projection_digest": receipt["candidate_projection_digest"],
        "proposer": {
            "proposer_kind": "MODEL",
            "proposer_id": "provider-neutral-synthetic-proposer",
        },
        "proposal_state": "PROVISIONAL",
        "epistemic_state": "uncertain",
        "proposed_assertions": proposed,
    }
    if vector.get("references"):
        proposal["proposed_unresolved_references"] = [
            {"reference_text": text, "reference_kind": kind} for text, kind in vector["references"]
        ]
    return proposal


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _validator(name: str) -> Draft202012Validator:
    documents = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(DESIGN.glob("*.schema.json"))
    }
    resources: list[tuple[str, Any]] = []
    for filename, document in documents.items():
        resource = Resource.from_contents(document, default_specification=DRAFT202012)
        if isinstance(document.get("$id"), str):
            resources.append((document["$id"], resource))
        resources.append((filename, resource))
    registry = Registry().with_resources(resources)
    return Draft202012Validator(documents[name], registry=registry)


def _check(validator: Draft202012Validator, instance: object, label: str) -> None:
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        pointer = "/".join(str(part) for part in first.absolute_path)
        raise AssertionError(f"{label}: /{pointer}: {first.message}")


def build() -> dict[str, Any]:
    ruleset_path = DESIGN / "INTERPRETATION-RULESET-v0.1.json"
    ruleset = json.loads(ruleset_path.read_text(encoding="utf-8"))
    ruleset_digest = digest_of(canonical_json(ruleset))

    ir_validator = _validator("INSTITUTIONAL-IR-v0.1.schema.json")
    proposal_validator = _validator("INTERPRETATION-PROPOSAL-v0.1.schema.json")
    evidence_validator = _validator("INTERPRETATION-EVIDENCE-v0.1.schema.json")

    vectors: list[dict[str, Any]] = []

    for vector in VECTORS:
        vid = vector["id"]
        source_id = f"policy-{vid.lower()}"
        version = "v1"
        digest = _source_digest(vector["text"])
        jurisdiction = vector.get("jurisdiction", "enterprise")
        standing = vector.get("source_standing", "ADOPTED")
        scope = [vector["applicability"]]

        admission_input = _admission_input(
            vector,
            source_id=source_id,
            version=version,
            evidence=[_evidence(vid, source_id, version, digest, scope, jurisdiction, standing)],
        )
        receipt = _admit(admission_input)
        if receipt["admission_state"] != "ADMITTED":
            raise AssertionError(f"{vid}: positive vector is not ADMITTED: {receipt}")

        interpretation_evidence = [
            _interpretation_evidence(vid, source_id, version, digest, "rule")
        ]
        units = [_build_unit(vector, receipt, admission_input, ruleset, ruleset_digest)]

        second = vector.get("second_unit")
        extra_inputs: list[dict[str, Any]] = []
        extra_receipts: list[dict[str, Any]] = []
        if second is not None:
            kind = second["kind"]
            if kind == "warrant":
                interpretation_evidence.append(
                    _interpretation_evidence(vid, source_id, version, digest, "warrant")
                )
                override = {second["slot"]: est(second["value"], quote=second["value"], basis="W")}
                units.append(
                    _build_unit(
                        vector,
                        receipt,
                        admission_input,
                        ruleset,
                        ruleset_digest,
                        slot_overrides=override,
                    )
                )
            else:
                other_source = second.get("source_id", source_id)
                other_version = second.get("source_version", version)
                other_input = _admission_input(
                    vector,
                    source_id=other_source,
                    version=other_version,
                    evidence=[
                        _evidence(
                            vid,
                            other_source,
                            other_version,
                            digest,
                            scope,
                            jurisdiction,
                            standing,
                            suffix="02",
                        )
                    ],
                )
                other_receipt = _admit(other_input)
                if other_receipt["admission_state"] != "ADMITTED":
                    raise AssertionError(f"{vid}: second unit is not ADMITTED")
                extra_inputs.append(other_input)
                extra_receipts.append(other_receipt)
                interpretation_evidence.append(
                    _interpretation_evidence(
                        f"{vid}-B", other_source, other_version, digest, "rule"
                    )
                )
                supersedes = units[0]["ir_unit_id"] if kind == "supersession" else None
                units.append(
                    _build_unit(
                        {**vector, "id": f"{vid}-B"},
                        other_receipt,
                        other_input,
                        ruleset,
                        ruleset_digest,
                        supersedes=supersedes,
                    )
                )

        proposal = _build_proposal(vector, receipt)

        for unit in units:
            _check(ir_validator, unit, f"{vid} IR unit")
        _check(proposal_validator, proposal, f"{vid} proposal")
        for item in interpretation_evidence:
            _check(evidence_validator, item, f"{vid} interpretation evidence")
            recomputed = digest_of(
                canonical_json({k: v for k, v in item.items() if k != "evidence_digest"})
            )
            if recomputed != item["evidence_digest"]:
                raise AssertionError(f"{vid}: interpretation evidence digest does not recompute")

        entry: dict[str, Any] = {
            "vector_id": vid,
            "title": vector["title"],
            "category": vector["category"],
            "threat_tags": vector["threats"],
            "source_text": vector["text"],
            "admission_inputs": [admission_input, *extra_inputs],
            "admission_receipts": [receipt, *extra_receipts],
            "interpretation_evidence": interpretation_evidence,
            "interpretation_proposal": proposal,
            "expected_canonical_ir": units,
            "expected_boundary_rejection": None,
            "forbidden_in_canonical_ir": vector.get("forbidden", []),
            "falsifier": vector["falsifier"],
            "claim_ceiling": CLAIM_CEILING,
        }
        vectors.append(entry)

    for vector in BOUNDARY_VECTORS:
        vid = vector["id"]
        source_id = f"policy-{vid.lower()}"
        version = "v1"
        digest = _source_digest(vector["text"])
        scope = [vector["applicability"]]
        kind = vector["break"]

        evidence: list[dict[str, Any]] = []
        registered = True
        revoked_at = None
        evaluation_scope = None
        if kind == "no_evidence":
            evidence = []
        elif kind == "out_of_scope":
            evidence = [_evidence(vid, source_id, version, digest, scope, "enterprise", "ADOPTED")]
            evaluation_scope = {"jurisdiction": "enterprise", "applicability": "contractors"}
        elif kind == "revoked":
            revoked_at = "2026-05-01T00:00:00Z"
            evidence = [
                _evidence(
                    vid,
                    source_id,
                    version,
                    digest,
                    scope,
                    "enterprise",
                    "ADOPTED",
                    status="REVOKED",
                    revoked_at=revoked_at,
                )
            ]
        elif kind == "conflict":
            evidence = [
                _evidence(
                    vid,
                    source_id,
                    version,
                    digest,
                    scope,
                    "enterprise",
                    "ADOPTED",
                    suffix="01",
                    basis="charter:a",
                ),
                _evidence(
                    vid,
                    source_id,
                    version,
                    digest,
                    scope,
                    "enterprise",
                    "ADOPTED",
                    suffix="02",
                    basis="charter:b",
                ),
            ]
        elif kind == "suspended":
            body = _evidence(vid, source_id, version, digest, scope, "enterprise", "UNKNOWN")
            body.pop("evidence_digest")
            body["admission_warrant"]["status"] = "SUSPENDED"
            body["evidence_digest"] = digest_of(canonical_json(body))
            evidence = [body]
        else:
            raise AssertionError(f"unknown boundary break: {kind}")

        admission_input = _admission_input(
            vector,
            source_id=source_id,
            version=version,
            evidence=evidence,
            registered=registered,
            revoked_at=revoked_at,
            evaluation_scope=evaluation_scope,
        )
        receipt = _admit(admission_input)
        if receipt["admission_state"] != vector["expected_admission_state"]:
            raise AssertionError(
                f"{vid}: expected {vector['expected_admission_state']}, "
                f"got {receipt['admission_state']}"
            )

        vectors.append(
            {
                "vector_id": vid,
                "title": vector["title"],
                "category": "ir_input_boundary",
                "threat_tags": ["non_admitted_material"],
                "source_text": vector["text"],
                "admission_inputs": [admission_input],
                "admission_receipts": [receipt],
                "interpretation_evidence": [],
                "interpretation_proposal": None,
                "expected_canonical_ir": [],
                "expected_boundary_rejection": "IR_INPUT_NOT_ADMITTED",
                "forbidden_in_canonical_ir": [],
                "falsifier": (
                    "A canonical IR unit is constructed from a receipt whose admission_state "
                    f"is {vector['expected_admission_state']}, or the refusal is recorded as an "
                    "empty IR rather than an input-boundary failure."
                ),
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    threat_tags = sorted({tag for vector in vectors for tag in vector["threat_tags"]})
    return {
        "corpus_id": CORPUS_ID,
        "design_only": True,
        "runtime_execution": False,
        "model_call": False,
        "provider_neutral": True,
        "ir_schema": "INSTITUTIONAL-IR-v0.1.schema.json",
        "proposal_schema": "INTERPRETATION-PROPOSAL-v0.1.schema.json",
        "interpretation_evidence_schema": "INTERPRETATION-EVIDENCE-v0.1.schema.json",
        "interpretation_ruleset": "INTERPRETATION-RULESET-v0.1.json",
        "interpretation_ruleset_digest": ruleset_digest,
        "admission_runtime_freeze": "OIC-ADMISSION-RUNTIME-FREEZE-001",
        "admission_ruleset_digest": (
            "sha256:794ff36a702964ef32b3bc7b68cc9286e06665e20744975db5f4ef692e685b6c"
        ),
        "canonicalization_id": "OIC-ADMISSION-CANONICAL-JSON-v0.1",
        "vector_count": len(vectors),
        "positive_vector_count": len(VECTORS),
        "boundary_vector_count": len(BOUNDARY_VECTORS),
        "threat_tags": threat_tags,
        "vectors": vectors,
        "claim_ceiling": CLAIM_CEILING,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }


def main() -> int:
    corpus = build()
    payload = json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    CORPUS_PATH.write_text(payload, encoding="utf-8")
    raw = CORPUS_PATH.read_bytes()
    freeze = {
        "freeze_id": "OIC-INSTITUTIONAL-IR-001-TEST-VECTORS-FREEZE-v0.1",
        "corpus_id": CORPUS_ID,
        "corpus_path": "design/institutional-ir-001/TEST-VECTORS-v0.1.json",
        "corpus_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_bytes": len(raw),
        "vector_count": corpus["vector_count"],
        "positive_vector_count": corpus["positive_vector_count"],
        "boundary_vector_count": corpus["boundary_vector_count"],
        "threat_tags": corpus["threat_tags"],
        "design_only": True,
        "runtime_execution": False,
        "model_call": False,
        "provider_neutral": True,
        "admission_runtime_freeze": "OIC-ADMISSION-RUNTIME-FREEZE-001",
        "interpretation_ruleset_digest": corpus["interpretation_ruleset_digest"],
        "claim_ceiling": CLAIM_CEILING,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }
    FREEZE_PATH.write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"corpus: {corpus['vector_count']} vectors, {len(raw)} bytes")
    print(f"sha256: {freeze['corpus_sha256']}")
    print(f"interpretation ruleset digest: {corpus['interpretation_ruleset_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
