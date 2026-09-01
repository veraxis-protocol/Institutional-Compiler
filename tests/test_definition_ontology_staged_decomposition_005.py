from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = (
    ROOT
    / "scripts/characterize_definition_ontology_staged_decomposition_005.py"
)


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_ontology005_test_module",
        SCRIPT,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[spec.name] = module

    try:
        spec.loader.exec_module(
            module
        )
    finally:
        sys.modules.pop(
            spec.name,
            None,
        )

    return module


def request(mod: Any) -> Any:
    return mod.ModelRequest(
        system_prompt="system",
        user_prompt="user",
        response_format={
            "type": "json_object",
        },
        temperature=0.0,
        max_tokens=100,
    )


def response(mod: Any) -> Any:
    return mod.ModelResponse(
        provider="fake-provider",
        model="fake-model",
        content='{"ok":true}',
        request_id="fake-request",
        raw={},
    )


def projection_sha(
    mod: Any,
    req: Any,
) -> str:
    provider = (
        mod.TransportRecoveringProvider(
            delegate=None,
            semantic_ordinal=1,
            expected_request_sha256="unused",
            sleep_fn=lambda _: None,
        )
    )

    return provider._projection_sha(
        req
    )


class SuccessProvider:
    def __init__(
        self,
        result: Any,
    ) -> None:
        self.result = result
        self.calls: list[Any] = []

    def complete(
        self,
        req: Any,
    ) -> Any:
        self.calls.append(
            req
        )

        return self.result


class TimeoutThenSuccessProvider:
    def __init__(
        self,
        mod: Any,
        result: Any,
    ) -> None:
        self.mod = mod
        self.result = result
        self.calls: list[Any] = []

    def complete(
        self,
        req: Any,
    ) -> Any:
        self.calls.append(
            req
        )

        if len(self.calls) == 1:
            raise self.mod.ModelProviderError(
                self.mod.ELIGIBLE_TIMEOUT
            )

        return self.result


class AlwaysTimeoutProvider:
    def __init__(
        self,
        mod: Any,
    ) -> None:
        self.mod = mod
        self.calls: list[Any] = []

    def complete(
        self,
        req: Any,
    ) -> Any:
        self.calls.append(
            req
        )

        raise self.mod.ModelProviderError(
            self.mod.ELIGIBLE_TIMEOUT
        )


class OtherErrorProvider:
    def __init__(
        self,
        mod: Any,
    ) -> None:
        self.mod = mod
        self.calls: list[Any] = []

    def complete(
        self,
        req: Any,
    ) -> Any:
        self.calls.append(
            req
        )

        raise self.mod.ModelProviderError(
            "some other provider failure"
        )


def test_005_materialization_is_exact_004_semantic_population() -> None:
    mod = load_module()

    ctx = mod.prereg_context()

    materialized = (
        mod.semantic_materialization(
            ctx
        )
    )

    assert len(materialized) == 54

    assert [
        item["ordinal"]
        for item in materialized
    ] == list(
        range(1, 55)
    )

    assert all(
        item["provider_constructed"] is False
        for item in materialized
    )

    assert all(
        item["network_request_made"] is False
        for item in materialized
    )


def test_005_timeout_gets_one_exact_same_object_retry() -> None:
    mod = load_module()

    req = request(mod)
    result = response(mod)

    delegate = TimeoutThenSuccessProvider(
        mod,
        result,
    )

    bounded = (
        mod.TransportRecoveringProvider(
            delegate=delegate,
            semantic_ordinal=45,
            expected_request_sha256=
                projection_sha(
                    mod,
                    req,
                ),
            sleep_fn=lambda _: None,
        )
    )

    actual = bounded.complete(
        req
    )

    assert actual is result
    assert len(delegate.calls) == 2
    assert delegate.calls[0] is req
    assert delegate.calls[1] is req

    assert len(bounded.calls) == 2

    assert bounded.calls[0]["outcome"] == (
        "PROVIDER_ERROR"
    )

    assert bounded.calls[0]["error_message"] == (
        mod.ELIGIBLE_TIMEOUT
    )

    assert bounded.calls[1]["outcome"] == (
        "ACCEPTED"
    )

    assert (
        bounded.calls[1][
            "same_request_object_as_first"
        ]
        is True
    )


