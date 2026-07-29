"""Contract tests over the local infrastructure compose shell.

Docker was not available in the environment that produced this work order, so
``docker compose config`` could not be run. These structural assertions are what stands
in for it: they check the properties that would otherwise be verified only by reading the
file, and they will keep holding once someone does run Docker.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.contract

COMPOSE_RELPATH = "docker/compose.yaml"
EXPECTED_SERVICES = {"postgres", "minio", "opa"}

DIGEST_PINNED = re.compile(r"^[\w./-]+:[\w.-]+@sha256:[0-9a-f]{64}$")
LOOPBACK_PORT = re.compile(r"^127\.0\.0\.1:")


@pytest.fixture(scope="module")
def compose(repo_root: Path) -> dict[Any, Any]:
    yaml = pytest.importorskip("yaml")
    document: dict[Any, Any] = yaml.safe_load(
        (repo_root / COMPOSE_RELPATH).read_text(encoding="utf-8")
    )
    return document


@pytest.fixture(scope="module")
def compose_text(repo_root: Path) -> str:
    return (repo_root / COMPOSE_RELPATH).read_text(encoding="utf-8")


def test_declares_exactly_the_three_infrastructure_services(compose: dict[Any, Any]) -> None:
    assert set(compose["services"]) == EXPECTED_SERVICES


def test_every_image_is_pinned_by_digest(compose: dict[Any, Any]) -> None:
    """A tag can be moved upstream; a digest cannot."""
    for name, service in compose["services"].items():
        image = service["image"]
        assert DIGEST_PINNED.match(image), f"{name} image is not digest-pinned: {image}"


def test_postgres_is_version_17(compose: dict[Any, Any]) -> None:
    assert compose["services"]["postgres"]["image"].startswith("postgres:17.")


def test_every_service_has_a_healthcheck(compose: dict[Any, Any]) -> None:
    for name, service in compose["services"].items():
        assert "healthcheck" in service, name
        healthcheck = service["healthcheck"]
        assert healthcheck["test"]
        assert "interval" in healthcheck
        assert "retries" in healthcheck


def test_every_published_port_binds_to_loopback(compose: dict[Any, Any]) -> None:
    published = [
        port for service in compose["services"].values() for port in service.get("ports", [])
    ]
    assert published, "no ports published; the assertion would be vacuous"
    for port in published:
        assert LOOPBACK_PORT.match(str(port)), f"port is not loopback-bound: {port}"


def test_no_service_binds_to_all_interfaces(compose_text: str) -> None:
    assert "0.0.0.0:" not in compose_text.replace("--addr=0.0.0.0:8181", "").replace(
        "--diagnostic-addr=0.0.0.0:8282", ""
    )


def test_stateful_services_use_named_volumes(compose: dict[Any, Any]) -> None:
    volumes = compose["volumes"]
    assert set(volumes) == {"postgres-data", "minio-data"}
    assert volumes["postgres-data"]["name"] == "oic-postgres-data"
    assert volumes["minio-data"]["name"] == "oic-minio-data"


def test_no_credential_has_a_default_value(compose_text: str) -> None:
    """Every credential must come from `.env` and fail loudly when unset.

    `${VAR:?message}` makes compose refuse to start rather than fall back to a default,
    so there is no built-in credential to forget to change.
    """
    for variable in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD",
    ):
        assert f"${{{variable}:?" in compose_text, variable
        assert f"${{{variable}:-" not in compose_text, f"{variable} has a default value"


def test_no_real_env_file_is_committed(repo_root: Path) -> None:
    assert (repo_root / "docker" / ".env.example").is_file()
    assert not (repo_root / "docker" / ".env").exists()
    assert not (repo_root / ".env").exists()


def test_env_example_uses_changeme_placeholders(repo_root: Path) -> None:
    text = (repo_root / "docker" / ".env.example").read_text(encoding="utf-8")
    for variable in ("POSTGRES_PASSWORD", "MINIO_ROOT_PASSWORD"):
        line = next(row for row in text.splitlines() if row.startswith(f"{variable}="))
        assert "CHANGEME" in line, f"{variable} does not use a CHANGEME placeholder"


def test_gitignore_excludes_env_files(repo_root: Path) -> None:
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert "\n.env\n" in gitignore


# ---------------------------------------------------------------------------
# Boundary discipline
# ---------------------------------------------------------------------------


def test_no_application_ztl_or_veip_container(compose: dict[Any, Any]) -> None:
    """Boundaries that are provisional must not appear as running services."""
    services = set(compose["services"])
    for forbidden in ("ztl", "veip", "app", "api", "compiler", "web", "ui"):
        assert forbidden not in services


def test_no_policy_or_bundle_is_mounted_into_opa(compose: dict[Any, Any]) -> None:
    """OPA must start empty: no bundle, no policy, no data."""
    opa = compose["services"]["opa"]
    assert "volumes" not in opa, "OPA has a mount; it must start with nothing loaded"
    command = " ".join(opa["command"])
    for flag in ("--bundle", "--set=services", "policy.rego", "/policies", "data.json"):
        assert flag not in command


def test_opa_decision_logging_to_console_is_off(compose: dict[Any, Any]) -> None:
    command = " ".join(compose["services"]["opa"]["command"])
    assert "--set=decision_logs.console=false" in command


def test_minio_update_check_is_disabled(compose: dict[Any, Any]) -> None:
    assert compose["services"]["minio"]["environment"]["MINIO_UPDATE"] == "off"


# ---------------------------------------------------------------------------
# Documentation obligations
# ---------------------------------------------------------------------------


def test_readme_documents_the_full_lifecycle(repo_root: Path) -> None:
    readme = (repo_root / "docker" / "README.md").read_text(encoding="utf-8")
    for command in ("up -d", "ps", "down", "down -v", "config --quiet"):
        assert command in readme, command


def test_readme_documents_volume_data_loss(repo_root: Path) -> None:
    readme = (repo_root / "docker" / "README.md").read_text(encoding="utf-8")
    assert "deletes the named volumes" in readme
    assert "no undo" in readme.lower()


def test_images_doc_records_every_pinned_digest(repo_root: Path, compose: dict[Any, Any]) -> None:
    images_doc = (repo_root / "docker" / "IMAGES.md").read_text(encoding="utf-8")
    for service in compose["services"].values():
        digest = service["image"].split("@", 1)[1]
        assert digest in images_doc, digest


def test_images_doc_states_pins_were_not_run(repo_root: Path) -> None:
    """The verification limitation must be recorded, not glossed over."""
    images_doc = (repo_root / "docker" / "IMAGES.md").read_text(encoding="utf-8")
    # Collapse markdown emphasis and hard-wrapped lines before matching prose.
    plain = " ".join(images_doc.replace("*", "").split())
    assert "have not been pulled or run" in plain
    assert "docker compose config" in plain
