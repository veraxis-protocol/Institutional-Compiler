"""The provider seam carries proposals, not admission or authority."""

from dataclasses import fields

from oic.model_provider import ModelRequest, ModelResponse


def test_request_has_no_authority_fields() -> None:
    assert {f.name for f in fields(ModelRequest)} == {
        "system_prompt",
        "user_prompt",
        "response_format",
        "temperature",
        "max_tokens",
    }


def test_response_has_no_admission_fields() -> None:
    assert {f.name for f in fields(ModelResponse)} == {
        "provider",
        "model",
        "content",
        "request_id",
        "raw",
    }
