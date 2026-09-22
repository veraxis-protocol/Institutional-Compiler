from __future__ import annotations

from dataclasses import dataclass

from .errors import TraceNotAdmissible
from .models import CanonicalEvent, EventKind, ParsedTrace


@dataclass(frozen=True)
class ClaimSnapshot:
    claim: CanonicalEvent
    evidence_at_claim: tuple[CanonicalEvent, ...]
    evidence_after_claim: tuple[CanonicalEvent, ...]


def reconstruct_claim_snapshot(trace: ParsedTrace) -> ClaimSnapshot:
    """Reconstruct the H1 point-in-time evidence partition.

    event_seq is only host-local causal ordering of VEIP observation markers.
    observed_at is the host-recorded time. Both must place an evidence marker no
    later than the user-claim marker before it is admitted to E_claim.
    """
    claims = [e for e in trace.events if e.kind is EventKind.USER_CLAIM]
    if len(claims) != 1:
        raise TraceNotAdmissible(
            "H1 requires exactly one explicit veip.user_claim_emitted event"
        )

    requests = [e for e in trace.events if e.kind is EventKind.USER_REQUEST]
    if len(requests) != 1:
        raise TraceNotAdmissible(
            "H1 requires exactly one explicit veip.user_request_received event"
        )

    claim = claims[0]
    request = requests[0]
    if claim.event_seq is None or request.event_seq is None:
        raise TraceNotAdmissible("VEIP boundary markers require event_seq")
    if request.event_seq >= claim.event_seq:
        raise TraceNotAdmissible("user request marker must causally precede user claim marker")
    if request.observed_at > claim.observed_at:
        raise TraceNotAdmissible("user request timestamp must not be after user claim timestamp")

    evidence = [e for e in trace.events if e.kind is EventKind.EVIDENCE_AVAILABLE]
    before: list[CanonicalEvent] = []
    after: list[CanonicalEvent] = []

    for event in evidence:
        if event.event_seq is None:
            raise TraceNotAdmissible(f"evidence {event.event_id} lacks event_seq")
        if event.agent_visible is not True:
            raise TraceNotAdmissible(f"evidence {event.event_id} is not explicitly agent-visible")

        if event.event_seq <= claim.event_seq and event.observed_at <= claim.observed_at:
            before.append(event)
        else:
            after.append(event)

    before.sort(key=lambda e: (e.event_seq, e.source_ref.record_index))
    after.sort(key=lambda e: (e.event_seq, e.source_ref.record_index))

    return ClaimSnapshot(
        claim=claim,
        evidence_at_claim=tuple(before),
        evidence_after_claim=tuple(after),
    )
