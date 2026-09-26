from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class EventKind(str, Enum):
    USER_REQUEST = "user_request"
    EVIDENCE_AVAILABLE = "evidence_available"
    USER_CLAIM = "user_claim"
    INDEPENDENT_STATE = "independent_state"
    NATIVE_SPAN = "native_span"


@dataclass(frozen=True)
class SourceRef:
    source_file_sha256: str
    raw_record_sha256: str
    record_index: int
    native_id: str | None


@dataclass(frozen=True)
class CanonicalEvent:
    event_id: str
    trace_id: str
    event_seq: int | None
    kind: EventKind
    observed_at: datetime
    source_system: str
    agent_visible: bool
    payload: dict[str, Any]
    source_ref: SourceRef


@dataclass(frozen=True)
class ParsedTrace:
    trace_id: str
    events: tuple[CanonicalEvent, ...]
    source_file_sha256: str
    source_format: str = "OPENAI_AGENTS_SPAN_EXPORT_JSONL_V1"
