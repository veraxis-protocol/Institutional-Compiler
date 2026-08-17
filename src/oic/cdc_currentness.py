"""Currentness propagation for CDC vertical slice 001.

This module implements two artifacts frozen before implementation and imported
byte-identically under ``veraxis/currentness-slice-001/``:

``CURRENTNESS-PROPAGATION-SLICE-001-SEMANTIC-DESIGN-v0.2.md``
    sha256 82ac78f51439e438eafb31565369f73ba58e530ad1a18b75688f4dcb91ffe0e8
``CURRENTNESS-SLICE-001-DIGEST-DERIVATION-v0.1.md``
    sha256 8b398291a657ab97e8e9e52b345051e257069c3532b49a8826207315b5c4c5dd

The semantic design controls; the derivation document controls serialization.
Neither is paraphrased here.  Currentness is a relation over (artifact identity,
institutional state, evaluation time) and is never written into an artifact: the
historical artifact is read, digested and left alone.

The module establishes no institutional reliance, no officiality, no CDC
acceptance and no production conformance.  ``PROCEED_TO_NEXT_GATE`` is not an
authorization; it emits no event and performs no transition.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any, Final

from oic.errors import OICError

CURRENTNESS_CONTRACT_ID: Final = "CURRENTNESS-PROPAGATION-SLICE-001-SEMANTIC-DESIGN-v0.2"
SEMANTIC_DESIGN_SHA256: Final = "82ac78f51439e438eafb31565369f73ba58e530ad1a18b75688f4dcb91ffe0e8"
DIGEST_DERIVATION_SHA256: Final = "8b398291a657ab97e8e9e52b345051e257069c3532b49a8826207315b5c4c5dd"
SYNTHETIC_CONTROL_SHA256: Final = "2a9158e0561d3ab1886f3f4f52c0b828a76979aadccc66b58c95ccb84914a45d"

ASSURANCE_CLASS: Final = "INTERNAL_TECHNICAL_DEMONSTRATION"
SELF_DESIGNED_AND_SELF_ADJUDICATED: Final = True
INDEPENDENT_REVIEW_CLAIM: Final = False

RESOLUTION_SCHEMA_VERSION: Final = "CDC-CURRENTNESS-RESOLUTION-v0.2"
USE_GATE_DECISION_SCHEMA_VERSION: Final = "CDC-CURRENTNESS-USE-GATE-DECISION-v0.2"

# ---------------------------------------------------------------------------
# Currentness states (semantic design §2, §3)
# ---------------------------------------------------------------------------

CURRENT: Final = "CURRENT"
SUPERSEDED: Final = "SUPERSEDED"
INELIGIBLE: Final = "INELIGIBLE"
UNKNOWN: Final = "UNKNOWN"
CURRENTNESS_STATES: Final = (CURRENT, SUPERSEDED, INELIGIBLE, UNKNOWN)

ELIGIBLE_SUBJECT_TO_FURTHER_GATES: Final = "ELIGIBLE_FOR_PRESENT_USE_SUBJECT_TO_FURTHER_GATES"
NOT_ELIGIBLE_FOR_PRESENT_USE: Final = "NOT_ELIGIBLE_FOR_PRESENT_USE"
ELIGIBILITY_UNDETERMINED: Final = "ELIGIBILITY_UNDETERMINED"

# ---------------------------------------------------------------------------
# Closed reason-code sets (semantic design §8): resolver 11, use gate 10
# ---------------------------------------------------------------------------

RESOLVER_REASON_CODES: Final[dict[str, str]] = {
    "R1": "NO_OPERATIVE_CONTROLLING_RECORD",
    "R2": "OUTPUT_SUPERSEDED",
    "R3": "OUTPUT_INELIGIBLE_PENDING_REGENERATION_OR_EXPLICIT_HUMAN_RESOLUTION",
    "R4": "CURRENTNESS_BASIS_INCOMPLETE",
    "R5": "BASIS_COMPLETENESS_ATTESTATION_MISSING",
    "R6": "BASIS_COMPLETENESS_ATTESTATION_INVALID",
    "R7": "AMBIGUOUS_CONTROLLING_SUCCESSORS",
    "R8": "SUCCESSOR_ADDRESSES_DIFFERENT_OUTPUT",
    "R9": "SUCCESSOR_BINDING_MISMATCH",
    "R10": "ARTIFACT_INTEGRITY_MISMATCH",
    "R11": "EFFECTIVE_TIME_NOT_YET_REACHED",
}

USE_GATE_REASON_CODES: Final[dict[str, str]] = {
    "G1": "PROCEED_TO_NEXT_GATE",
    "G2": "DENY_OUTPUT_SUPERSEDED",
    "G3": "DENY_OUTPUT_INELIGIBLE",
    "G4": "DENY_CURRENTNESS_UNKNOWN_FAIL_CLOSED",
    "G5": "DENY_ARTIFACT_INTEGRITY_MISMATCH",
    "G6": "DENY_RESOLUTION_BINDING_MISMATCH",
    "G7": "DENY_RESOLUTION_STALE_REEVALUATION_REQUIRED",
    "G8": "DENY_CALLER_SUPPLIED_CURRENTNESS_REJECTED",
    "G9": "DENY_PRECOMPUTED_RESOLUTION_DIGEST_MISMATCH",
    "G10": "DENY_INDEX_IDENTITY_MISMATCH",
}

RESOLVER_REASON_CODE_COUNT: Final = len(RESOLVER_REASON_CODES)
USE_GATE_REASON_CODE_COUNT: Final = len(USE_GATE_REASON_CODES)

PROCEED: Final = "PROCEED"
DENY: Final = "DENY"

# ---------------------------------------------------------------------------
# Record classes and admission paths
# ---------------------------------------------------------------------------

HISTORICAL_ARTIFACT_IDENTITY_RECORD: Final = "HISTORICAL_ARTIFACT_IDENTITY_RECORD"
SUPERSESSION_RECORD: Final = "SUPERSESSION_RECORD"
CORRECTION_SUCCESSOR_RECORD: Final = "CORRECTION_SUCCESSOR_RECORD"
ELIGIBILITY_DETERMINATION_RECORD: Final = "ELIGIBILITY_DETERMINATION_RECORD"

CONTROLLING_RECORD_CLASSES: Final = (
    SUPERSESSION_RECORD,
    CORRECTION_SUCCESSOR_RECORD,
    ELIGIBILITY_DETERMINATION_RECORD,
)

SYNTHETIC_CONTROL_PATH: Final = "SYNTHETIC_CONTROL_PATH_ONLY"
GOVERNED_BASIS_ATTESTATION_PATH: Final = "GOVERNED_BASIS_ATTESTATION_PATH"
SYNTHETIC_UNAFFECTED_CONTROL: Final = "SYNTHETIC_UNAFFECTED_CONTROL"

FUTURE_SUPERSESSION_SCHEDULED: Final = "FUTURE_SUPERSESSION_SCHEDULED"
ELIGIBILITY_DETERMINATION_ALSO_PRESENT: Final = "ELIGIBILITY_DETERMINATION_ALSO_PRESENT"

DEFAULT_RESOLUTION_TTL_SECONDS: Final = 300


class CurrentnessIndexError(OICError):
    """The currentness index could not be built over governed state."""


class CurrentnessGateError(OICError):
    """The use gate refused to decide at all, rather than emit a coded decision."""


# ---------------------------------------------------------------------------
# Canonical serialization — digest derivation §1
# ---------------------------------------------------------------------------


def canonical_bytes(value: object) -> bytes:
    """Serialize exactly as the frozen derivation document requires.

    Lexicographic key order, no indentation, ``","``/``":"`` separators, literal
    non-ASCII, no trailing newline, no value normalization.
    """
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_digest(value: object) -> str:
    """Return the unprefixed lowercase SHA-256 of the canonical form."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def strip_digest_prefix(value: str) -> str:
    """Drop a presentation-only ``sha256:`` prefix before any comparison.

    Derivation §4: a comparison failing because one side carried a prefix is an
    implementation defect, not a mismatch.
    """
    return value[len("sha256:") :] if value.startswith("sha256:") else value


