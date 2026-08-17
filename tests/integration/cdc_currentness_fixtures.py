"""Read-only fixtures for currentness slice 001.

Every fixture is derived from already-frozen evidence opened for reading only:
the RUN-001 Stage-2 raw result, the RUN-002 correction-successor raw result, and
the frozen synthetic control imported byte-identically into the repository.

Nothing here writes, and nothing here imports the RUN-002 execution harness or
any result-bearing Mission-001 route.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from oic.cdc_currentness import (
    SYNTHETIC_CONTROL_PATH,
    CurrentnessIndex,
    build_currentness_index,
    historical_artifact_digest,
    historical_artifact_from_frozen_draft,
    persisted_file_sha256,
)

REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[2]
# The two frozen RUN results are read from an immutable in-repository fixture
# location rather than an absolute machine path, so the suite is reproducible from
# repository state alone.  The bytes and their pinned digests are unchanged.
CDC_EVIDENCE_FIXTURE_ROOT: Final = REPOSITORY_ROOT / "tests/fixtures/cdc-currentness-evidence"

STAGE_2_RAW_RESULT_PATH: Final = (
    CDC_EVIDENCE_FIXTURE_ROOT / "CDC-END-TO-END-MISSION-001-STAGE-2-RAW-RESULT-v0.1.json"
)
STAGE_2_RAW_RESULT_SHA256: Final = (
    "715a97038be184f5f0715a9e53d9ceb9150bf74b72e1ff2f4d27654c2b61d45d"
)

CORRECTION_RESULT_PATH: Final = (
    CDC_EVIDENCE_FIXTURE_ROOT
    / "CDC-END-TO-END-MISSION-001-M12-CORRECTION-SUCCESSOR-RUN-002-RAW-RESULT-v0.1.json"
)
CORRECTION_RESULT_SHA256: Final = (
    "8b81e62a1a5e65f14e86ced9f7b3c1f506f4dd4ccaa1c4375e4fb76d41fee246"
)
SYNTHETIC_CONTROL_PATH_ON_DISK: Final = (
    REPOSITORY_ROOT
    / "veraxis/currentness-slice-001"
    / "CDC-CURRENTNESS-SLICE-001-SYNTHETIC-UNAFFECTED-CONTROL-v0.1.json"
)
SYNTHETIC_CONTROL_SHA256: Final = (
    "2a9158e0561d3ab1886f3f4f52c0b828a76979aadccc66b58c95ccb84914a45d"
)
SEMANTIC_DESIGN_PATH: Final = (
    REPOSITORY_ROOT
    / "veraxis/currentness-slice-001/CURRENTNESS-PROPAGATION-SLICE-001-SEMANTIC-DESIGN-v0.2.md"
)
DIGEST_DERIVATION_PATH: Final = (
    REPOSITORY_ROOT
    / "veraxis/currentness-slice-001/CURRENTNESS-SLICE-001-DIGEST-DERIVATION-v0.1.md"
)

MISSION_SCOPE_REF: Final = "CDC-TEST-MISSION-001"
CONTROL_OUTPUT_REF: Final = "CDC-SYNTHETIC-UNAFFECTED-001/SYNTH-OUTPUT-01"
CONTROLLING_SUCCESSOR_ID: Final = "EBAWU-P-001-C-TENDER-01-CORR-002"
CORRECTION_EVENT_ID: Final = "CDC-E2E-M12-CORRECTION-EVT-002"
PREDECESSOR_CANDIDATE_ID: Final = "CAND-P-001-C-TENDER-01"
SUPERSEDED_AT: Final = "2026-08-14T18:10:54Z"

INDEX_OBSERVED_AT: Final = "2026-08-14T22:00:00Z"
INDEX_ADMITTED_AT: Final = "2026-08-14T22:00:00Z"
EVALUATED_AT: Final = "2026-08-14T22:05:00Z"

AFFECTED_OUTPUT_REFS: Final = (
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01",
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-02",
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-03",
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-04",
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-05",
)

# Measured from the frozen RUN-001 evidence before implementation began.  These
# are the byte-preservation anchors: if one of them moves, the slice's headline
# claim is false regardless of what any currentness record says.
FROZEN_ARTIFACT_DIGESTS: Final[dict[str, str]] = {
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01": (
        "239f0d675faeb7cf6b3e5cb879763800d36189f644d1c2623f921da3d10d497b"
    ),
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-02": (
        "66dd4f15c23fdbfeca27ece970b122c668a9c3a3180f0ee3ce80c85da901ee89"
    ),
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-03": (
        "a6f24f7171a80850b45ca3b73284ab35126e63d51018e9f4874959b5acc3f91c"
    ),
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-04": (
        "17595a4235f0860490c6ccfbccc91b682f6ea15da956eed08a8104394c10d8ff"
    ),
    "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-05": (
        "6d211ed3e283ff6bd28f0751d2bd6bcf1da9c6cb7b6d5f61206bdce29d410891"
    ),
}

RUN_METADATA: Final[dict[str, str]] = {
    "run_id": "CDC-CURRENTNESS-SLICE-001-DEVELOPMENT",
    "trace_id": "CDC-CURRENTNESS-SLICE-001-DEVELOPMENT-TRACE",
    "producer": "tests/integration/test_cdc_currentness_slice_001.py",
    "producer_version": "DEVELOPMENT_TEST_NOT_RESULT_BEARING",
    "occurred_at": EVALUATED_AT,
    "recorded_at": EVALUATED_AT,
}


def stage_2_bytes() -> bytes:
    """The frozen Stage-2 raw result, read without modification."""
    return STAGE_2_RAW_RESULT_PATH.read_bytes()


def correction_bytes() -> bytes:
    """The frozen RUN-002 correction-successor raw result, read-only."""
    return CORRECTION_RESULT_PATH.read_bytes()


def control_bytes() -> bytes:
    """The frozen synthetic control as imported into the repository."""
    return SYNTHETIC_CONTROL_PATH_ON_DISK.read_bytes()


# Snapshot taken at import, before any test runs, so the byte-preservation tests
# compare against something observed at the start of the session rather than
# against a value recomputed from whatever the file happens to say later.
SESSION_START_IDENTITIES: Final[dict[str, str]] = {
    "stage_2_file": persisted_file_sha256(stage_2_bytes()),
    "correction_file": persisted_file_sha256(correction_bytes()),
    "control_file": persisted_file_sha256(control_bytes()),
}
SESSION_START_ARTIFACT_DIGESTS: Final[dict[str, str]] = {
    str(draft["draft_id"]): historical_artifact_digest(draft)
    for draft in json.loads(stage_2_bytes().decode("utf-8"))["drafts"]
}


def frozen_drafts() -> dict[str, dict[str, Any]]:
    """Every frozen RUN-001 draft, keyed by its literal identifier."""
    payload = json.loads(stage_2_bytes().decode("utf-8"))
    return {str(draft["draft_id"]): draft for draft in payload["drafts"]}


def historical_artifact(output_ref: str) -> dict[str, Any]:
    """The historical artifact for a real frozen output."""
    return historical_artifact_from_frozen_draft(frozen_drafts()[output_ref])


def control_artifact() -> dict[str, Any]:
    """The synthetic control's historical artifact, wrapper stripped."""
    control = json.loads(control_bytes().decode("utf-8"))
    return dict(control["historical_artifact"])


def control_document() -> dict[str, Any]:
    """The whole frozen synthetic control document."""
    return json.loads(control_bytes().decode("utf-8"))


def governed_index(*, with_control: bool = True) -> CurrentnessIndex:
    """The index built from governed evidence only."""
    return build_currentness_index(
        scope_ref=MISSION_SCOPE_REF,
        stage_2_raw_result_bytes=stage_2_bytes(),
        expected_stage_2_sha256=STAGE_2_RAW_RESULT_SHA256,
        correction_result_bytes=correction_bytes(),
        expected_correction_sha256=CORRECTION_RESULT_SHA256,
        observed_at=INDEX_OBSERVED_AT,
        admitted_at=INDEX_ADMITTED_AT,
        synthetic_control_bytes=control_bytes() if with_control else None,
        expected_synthetic_control_sha256=(
            SYNTHETIC_CONTROL_SHA256 if with_control else None
        ),
    )


assert SYNTHETIC_CONTROL_PATH == "SYNTHETIC_CONTROL_PATH_ONLY"