def test_005_success_is_never_retried() -> None:
    mod = load_module()

    req = request(mod)
    result = response(mod)

    delegate = SuccessProvider(
        result
    )

    bounded = (
        mod.TransportRecoveringProvider(
            delegate=delegate,
            semantic_ordinal=1,
            expected_request_sha256=
                projection_sha(
                    mod,
                    req,
                ),
            sleep_fn=lambda _: None,
        )
    )

    assert bounded.complete(req) is result
    assert len(delegate.calls) == 1
    assert len(bounded.calls) == 1
    assert bounded.calls[0]["outcome"] == "ACCEPTED"


def test_005_noneligible_provider_error_is_never_retried() -> None:
    mod = load_module()

    req = request(mod)

    delegate = OtherErrorProvider(
        mod
    )

    bounded = (
        mod.TransportRecoveringProvider(
            delegate=delegate,
            semantic_ordinal=1,
            expected_request_sha256=
                projection_sha(
                    mod,
                    req,
                ),
            sleep_fn=lambda _: None,
        )
    )

    with pytest.raises(
        mod.ModelProviderError,
        match="some other provider failure",
    ):
        bounded.complete(
            req
        )

    assert len(delegate.calls) == 1
    assert len(bounded.calls) == 1


def test_005_second_timeout_is_final_failure() -> None:
    mod = load_module()

    req = request(mod)

    delegate = AlwaysTimeoutProvider(
        mod
    )

    bounded = (
        mod.TransportRecoveringProvider(
            delegate=delegate,
            semantic_ordinal=45,
            expected_request_sha256=
                projection_sha(
                    mod,
                    req,
                ),
            sleep_fn=lambda _: None,
        )
    )

    with pytest.raises(
        mod.ModelProviderError,
        match=mod.ELIGIBLE_TIMEOUT,
    ):
        bounded.complete(
            req
        )

    assert len(delegate.calls) == 2
    assert delegate.calls[0] is req
    assert delegate.calls[1] is req
    assert len(bounded.calls) == 2

    assert all(
        item["outcome"] == "PROVIDER_ERROR"
        for item in bounded.calls
    )


def test_005_request_hash_drift_fails_before_provider() -> None:
    mod = load_module()

    req = request(mod)

    delegate = SuccessProvider(
        response(mod)
    )

    bounded = (
        mod.TransportRecoveringProvider(
            delegate=delegate,
            semantic_ordinal=1,
            expected_request_sha256="0" * 64,
            sleep_fn=lambda _: None,
        )
    )

    with pytest.raises(
        mod.RequestBindingError,
    ):
        bounded.complete(
            req
        )

    assert delegate.calls == []
    assert bounded.calls == []


def test_005_transport_policy_is_narrow_and_frozen() -> None:
    mod = load_module()

    ctx = mod.prereg_context()

    retry = ctx.transport[
        "retry"
    ]

    assert retry[
        "max_retries_per_semantic_request"
    ] == 1

    assert retry[
        "eligible_exception_type"
    ] == "ModelProviderError"

    assert retry[
        "eligible_exact_error_message"
    ] == mod.ELIGIBLE_TIMEOUT

    assert retry[
        "same_model_request_object_required"
    ] is True

    assert retry[
        "same_request_projection_sha256_required"
    ] is True

    assert retry[
        "retry_after_boundary_rejection"
    ] is False

    assert retry[
        "retry_after_nonretryable_provider_error"
    ] is False

    assert retry[
        "retry_after_accepted_response"
    ] is False

    assert retry[
        "retry_after_semantic_parse_failure"
    ] is False
