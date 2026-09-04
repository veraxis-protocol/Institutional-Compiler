"""Finite exact-request replay is offline and fails closed."""

import hashlib
import json
from pathlib import Path

import pytest

from oic.frozen_synthetic_provider import FrozenSyntheticProvider, request_digest
from oic.model_provider import ModelProvider, ModelProviderError, ModelRequest


def provider_file(tmp_path: Path, content: bytes) -> FrozenSyntheticProvider:
    path = tmp_path / "fixture.json"
    path.write_bytes(content)
    return FrozenSyntheticProvider(path, expected_sha256=hashlib.sha256(content).hexdigest())


def test_replay_is_deterministic_and_exhausts(tmp_path: Path) -> None:
    request = ModelRequest("synthetic", "input")
    data = json.dumps(
        {
            "format": "SYNTHETIC-REPLAY-001",
            "exchanges": [
                {"request_sha256": request_digest(request), "content": "{}", "model": "fixture"}
            ],
        }
    ).encode()
    first: ModelProvider = provider_file(tmp_path, data)
    second = provider_file(tmp_path, data)
    assert first.complete(request) == second.complete(request)
    with pytest.raises(ModelProviderError, match="exhausted"):
        second.complete(request)


def test_request_mismatch_does_not_consume(tmp_path: Path) -> None:
    request = ModelRequest("synthetic", "input")
    data = json.dumps(
        {
            "format": "SYNTHETIC-REPLAY-001",
            "exchanges": [
                {"request_sha256": request_digest(request), "content": "{}", "model": "fixture"}
            ],
        }
    ).encode()
    provider = provider_file(tmp_path, data)
    with pytest.raises(ModelProviderError, match="mismatch"):
        provider.complete(ModelRequest("synthetic", "different"))
    assert provider.consumed == 0
    assert provider.complete(request).content == "{}"


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not JSON",
        b"[]",
        b"{}",
        b'{"format":"SYNTHETIC-REPLAY-001","exchanges":[]}',
        b'{"format":"SYNTHETIC-REPLAY-001","exchanges":[{}]}',
    ],
)
def test_malformed_fixture_refused(tmp_path: Path, data: bytes) -> None:
    with pytest.raises(ModelProviderError):
        provider_file(tmp_path, data)


def test_missing_fixture_refused(tmp_path: Path) -> None:
    with pytest.raises(ModelProviderError):
        FrozenSyntheticProvider(tmp_path / "absent", expected_sha256="0" * 64)


def test_modified_fixture_refused(tmp_path: Path) -> None:
    path = tmp_path / "fixture.json"
    path.write_bytes(b"{}")
    with pytest.raises(ModelProviderError, match="digest mismatch"):
        FrozenSyntheticProvider(path, expected_sha256="0" * 64)
