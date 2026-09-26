"""Release-source compatibility fixture for OpenAI Agents SDK 0.22.3.

This is NOT a vendored SDK and MUST NOT be represented as an installed/live SDK run.
It reproduces the exact export-relevant implementations from the signed release source:
- src/agents/tracing/spans.py SpanImpl.export()
- src/agents/tracing/span_data.py CustomSpanData.export()
- src/agents/tracing/span_data.py FunctionSpanData.export()

Release: openai-agents 0.22.3
Publishing commit: fdf21db62c303a3db54b0dfbee82de2141fa2799
Upstream Git blob SHA spans.py: 8f564beedb8354f14295868bae54a557b8883892
Upstream Git blob SHA span_data.py: 57b7fe6226c99aeb8a97544c49390b9b66961739
"""
from __future__ import annotations
from typing import Any

_SPAN_METADATA_ROUTING_KEYS = ("agent_harness_id",)


class CustomSpanData:
    __slots__ = ("name", "data")

    def __init__(self, name: str, data: dict[str, Any]):
        self.name = name
        self.data = data

    @property
    def type(self) -> str:
        return "custom"

    def export(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "data": self.data,
        }


class FunctionSpanData:
    __slots__ = ("name", "input", "output", "mcp_data")

    def __init__(
        self,
        name: str,
        input: str | None,
        output: Any | None,
        mcp_data: dict[str, Any] | None = None,
    ):
        self.name = name
        self.input = input
        self.output = output
        self.mcp_data = mcp_data

    @property
    def type(self) -> str:
        return "function"

    def export(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "input": self.input,
            "output": str(self.output) if self.output is not None else None,
            "mcp_data": self.mcp_data,
        }


class SpanImplExportFixture:
    """Export-relevant surface of upstream SpanImpl, with deterministic field injection.

    export() is copied verbatim in behavior from OpenAI Agents SDK 0.22.3 SpanImpl.export().
    Lifecycle/provider code is intentionally absent; therefore this class proves export-contract
    compatibility only and does not satisfy the installed/live-SDK freeze gate.
    """

    def __init__(
        self,
        *,
        trace_id: str,
        span_id: str,
        parent_id: str | None,
        started_at: str,
        ended_at: str,
        span_data: Any,
        error: dict[str, Any] | None = None,
        trace_metadata: dict[str, Any] | None = None,
    ):
        self._trace_id = trace_id
        self._span_id = span_id
        self._parent_id = parent_id
        self._started_at = started_at
        self._ended_at = ended_at
        self._span_data = span_data
        self._error = error
        self._trace_metadata = trace_metadata

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def span_id(self) -> str:
        return self._span_id

    @property
    def span_data(self):
        return self._span_data

    def export(self) -> dict[str, Any] | None:
        payload = {
            "object": "trace.span",
            "id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self._parent_id,
            "started_at": self._started_at,
            "ended_at": self._ended_at,
            "span_data": self.span_data.export(),
            "error": self._error,
        }
        metadata: dict[str, Any] = {}
        if self._trace_metadata is not None:
            metadata.update(
                {
                    key: self._trace_metadata[key]
                    for key in _SPAN_METADATA_ROUTING_KEYS
                    if key in self._trace_metadata
                }
            )
        span_data_metadata = getattr(self.span_data, "metadata", None)
        if isinstance(span_data_metadata, dict):
            metadata.update(
                {key: value for key, value in span_data_metadata.items() if key not in metadata}
            )
        if metadata:
            payload["metadata"] = metadata
        return payload