def digests_equal(left: str, right: str) -> bool:
    """Compare two digests independently of prefix presentation."""
    return strip_digest_prefix(left) == strip_digest_prefix(right)


def _self_excluded(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    """Remove the record's own digest field by key removal, never by null."""
    return {key: value for key, value in record.items() if key != field}


# --- the nine frozen digest classes (derivation §3) -------------------------


def historical_artifact_digest(body: Mapping[str, Any]) -> str:
    """3.1 — the deliverable content body only, never its transport wrapper."""
    return canonical_digest(body)


def basis_record_digest(record: Mapping[str, Any]) -> str:
    """3.2 — one governing record exactly as stored; nothing excluded."""
    return canonical_digest(record)


def completeness_digest(attestation: Mapping[str, Any]) -> str:
    """3.3 — attestation minus ``completeness_digest``; paired arrays unsorted."""
    return canonical_digest(_self_excluded(attestation, "completeness_digest"))


def currentness_index_digest(
    *,
    scope_ref: str,
    entries: Sequence[Mapping[str, Any]],
    attestations: Sequence[Mapping[str, Any]],
    admitted_at: str,
) -> str:
    """3.4 — reduced entries sorted by (output_ref, record_ref); no bodies."""
    reduced = sorted(entries, key=lambda entry: (entry["output_ref"], entry["record_ref"]))
    return canonical_digest(
        {
            "scope_ref": scope_ref,
            "entries": reduced,
            "attestations": list(attestations),
            "admitted_at": admitted_at,
        }
    )


def resolution_digest(record: Mapping[str, Any]) -> str:
    """3.5 — whole resolution minus its own digest; evaluation times included."""
    return canonical_digest(_self_excluded(record, "resolution_digest"))


def use_gate_decision_digest(record: Mapping[str, Any]) -> str:
    """3.6 — whole decision minus its own digest, binding resolution + artifact."""
    return canonical_digest(_self_excluded(record, "use_gate_decision_digest"))


OBSERVATION_DIGEST_DOMAIN: Final = (
    "case_id",
    "mutation_applied",
    "expected_reason_code",
    "observed_reason_code",
    "observed_state",
    "subject_refs",
    "evaluated_at",
)


def observation_digest(record: Mapping[str, Any]) -> str:
    """3.7 — exactly the seven named observation fields, nothing else."""
    missing = sorted(set(OBSERVATION_DIGEST_DOMAIN) - record.keys())
    if missing:
        raise CurrentnessIndexError(f"adversarial observation missing fields: {missing}")
    return canonical_digest({key: record[key] for key in OBSERVATION_DIGEST_DOMAIN})


def package_digest(record: Mapping[str, Any]) -> str:
    """3.8 — whole package minus its own digest; member identities, not bodies."""
    return canonical_digest(_self_excluded(record, "package_digest"))


def persisted_file_sha256(payload: bytes) -> str:
    """3.9 — the exact persisted bytes, including any trailing newline."""
    return hashlib.sha256(payload).hexdigest()


DIGEST_CLASSES: Final = (
    "historical_artifact_digest",
    "basis_record_digest",
    "completeness_digest",
    "currentness_index_digest",
    "resolution_digest",
    "use_gate_decision_digest",
    "observation_digest",
    "package_digest",
    "persisted_file_sha256",
)

# ---------------------------------------------------------------------------
# Time handling
# ---------------------------------------------------------------------------


def parse_utc(value: str) -> datetime:
    """Parse a ``…Z`` UTC instant; anything else is a caller defect."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CurrentnessIndexError(f"not a UTC Z-suffixed instant: {value!r}")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def format_utc(moment: datetime) -> str:
    """Render an instant in the single ``…Z`` form used across the slice."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# BasisCompletenessAttestation — semantic design §3
# ---------------------------------------------------------------------------

ATTESTATION_REQUIRED_FIELDS: Final = (
    "scope_ref",
    "covered_output_ref",
    "record_kinds_covered",
    "basis_snapshot_refs",
    "basis_snapshot_digests",
    "completeness_as_of",
    "admitted_at",
    "fixture_class",
)
# ``semantics`` is prose carried by the frozen synthetic control artifact.  It is
# inside the digest domain because the derivation excludes only the self-digest,
# so it is admitted explicitly rather than silently tolerated.
ATTESTATION_OPTIONAL_FIELDS: Final = ("semantics",)
ATTESTATION_ALLOWED_FIELDS: Final = (
    *ATTESTATION_REQUIRED_FIELDS,
    *ATTESTATION_OPTIONAL_FIELDS,
    "completeness_digest",
)


@dataclass(frozen=True, slots=True, eq=False)
class BasisCompletenessAttestation:
    """Affirmative evidence that a governing basis was attested complete.

    Absence of one can never produce ``CURRENT``; that is the whole point of the
    object, so it carries its own verbatim source form for digest reproduction.
    """

    scope_ref: str
    covered_output_ref: str
    record_kinds_covered: tuple[str, ...]
    basis_snapshot_refs: tuple[str, ...]
    basis_snapshot_digests: tuple[str, ...]
    completeness_as_of: str
    admitted_at: str
    fixture_class: str | None
    completeness_digest: str
    source: Mapping[str, Any]
    admission_path: str

    def as_record(self) -> dict[str, Any]:
        """The stored form plus the reproduced digest, for index digesting."""
        return {**dict(self.source), "completeness_digest": self.completeness_digest}


def parse_basis_completeness_attestation(
    source: Mapping[str, Any], *, admission_path: str
) -> BasisCompletenessAttestation:
    """Build an attestation or raise; malformed input is R6 at the resolver.

    Closure is enforced over the frozen field set.  The stored form is kept
    verbatim so ``completeness_digest`` reproduces from the same bytes an
    adjudicator would hash.
    """
    if not isinstance(source, Mapping):
        raise CurrentnessIndexError("attestation is not a mapping")
    unknown = sorted(set(source) - set(ATTESTATION_ALLOWED_FIELDS))
    if unknown:
        raise CurrentnessIndexError(f"attestation carries unknown fields: {unknown}")
    missing = sorted(set(ATTESTATION_REQUIRED_FIELDS) - source.keys())
    if missing:
        raise CurrentnessIndexError(f"attestation missing required fields: {missing}")
    refs = source["basis_snapshot_refs"]
    snapshot_digests = source["basis_snapshot_digests"]
    if not isinstance(refs, list) or not isinstance(snapshot_digests, list):
        raise CurrentnessIndexError("attestation basis snapshots must be arrays")
    if len(refs) != len(snapshot_digests):
        raise CurrentnessIndexError(
            "attestation basis refs and digests are not positionally paired"
        )
    kinds = source["record_kinds_covered"]
    if not isinstance(kinds, list) or not all(isinstance(kind, str) for kind in kinds):
        raise CurrentnessIndexError("attestation record_kinds_covered must be an array of strings")
    reproduced = completeness_digest(source)
    stored = source.get("completeness_digest")
    if stored is not None and not digests_equal(str(stored), reproduced):
        raise CurrentnessIndexError("attestation completeness_digest does not reproduce")
    parse_utc(str(source["completeness_as_of"]))
    parse_utc(str(source["admitted_at"]))
    return BasisCompletenessAttestation(
        scope_ref=str(source["scope_ref"]),
        covered_output_ref=str(source["covered_output_ref"]),
        record_kinds_covered=tuple(kinds),
        basis_snapshot_refs=tuple(str(ref) for ref in refs),
        basis_snapshot_digests=tuple(str(item) for item in snapshot_digests),
        completeness_as_of=str(source["completeness_as_of"]),
        admitted_at=str(source["admitted_at"]),
        fixture_class=(None if source["fixture_class"] is None else str(source["fixture_class"])),
        completeness_digest=reproduced,
        source=dict(source),
        admission_path=admission_path,
    )


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class IndexEntry:
    """One governing record as admitted, with its identity fixed at admission."""

    output_ref: str
    record_ref: str
    record_class: str
    record_digest: str
    effective_at: str | None
    admitted_at: str
    record: Mapping[str, Any]

    def reduced(self) -> dict[str, Any]:
        """The six-field projection that alone participates in index identity."""
        return {
            "output_ref": self.output_ref,
            "record_ref": self.record_ref,
            "record_digest": self.record_digest,
            "record_class": self.record_class,
            "effective_at": self.effective_at,
            "admitted_at": self.admitted_at,
        }


@dataclass(frozen=True, slots=True, eq=False)
class CurrentnessIndex:
    """Separately maintained institutional state; never part of an artifact."""

    scope_ref: str
    entries: tuple[IndexEntry, ...]
    attestations: tuple[BasisCompletenessAttestation, ...]
    observed_at: str
    admitted_at: str
    index_digest: str
    basis_source_identities: Mapping[str, str]

    def entries_for(self, output_ref: str) -> tuple[IndexEntry, ...]:
        """Every admitted record naming this output, in admission order."""
        return tuple(entry for entry in self.entries if entry.output_ref == output_ref)

    def attestation_for(self, output_ref: str) -> BasisCompletenessAttestation | None:
        """The attestation covering this output, if one was admitted."""
        for attestation in self.attestations:
            if attestation.covered_output_ref == output_ref:
                return attestation
        return None

    def covers(self, output_ref: str) -> bool:
        """Whether the index holds any record at all about this output."""
        return bool(self.entries_for(output_ref)) or self.attestation_for(output_ref) is not None


def _index_digest_of(
    scope_ref: str,
    entries: Iterable[IndexEntry],
    attestations: Iterable[BasisCompletenessAttestation],
    admitted_at: str,
) -> str:
    return currentness_index_digest(
        scope_ref=scope_ref,
        entries=[entry.reduced() for entry in entries],
        attestations=[attestation.as_record() for attestation in attestations],
        admitted_at=admitted_at,
    )


def _require_bytes_identity(payload: bytes, expected_sha256: str, label: str) -> str:
    observed = persisted_file_sha256(payload)
    if not digests_equal(observed, expected_sha256):
        raise CurrentnessIndexError(
            f"{label} byte identity mismatch: expected {strip_digest_prefix(expected_sha256)}, "
            f"observed {observed}"
        )
    return observed


def historical_artifact_from_frozen_draft(draft: Mapping[str, Any]) -> dict[str, Any]:
    """Wrap a frozen RUN-001 draft as a historical artifact, unchanged.

    The draft mapping becomes the digest body verbatim.  Nothing is added to it,
    because the byte-preservation claim rests on this digest.
    """
    return {
        "body": dict(draft),
        "historical_state": draft.get("eligibility_state"),
    }


def _governed_controlling_output_refs(correction_result: Mapping[str, Any]) -> frozenset[str]:
    refs = correction_result.get("affected_output_refs", [])
    return frozenset(str(ref) for ref in refs) if isinstance(refs, list) else frozenset()


def build_currentness_index(
    *,
    scope_ref: str,
    stage_2_raw_result_bytes: bytes,
    expected_stage_2_sha256: str,
    correction_result_bytes: bytes,
    expected_correction_sha256: str,
    observed_at: str,
    admitted_at: str,
    synthetic_control_bytes: bytes | None = None,
    expected_synthetic_control_sha256: str | None = None,
) -> CurrentnessIndex:
    """Admit governed institutional state, and only governed state.

    Both frozen inputs must match the byte identities the caller declares, so the
    index cannot be built over substituted evidence.  The synthetic control enters
    only through its own named parameter — the separately identified
    synthetic-control path — and never as an ordinary entry.
    """
    stage_2_identity = _require_bytes_identity(
        stage_2_raw_result_bytes, expected_stage_2_sha256, "stage-2 raw result"
    )
    correction_identity = _require_bytes_identity(
        correction_result_bytes, expected_correction_sha256, "correction successor result"
    )
    stage_2 = json.loads(stage_2_raw_result_bytes.decode("utf-8"))
    correction = json.loads(correction_result_bytes.decode("utf-8"))

    parse_utc(observed_at)
    parse_utc(admitted_at)
    if parse_utc(observed_at) > parse_utc(admitted_at):
        raise CurrentnessIndexError("observed_at must not follow admitted_at")

    drafts = stage_2.get("drafts")
    if not isinstance(drafts, list):
        raise CurrentnessIndexError("stage-2 evidence carries no drafts array")

    entries: list[IndexEntry] = []
    for draft in drafts:
        output_ref = str(draft["draft_id"])
        identity_record = {
            "output_ref": output_ref,
            "historical_artifact_digest": historical_artifact_digest(draft),
            "historical_state": draft.get("eligibility_state"),
            "source": "FROZEN_STAGE_2_RAW_RESULT",
        }
        entries.append(
            IndexEntry(
                output_ref=output_ref,
                record_ref=f"ARTIFACT-IDENTITY#{output_ref}",
                record_class=HISTORICAL_ARTIFACT_IDENTITY_RECORD,
                record_digest=basis_record_digest(identity_record),
                effective_at=None,
                admitted_at=admitted_at,
                record=identity_record,
            )
        )

    successor = correction.get("successor", {})
    supersession = correction.get("predecessor_supersession_record", {})
    instruction = correction.get("correction_instruction", {})
    superseded_at = str(supersession.get("superseded_at_utc"))
    parse_utc(superseded_at)
    for output_ref in _governed_controlling_output_refs(correction):
        record = {
            "output_ref": output_ref,
            "record_class": SUPERSESSION_RECORD,
            "predecessor_id": supersession.get("predecessor_id"),
            "predecessor_candidate_id": supersession.get("predecessor_candidate_id"),
            "predecessor_digest": supersession.get("predecessor_digest"),
            "successor_id": successor.get("successor_id"),
            "correction_event_id": successor.get("correction_event_id"),
            "superseded_at_utc": superseded_at,
            "correction_instruction_sha256": instruction.get("correction_instruction_sha256"),
            "correction_result_sha256": correction_identity,
        }
        entries.append(
            IndexEntry(
                output_ref=output_ref,
                record_ref=f"{successor.get('successor_id')}#{output_ref}",
                record_class=SUPERSESSION_RECORD,
                record_digest=basis_record_digest(record),
                effective_at=superseded_at,
                admitted_at=admitted_at,
                record=record,
            )
        )

    for determination in correction.get("affected_output_eligibility", []):
        output_ref = str(determination["draft_id"])
        if determination.get("correction_impact") != "AFFECTED_BY_SUPERSESSION":
            continue
        record = {
            "output_ref": output_ref,
            "record_class": ELIGIBILITY_DETERMINATION_RECORD,
            "post_correction_reliance_state": determination.get("post_correction_reliance_state"),
            "pre_correction_frozen_eligibility": determination.get(
                "pre_correction_frozen_eligibility"
            ),
            "determination_class": determination.get("determination_class"),
            "basis": determination.get("basis"),
            "correction_result_sha256": correction_identity,
        }
        entries.append(
            IndexEntry(
                output_ref=output_ref,
                record_ref=f"ELIGIBILITY#{output_ref}",
                record_class=ELIGIBILITY_DETERMINATION_RECORD,
                record_digest=basis_record_digest(record),
                effective_at=superseded_at,
                admitted_at=admitted_at,
                record=record,
            )
        )

    attestations: list[BasisCompletenessAttestation] = []
    if synthetic_control_bytes is not None:
        if expected_synthetic_control_sha256 is None:
            raise CurrentnessIndexError("synthetic control admitted without a declared identity")
        _require_bytes_identity(
            synthetic_control_bytes, expected_synthetic_control_sha256, "synthetic control"
        )
        control = json.loads(synthetic_control_bytes.decode("utf-8"))
        control_entry, control_attestation = _admit_synthetic_control(control, admitted_at)
        entries.append(control_entry)
        attestations.append(control_attestation)

    for entry in entries:
        if entry.record_class != HISTORICAL_ARTIFACT_IDENTITY_RECORD:
            continue
        if entry.record.get("fixture_class") == SYNTHETIC_UNAFFECTED_CONTROL and (
            entry.record.get("index_admission_path") != SYNTHETIC_CONTROL_PATH
        ):
            raise CurrentnessIndexError(
                "a synthetic-control fixture may enter only through the synthetic-control path"
            )

    ordered = tuple(entries)
    return CurrentnessIndex(
        scope_ref=scope_ref,
        entries=ordered,
        attestations=tuple(attestations),
        observed_at=observed_at,
        admitted_at=admitted_at,
        index_digest=_index_digest_of(scope_ref, ordered, attestations, admitted_at),
        basis_source_identities={
            "stage_2_raw_result_sha256": stage_2_identity,
            "correction_successor_result_sha256": correction_identity,
            "synthetic_control_sha256": (
                persisted_file_sha256(synthetic_control_bytes)
                if synthetic_control_bytes is not None
                else ""
            ),
        },
    )


def _admit_synthetic_control(
    control: Mapping[str, Any], admitted_at: str
) -> tuple[IndexEntry, BasisCompletenessAttestation]:
    """Admit the frozen fixture through its own path, isolated from real outputs."""
    if control.get("fixture_class") != SYNTHETIC_UNAFFECTED_CONTROL:
        raise CurrentnessIndexError("synthetic-control path used for a non-fixture artifact")
    if control.get("derived_from_real_mission_001_output") is not False:
        raise CurrentnessIndexError("synthetic control must declare no real-output derivation")
    if control.get("index_admission_path") != SYNTHETIC_CONTROL_PATH:
        raise CurrentnessIndexError("synthetic control declares a foreign admission path")
    output_ref = str(control["output_ref"])
    artifact = control["historical_artifact"]
    identity_record = {
        "output_ref": output_ref,
        "historical_artifact_digest": historical_artifact_digest(artifact["body"]),
        "historical_state": artifact.get("historical_state"),
        "fixture_class": SYNTHETIC_UNAFFECTED_CONTROL,
        "index_admission_path": SYNTHETIC_CONTROL_PATH,
        "source": "FROZEN_SYNTHETIC_CONTROL",
    }
    entry = IndexEntry(
        output_ref=output_ref,
        record_ref=f"ARTIFACT-IDENTITY#{output_ref}",
        record_class=HISTORICAL_ARTIFACT_IDENTITY_RECORD,
        record_digest=basis_record_digest(identity_record),
        effective_at=None,
        admitted_at=admitted_at,
        record=identity_record,
    )
    attestation = parse_basis_completeness_attestation(
        control["basis_completeness_attestation"], admission_path=SYNTHETIC_CONTROL_PATH
    )
    if attestation.covered_output_ref != output_ref:
        raise CurrentnessIndexError("synthetic control attestation covers a different output")
    return entry, attestation


def derive_index_variant(
    index: CurrentnessIndex,
    *,
    entries: Sequence[IndexEntry] | None = None,
    attestations: Sequence[BasisCompletenessAttestation] | None = None,
    governed_controlling_output_refs: Iterable[str] = (),
) -> CurrentnessIndex:
    """Produce a re-identified index variant, re-running admission guards.

    Used to construct adversarial states.  An attestation for an output the
    governed source knows to carry a controlling record is refused admission: a
    complete-basis claim cannot be manufactured by withholding the record it
    would have had to cover.
    """
    new_entries = tuple(index.entries if entries is None else entries)
    new_attestations = tuple(index.attestations if attestations is None else attestations)
    governed = frozenset(str(ref) for ref in governed_controlling_output_refs)
    for attestation in new_attestations:
        if attestation.admission_path == SYNTHETIC_CONTROL_PATH:
            if attestation.fixture_class != SYNTHETIC_UNAFFECTED_CONTROL:
                raise CurrentnessIndexError(
                    "synthetic-control admission path used by a non-fixture attestation"
                )
            continue
        if attestation.covered_output_ref in governed:
            raise CurrentnessIndexError(
                "completeness attestation refused: the governed source holds a controlling "
                f"record for {attestation.covered_output_ref}"
            )
    return CurrentnessIndex(
        scope_ref=index.scope_ref,
        entries=new_entries,
        attestations=new_attestations,
        observed_at=index.observed_at,
        admitted_at=index.admitted_at,
        index_digest=_index_digest_of(
            index.scope_ref, new_entries, new_attestations, index.admitted_at
        ),
        basis_source_identities=dict(index.basis_source_identities),
    )


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class CurrentnessResolution:
    """A relation computed at an instant, never a property stored on anything."""

    output_ref: str
    historical_artifact_digest: str
    historical_state: Any
    currentness_state: str
    eligibility: str
    secondary_states: tuple[str, ...]
    controlling_successor_ref: str | None
    correction_event_ref: str | None
    competing_refs: tuple[str, ...]
    scheduled_supersession: Mapping[str, Any] | None
    basis_records: tuple[Mapping[str, Any], ...]
    reason_code_id: str
    reason_code: str
    times: Mapping[str, Any]
    index_digest: str
    resolution_digest: str

    def as_record(self) -> dict[str, Any]:
        """The closed 19-field serialized form that the digest is taken over."""
        return {
            "record_class": "CDC_CURRENTNESS_RESOLUTION",
            "schema_version": RESOLUTION_SCHEMA_VERSION,
            "output_ref": self.output_ref,
            "historical_artifact_digest": self.historical_artifact_digest,
            "historical_state": self.historical_state,
            "currentness_state": self.currentness_state,
            "eligibility": self.eligibility,
            "secondary_states": list(self.secondary_states),
            "controlling_successor_ref": self.controlling_successor_ref,
            "correction_event_ref": self.correction_event_ref,
            "competing_refs": list(self.competing_refs),
            "scheduled_supersession": (
                None if self.scheduled_supersession is None else dict(self.scheduled_supersession)
            ),
            "basis_records": [dict(record) for record in self.basis_records],
            "reason_code_id": self.reason_code_id,
            "reason_code": self.reason_code,
            "times": dict(self.times),
            "index_digest": self.index_digest,
            "assurance_class": ASSURANCE_CLASS,
            "resolution_digest": self.resolution_digest,
        }


def _eligibility_for(state: str) -> str:
    if state == CURRENT:
        return ELIGIBLE_SUBJECT_TO_FURTHER_GATES
    if state == UNKNOWN:
        return ELIGIBILITY_UNDETERMINED
    return NOT_ELIGIBLE_FOR_PRESENT_USE


def _build_resolution(
    *,
    output_ref: str,
    artifact_digest: str,
    historical_state: object,
    state: str,
    reason_code_id: str,
    index: CurrentnessIndex,
    evaluated_at: str,
    ttl_seconds: int,
    secondary_states: Sequence[str] = (),
    controlling_successor_ref: str | None = None,
    correction_event_ref: str | None = None,
    competing_refs: Sequence[str] = (),
    scheduled_supersession: Mapping[str, Any] | None = None,
    basis_records: Sequence[Mapping[str, Any]] = (),
    effective_at: str | None = None,
) -> CurrentnessResolution:
    if reason_code_id not in RESOLVER_REASON_CODES:
        raise CurrentnessIndexError(
            f"reason code outside the closed resolver set: {reason_code_id}"
        )
    expires_at = format_utc(parse_utc(evaluated_at) + timedelta(seconds=ttl_seconds))
    times = {
        "observed_at": index.observed_at,
        "admitted_at": index.admitted_at,
        "evaluated_at": evaluated_at,
        "expires_at": expires_at,
        "effective_at": effective_at,
    }
    resolution = CurrentnessResolution(
        output_ref=output_ref,
        historical_artifact_digest=artifact_digest,
        historical_state=historical_state,
        currentness_state=state,
        eligibility=_eligibility_for(state),
        secondary_states=tuple(sorted(set(secondary_states))),
        controlling_successor_ref=controlling_successor_ref,
        correction_event_ref=correction_event_ref,
        competing_refs=tuple(competing_refs),
        scheduled_supersession=scheduled_supersession,
        basis_records=tuple(basis_records),
        reason_code_id=reason_code_id,
        reason_code=RESOLVER_REASON_CODES[reason_code_id],
        times=times,
        index_digest=index.index_digest,
        resolution_digest="",
    )
    record = resolution.as_record()
    return CurrentnessResolution(
        output_ref=resolution.output_ref,
        historical_artifact_digest=resolution.historical_artifact_digest,
        historical_state=resolution.historical_state,
        currentness_state=resolution.currentness_state,
        eligibility=resolution.eligibility,
        secondary_states=resolution.secondary_states,
        controlling_successor_ref=resolution.controlling_successor_ref,
        correction_event_ref=resolution.correction_event_ref,
        competing_refs=resolution.competing_refs,
        scheduled_supersession=resolution.scheduled_supersession,
        basis_records=resolution.basis_records,
        reason_code_id=resolution.reason_code_id,
        reason_code=resolution.reason_code,
        times=resolution.times,
        index_digest=resolution.index_digest,
        resolution_digest=resolution_digest(record),
    )


def _basis_pointer(entry: IndexEntry) -> dict[str, Any]:
    return {
        "record_ref": entry.record_ref,
        "record_class": entry.record_class,
        "record_digest": entry.record_digest,
        "effective_at": entry.effective_at,
        "admitted_at": entry.admitted_at,
    }


def resolve_currentness(
    *,
    output_ref: str,
    historical_artifact: Mapping[str, Any],
    index: CurrentnessIndex,
    evaluated_at: str,
    ttl_seconds: int = DEFAULT_RESOLUTION_TTL_SECONDS,
    asserted_controlling_record: Mapping[str, Any] | None = None,
) -> CurrentnessResolution:
    """Resolve currentness from governed state alone.

    There is no parameter through which a caller can assert ``CURRENT``.
    ``asserted_controlling_record`` lets a caller nominate a controlling record,
    which can only ever produce a refusal or be ignored — never currency.
    """
    body = historical_artifact.get("body")
    if not isinstance(body, Mapping):
        raise CurrentnessGateError("historical artifact carries no body object")
    observed_digest = historical_artifact_digest(body)
    historical_state = historical_artifact.get("historical_state")

    entries = index.entries_for(output_ref)
    identity_entries = [
        entry for entry in entries if entry.record_class == HISTORICAL_ARTIFACT_IDENTITY_RECORD
    ]
    resolve = partial(
        _build_resolution,
        output_ref=output_ref,
        artifact_digest=observed_digest,
        historical_state=historical_state,
        index=index,
        evaluated_at=evaluated_at,
        ttl_seconds=ttl_seconds,
    )

    declared_id = body.get("draft_id")
    if declared_id is not None and str(declared_id) != output_ref:
        return resolve(state=UNKNOWN, reason_code_id="R10")
    for entry in identity_entries:
        expected = str(entry.record["historical_artifact_digest"])
        if not digests_equal(expected, observed_digest):
            return resolve(
                state=UNKNOWN, reason_code_id="R10", basis_records=[_basis_pointer(entry)]
            )

    if asserted_controlling_record is not None:
        asserted_output = str(asserted_controlling_record.get("output_ref", ""))
        if asserted_output != output_ref:
            return resolve(
                state=UNKNOWN,
                reason_code_id="R8",
                controlling_successor_ref=asserted_controlling_record.get("successor_id"),
            )
        known = {entry.record_digest for entry in entries}
        if basis_record_digest(asserted_controlling_record) not in known:
            return resolve(
                state=UNKNOWN,
                reason_code_id="R9",
                controlling_successor_ref=asserted_controlling_record.get("successor_id"),
            )

    if not index.covers(output_ref):
        return resolve(state=UNKNOWN, reason_code_id="R5")

    now = parse_utc(evaluated_at)
    supersessions = [
        entry
        for entry in entries
        if entry.record_class in (SUPERSESSION_RECORD, CORRECTION_SUCCESSOR_RECORD)
    ]
    for entry in supersessions:
        predecessor = entry.record.get("predecessor_candidate_id")
        provenance = body.get("provenance")
        refs = provenance.get("candidate_refs", []) if isinstance(provenance, Mapping) else []
        if predecessor is not None and isinstance(refs, list) and refs and predecessor not in refs:
            return resolve(
                state=UNKNOWN,
                reason_code_id="R9",
                controlling_successor_ref=entry.record.get("successor_id"),
                basis_records=[_basis_pointer(entry)],
            )

    operative = [
        entry
        for entry in supersessions
        if entry.effective_at is not None and parse_utc(entry.effective_at) <= now
    ]
    scheduled = [
        entry
        for entry in supersessions
        if entry.effective_at is not None and parse_utc(entry.effective_at) > now
    ]

    distinct = {str(entry.record.get("successor_id")) for entry in operative}
    if len(distinct) > 1:
        return resolve(
            state=UNKNOWN,
            reason_code_id="R7",
            competing_refs=sorted(entry.record_ref for entry in operative),
            basis_records=[_basis_pointer(entry) for entry in operative],
        )

    eligibility_entries = [
        entry
        for entry in entries
        if entry.record_class == ELIGIBILITY_DETERMINATION_RECORD
        and entry.effective_at is not None
        and parse_utc(entry.effective_at) <= now
    ]

    if operative:
        entry = operative[0]
        also_ineligible = [ELIGIBILITY_DETERMINATION_ALSO_PRESENT] if eligibility_entries else []
        return resolve(
            state=SUPERSEDED,
            reason_code_id="R2",
            controlling_successor_ref=str(entry.record.get("successor_id")),
            correction_event_ref=str(entry.record.get("correction_event_id")),
            secondary_states=also_ineligible,
            basis_records=[_basis_pointer(item) for item in (entry, *eligibility_entries)],
            effective_at=entry.effective_at,
        )

    if eligibility_entries:
        entry = eligibility_entries[0]
        return resolve(
            state=INELIGIBLE,
            reason_code_id="R3",
            basis_records=[_basis_pointer(entry)],
            effective_at=entry.effective_at,
        )

    # No operative controlling record.  CURRENT is now a positive claim and needs
    # affirmative completeness evidence; not-found is not complete absence.
    attestation = index.attestation_for(output_ref)
    if attestation is None:
        return resolve(state=UNKNOWN, reason_code_id="R5")
    if attestation.scope_ref not in output_ref and not output_ref.startswith(attestation.scope_ref):
        return resolve(state=UNKNOWN, reason_code_id="R6")
    if not digests_equal(completeness_digest(attestation.source), attestation.completeness_digest):
        return resolve(state=UNKNOWN, reason_code_id="R6")
    if parse_utc(attestation.admitted_at) > now:
        return resolve(state=UNKNOWN, reason_code_id="R5")
    if parse_utc(attestation.completeness_as_of) > now:
        return resolve(state=UNKNOWN, reason_code_id="R6")
    uncovered = sorted(
        {
            entry.record_class
            for entry in entries
            if entry.record_class in CONTROLLING_RECORD_CLASSES
        }
        - set(attestation.record_kinds_covered)
    )
    if uncovered:
        return resolve(state=UNKNOWN, reason_code_id="R4")
    for entry in entries:
        if entry.record_class in CONTROLLING_RECORD_CLASSES and parse_utc(
            entry.admitted_at
        ) > parse_utc(attestation.admitted_at):
            return resolve(state=UNKNOWN, reason_code_id="R4")

    secondary: list[str] = []
    scheduled_record: dict[str, Any] | None = None
    if scheduled:
        entry = scheduled[0]
        secondary.append(FUTURE_SUPERSESSION_SCHEDULED)
        scheduled_record = {
            "successor_ref": str(entry.record.get("successor_id")),
            "effective_at": entry.effective_at,
            "set_aside_reason_code_id": "R11",
            "set_aside_reason_code": RESOLVER_REASON_CODES["R11"],
        }
    return resolve(
        state=CURRENT,
        reason_code_id="R1",
        secondary_states=secondary,
        scheduled_supersession=scheduled_record,
        basis_records=[
            {
                "record_ref": f"ATTESTATION#{attestation.covered_output_ref}",
                "record_class": "BASIS_COMPLETENESS_ATTESTATION",
                "record_digest": attestation.completeness_digest,
                "effective_at": attestation.completeness_as_of,
                "admitted_at": attestation.admitted_at,
            }
        ],
    )


def current_requires_attested_complete_basis(
    resolution: CurrentnessResolution, index: CurrentnessIndex
) -> bool:
    """The structural implication CURRENT ⇒ verified attested complete basis.

    Stated as a checkable predicate rather than a comment so the invariant can be
    asserted directly against any resolution the resolver produces.
    """
    if resolution.currentness_state != CURRENT:
        return True
    attestation = index.attestation_for(resolution.output_ref)
    return (
        attestation is not None
        and digests_equal(completeness_digest(attestation.source), attestation.completeness_digest)
        and resolution.reason_code_id == "R1"
    )


# ---------------------------------------------------------------------------
# Present-use gate
# ---------------------------------------------------------------------------

REQUIRED_RUN_METADATA: Final = (
    "run_id",
    "trace_id",
    "producer",
    "producer_version",
    "occurred_at",
    "recorded_at",
)


@dataclass(frozen=True, slots=True, eq=False)
class UseGateProfile:
    """Bounded profile, frozen before execution.  UNKNOWN denies, always."""

    profile_id: str = "CDC-CURRENTNESS-USE-PROFILE-001"
    unknown_disposition: str = DENY
    max_resolution_age_seconds: int = DEFAULT_RESOLUTION_TTL_SECONDS
    next_gate_on_current: str = "AUTHORITY_AND_ADMISSIBILITY_GATE"

    def __post_init__(self) -> None:
        if self.unknown_disposition != DENY:
            raise CurrentnessGateError("UNKNOWN_DISPOSITION is fixed to DENY for this slice")


@dataclass(frozen=True, slots=True, eq=False)
class UseGateRequest:
    """A request to use a historical output in a new present operation."""

    output_ref: str
    requested_use: str
    requested_operation_class: str
    consequential: bool
    requesting_scope_ref: str
    requested_at: str
    expected_index_digest: str | None = None
    precomputed_resolution: Mapping[str, Any] | None = None
    asserted_currentness_state: str | None = None
    asserted_controlling_record: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True, eq=False)
