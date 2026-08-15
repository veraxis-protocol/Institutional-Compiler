"""The reliance consumer, run as its own process.

Its entire input is a job file of paths and instants.  It receives no
``CurrentnessIndex``, no resolution object and no producer state of any kind: it
opens the governed bytes itself, rebuilds its own index, re-resolves currentness
at its own instant and re-evaluates authority before it will consider issuing.

Invoked as::

    python -m tests.integration.cdc_integration_consumer <job.json>

It writes its result to the output path named in the job and prints that path.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.integration.cdc_currentness_fixtures import control_artifact  # noqa: E402
from tests.integration.cdc_integration_fixtures import (  # noqa: E402
    ARTIFACT_CLASS,
    control_body_digest,
    epoch_for,
    index_with_future_successor,
    index_without_control,
    index_without_successor,
)

from oic.cdc_authority import (  # noqa: E402
    AuthorityRequest,
    evaluate_synthetic_authority,
    parse_basis_record,
    parse_profile,
)
from oic.cdc_currentness import (  # noqa: E402
    CURRENT,
    UseGateProfile,
    resolve_currentness,
)
from oic.cdc_propagation import read_materialized_envelope  # noqa: E402
from oic.cdc_reliance import (  # noqa: E402
    ConsumerContext,
    RelianceContractError,
    ReResolvedCurrentness,
    claim_issuance_attempt,
    issue_reliance,
    persisted_file_sha256,
    run_consumer_validation,
)


def main(job_path: Path) -> Path:
    """Validate an envelope read from disk and record the reliance outcome."""
    job: dict[str, Any] = json.loads(job_path.read_bytes().decode("utf-8"))
    now = str(job["now"])
    envelope_bytes = read_materialized_envelope(Path(job["envelope_path"]))
    decision = json.loads(Path(job["propagated_decision_path"]).read_bytes().decode("utf-8"))
    producer = parse_profile(
        json.loads(Path(job["producer_profile_path"]).read_bytes().decode("utf-8"))
    )
    consumer = parse_profile(
        json.loads(Path(job["consumer_profile_path"]).read_bytes().decode("utf-8"))
    )
    authority_bases = [
        parse_basis_record(item)
        for item in json.loads(Path(job["authority_bases_path"]).read_bytes().decode("utf-8"))
    ]
    admissibility_bases = [
        parse_basis_record(item)
        for item in json.loads(
            Path(job["admissibility_bases_path"]).read_bytes().decode("utf-8")
        )
    ]

    # The consumer builds its own index from governed bytes it reads itself.
    if job.get("without_control"):
        index = index_without_control()
    elif job.get("with_future_successor"):
        index = index_with_future_successor()
    else:
        index = index_without_successor()
    artifact = control_artifact()

    def recompute_artifact_digest(artifact_ref: str) -> str | None:
        if artifact_ref != job["expected_artifact_ref"]:
            return None
        return control_body_digest()

    def resolve_evidence_ref(ref: Any) -> bool:  # noqa: ANN401
        path = ref.get("path") if isinstance(ref, dict) else None
        return bool(path) and Path(str(path)).is_file()

    def re_resolve(artifact_ref: str, moment: str) -> ReResolvedCurrentness:
        resolution = resolve_currentness(
            output_ref=artifact_ref,
            historical_artifact=artifact,
            index=index,
            evaluated_at=moment,
            ttl_seconds=UseGateProfile().max_resolution_age_seconds,
        )
        return ReResolvedCurrentness(
            currentness_state=resolution.currentness_state,
            resolution_digest=resolution.resolution_digest,
            epoch_digest=epoch_for(index, artifact_ref, moment),
            basis_reachable=index.covers(artifact_ref),
        )

    def re_evaluate(artifact_ref: str, moment: str, re_resolved: ReResolvedCurrentness) -> Any:  # noqa: ANN401
        return evaluate_synthetic_authority(
            request=AuthorityRequest(
                artifact_ref=artifact_ref,
                artifact_digest=control_body_digest(),
                recomputed_artifact_digest=control_body_digest(),
                requested_use=str(job["expected_requested_use"]),
                scope=str(job["expected_scope"]),
                requesting_principal=str(job["expected_subject_principal"]),
                currentness_resolution_digest=re_resolved.resolution_digest,
                currentness_epoch_digest=re_resolved.epoch_digest,
                evaluation_time=moment,
                valid_until=str(job["decision_valid_until"]),
                decision_id=f"{job['reliance_id']}-RELIANCE-TIME-AUTHORITY",
            ),
            authority_bases=authority_bases,
            admissibility_bases=admissibility_bases,
            artifact_class=ARTIFACT_CLASS,
        )

    context = ConsumerContext(
        consumer_profile=consumer,
        producer_profile=producer,
        consumer_identity={
            "consumer_principal": consumer.principal_id,
            "process_id": os.getpid(),
            "run_id": str(job["run_id"]),
            "trace_id": str(job["trace_id"]),
        },
        now=now,
        expected_scope=str(job["expected_scope"]),
        expected_requested_use=str(job["expected_requested_use"]),
        expected_subject_principal=str(job["expected_subject_principal"]),
        recompute_artifact_digest=recompute_artifact_digest,
        resolve_evidence_ref=resolve_evidence_ref,
        re_resolve_currentness=re_resolve,
        re_evaluate_authority=re_evaluate,
    )

    outcome = run_consumer_validation(
        envelope_bytes=envelope_bytes, propagated_decision=decision, context=context
    )

    direct = bool(job.get("direct_assertion_attempted"))
    already_consumed = False
    attempt: dict[str, Any] | None = None
    authorization_path = Path(job["authorization_path"])
    try:
        attempt = claim_issuance_attempt(
            authorization_path=authorization_path,
            attempt_path=Path(job["attempt_path"]),
            run_id=str(job["run_id"]),
            trace_id=str(job["trace_id"]),
            claimed_at=now,
        )
    except RelianceContractError:
        already_consumed = True

    authorization_digest = persisted_file_sha256(authorization_path.read_bytes())
    reliance = issue_reliance(
        reliance_id=str(job["reliance_id"]),
        validation_outcome=outcome,
        propagated_decision=decision,
        context=context,
        issuance_authorization_digest=authorization_digest,
        attempt_record_digest=(
            "" if attempt is None else str(attempt["attempt_record_digest"])
        ),
        evidence_refs=outcome["envelope_record"].get("evidence_refs", []),
        issued_at=now,
        direct_assertion_attempted=direct,
        authorization_already_consumed=already_consumed,
    )

    result = {
        "record_class": "CDC_INTEGRATION_SLICE_001_CONSUMER_RESULT",
        "consumer_process_id": os.getpid(),
        "consumer_principal": consumer.principal_id,
        "consumer_inputs_were_paths_only": True,
        "consumer_input_paths": sorted(
            str(job[key]) for key in job if key.endswith("_path") and key != "output_path"
        ),
        "producer_state_shared": False,
        "now": now,
        "validation": outcome["validation"],
        "gate_open": outcome["gate_open"],
        "reliance_record": reliance,
        "attempt": attempt,
        "issuance_authorization_digest": authorization_digest,
        "reliance_time_authority_decision": (
            None
            if outcome["reliance_time_decision"] is None
            else outcome["reliance_time_decision"].as_record()
        ),
        "re_resolved_currentness_state": (
            None if outcome["re_resolved"] is None else outcome["re_resolved"].currentness_state
        ),
        "currentness_current_constant": CURRENT,
    }
    output_path = Path(job["output_path"])
    output_path.write_bytes(
        (json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    return output_path


if __name__ == "__main__":
    print(main(Path(sys.argv[1])))