class UseGateDecision:
    """The gate's output.  PROCEED is a pointer to the next gate, not consent."""

    decision: str
    reason_code_id: str
    reason_code: str
    output_ref: str
    currentness_state: str
    controlling_successor_ref: str | None
    controlling_evidence_pointer: Mapping[str, Any] | None
    next_gate: str | None
    resolution_digest: str
    artifact_observed_digest: str
    index_digest: str
    times: Mapping[str, Any]
    run_metadata: Mapping[str, Any]
    use_gate_decision_digest: str

    def as_record(self) -> dict[str, Any]:
        """The serialized decision; its digest binds resolution and artifact."""
        return {
            "record_class": "CDC_CURRENTNESS_USE_GATE_DECISION",
            "schema_version": USE_GATE_DECISION_SCHEMA_VERSION,
            "decision": self.decision,
            "reason_code_id": self.reason_code_id,
            "reason_code": self.reason_code,
            "output_ref": self.output_ref,
            "currentness_state": self.currentness_state,
            "controlling_successor_ref": self.controlling_successor_ref,
            "controlling_evidence_pointer": (
                None
                if self.controlling_evidence_pointer is None
                else dict(self.controlling_evidence_pointer)
            ),
            "next_gate": self.next_gate,
            "resolution_digest": self.resolution_digest,
            "artifact_observed_digest": self.artifact_observed_digest,
            "index_digest": self.index_digest,
            "times": dict(self.times),
            "run_metadata": dict(self.run_metadata),
            "consequential_gate_reached": self.decision == PROCEED,
            "assurance_class": ASSURANCE_CLASS,
            "use_gate_decision_digest": self.use_gate_decision_digest,
        }


def _pointer_for(resolution: CurrentnessResolution) -> dict[str, Any] | None:
    if not resolution.basis_records:
        return None
    return {
        "successor_ref": resolution.controlling_successor_ref,
        "correction_event_ref": resolution.correction_event_ref,
        "basis_record_refs": [record["record_ref"] for record in resolution.basis_records],
        "basis_record_digests": [record["record_digest"] for record in resolution.basis_records],
        "resolution_digest": resolution.resolution_digest,
        "index_digest": resolution.index_digest,
    }


def _decide(
    *,
    reason_code_id: str,
    request: UseGateRequest,
    resolution: CurrentnessResolution,
    profile: UseGateProfile,
    run_metadata: Mapping[str, Any],
    decided_at: str,
) -> UseGateDecision:
    if reason_code_id not in USE_GATE_REASON_CODES:
        raise CurrentnessGateError(f"reason code outside the closed gate set: {reason_code_id}")
    proceed = reason_code_id == "G1"
    decision = UseGateDecision(
        decision=PROCEED if proceed else DENY,
        reason_code_id=reason_code_id,
        reason_code=USE_GATE_REASON_CODES[reason_code_id],
        output_ref=request.output_ref,
        currentness_state=resolution.currentness_state,
        controlling_successor_ref=resolution.controlling_successor_ref,
        controlling_evidence_pointer=_pointer_for(resolution),
        next_gate=profile.next_gate_on_current if proceed else None,
        resolution_digest=resolution.resolution_digest,
        artifact_observed_digest=resolution.historical_artifact_digest,
        index_digest=resolution.index_digest,
        times={
            "requested_at": request.requested_at,
            "decided_at": decided_at,
            "evaluated_at": resolution.times["evaluated_at"],
        },
        run_metadata=dict(run_metadata),
        use_gate_decision_digest="",
    )
    record = decision.as_record()
    return UseGateDecision(
        decision=decision.decision,
        reason_code_id=decision.reason_code_id,
        reason_code=decision.reason_code,
        output_ref=decision.output_ref,
        currentness_state=decision.currentness_state,
        controlling_successor_ref=decision.controlling_successor_ref,
        controlling_evidence_pointer=decision.controlling_evidence_pointer,
        next_gate=decision.next_gate,
        resolution_digest=decision.resolution_digest,
        artifact_observed_digest=decision.artifact_observed_digest,
        index_digest=decision.index_digest,
        times=decision.times,
        run_metadata=decision.run_metadata,
        use_gate_decision_digest=use_gate_decision_digest(record),
    )


def evaluate_present_use(
    *,
    request: UseGateRequest,
    historical_artifact: Mapping[str, Any],
    currentness_index: CurrentnessIndex,
    profile: UseGateProfile,
    run_metadata: Mapping[str, Any],
) -> UseGateDecision:
    """Refuse or pass a historical output through to the next gate.

    The gate derives currentness itself at ``request.requested_at``.  A supplied
    precomputed resolution is a performance hint only: it is checked against the
    governed resolution recomputed at the precomputed instant and must match
    exactly.  A caller-supplied currentness assertion is refused explicitly, so
    the attempt appears in evidence rather than being silently dropped.

    Incomplete run metadata raises instead of returning a decision — the gate
    reason-code set is closed and contains no code for it, and inventing one
    after the fact would be a criteria modification.
    """
    missing = sorted(set(REQUIRED_RUN_METADATA) - run_metadata.keys())
    if missing:
        raise CurrentnessGateError(f"run metadata incomplete: {missing}")

    resolution = resolve_currentness(
        output_ref=request.output_ref,
        historical_artifact=historical_artifact,
        index=currentness_index,
        evaluated_at=request.requested_at,
        ttl_seconds=profile.max_resolution_age_seconds,
        asserted_controlling_record=request.asserted_controlling_record,
    )
    decided_at = request.requested_at

    def decide(code: str) -> UseGateDecision:
        return _decide(
            reason_code_id=code,
            request=request,
            resolution=resolution,
            profile=profile,
            run_metadata=run_metadata,
            decided_at=decided_at,
        )

    if resolution.reason_code_id == "R10":
        return decide("G5")
    if request.expected_index_digest is not None and not digests_equal(
        request.expected_index_digest, currentness_index.index_digest
    ):
        return decide("G10")

    precomputed = request.precomputed_resolution
    if precomputed is not None:
        precomputed_times = precomputed.get("times", {})
        precomputed_evaluated_at = str(precomputed_times.get("evaluated_at", ""))
        if precomputed.get("output_ref") != request.output_ref or not digests_equal(
            str(precomputed.get("historical_artifact_digest", "")),
            resolution.historical_artifact_digest,
        ):
            return decide("G6")
        expected = resolve_currentness(
            output_ref=request.output_ref,
            historical_artifact=historical_artifact,
            index=currentness_index,
            evaluated_at=precomputed_evaluated_at,
            ttl_seconds=profile.max_resolution_age_seconds,
            asserted_controlling_record=request.asserted_controlling_record,
        )
        # Two independent equalities: the hint must be internally self-consistent
        # (its body must reproduce its own digest field, so a mutated body with a
        # stale digest cannot pass) and it must equal the governed recomputation.
        stored_digest = str(precomputed.get("resolution_digest", ""))
        if not digests_equal(stored_digest, resolution_digest(precomputed)):
            return decide("G9")
        if not digests_equal(stored_digest, expected.resolution_digest):
            return decide("G9")
        age = parse_utc(request.requested_at) - parse_utc(precomputed_evaluated_at)
        expires_at = precomputed_times.get("expires_at")
        expired = expires_at is not None and parse_utc(request.requested_at) > parse_utc(
            str(expires_at)
        )
        if age > timedelta(seconds=profile.max_resolution_age_seconds) or expired:
            return decide("G7")

    if request.asserted_currentness_state is not None:
        return decide("G8")

    if resolution.currentness_state == UNKNOWN:
        return decide("G4")
    if resolution.currentness_state == SUPERSEDED:
        return decide("G2")
    if resolution.currentness_state == INELIGIBLE:
        return decide("G3")
    return decide("G1")


CLAIM_CEILING_IF_MEASURED: Final[dict[str, str]] = {
    "EXECUTABLE_CURRENTNESS_RESOLUTION": "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION",
    "STALE_OUTPUT_PRESENT_USE_REFUSAL": "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION",
    "HISTORICAL_ARTIFACT_PRESERVATION_DURING_CURRENTNESS_CHANGE": (
        "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION"
    ),
}

NOT_ESTABLISHED: Final = (
    "real_unaffected_CDC_output_resolves_CURRENT",
    "consumer_bypass_resistance",
    "institutional_currentness_propagation",
    "institutional_reliance",
    "official_CDC_issuance",
    "legal_effect",
    "production_conformance",
    "CDC_acceptance",
    "general_rollback_resistance",
    "distributed_consistency_across_institutions",
)
