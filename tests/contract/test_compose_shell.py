"""Contract tests over the local infrastructure compose shell.

These are structural assertions over the compose file: digest pinning, loopback binding,
absence of default credentials, and boundary discipline. They are cheap and run
everywhere, including where Docker is unavailable.

They are not a substitute for running the stack. The ``compose-validation`` CI job does
that: it resolves the configuration, pulls every pinned digest, starts all three
services, waits for their healthchecks to pass, and tears the stack down. Between them,
the structure is asserted here and the behaviour is asserted there.
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


def test_healthchecks_probe_real_service_availability(compose: dict[Any, Any]) -> None:
    """A healthcheck must test that the service answers, not merely that a binary runs.

    The OPA check was originally `opa eval true`, which evaluates in-process and reports
    healthy even when the server failed to bind its port. A check that cannot fail when
    the service is down is worse than no check, because CI would report it green.
    """
    checks = {name: " ".join(s["healthcheck"]["test"]) for name, s in compose["services"].items()}

    # PostgreSQL: pg_isready connects to the server and reports acceptance.
    assert "pg_isready" in checks["postgres"]

    # MinIO: `mc ready local` queries the server's readiness endpoint.
    assert "mc ready" in checks["minio"]

    # OPA: a real HTTP request to the diagnostic health endpoint.
    opa = checks["opa"]
    assert "http.send" in opa, "OPA healthcheck does not make an HTTP request"
    assert "/health" in opa
    assert "status_code == 200" in opa
    assert "--fail" in opa, "without --fail an undefined result would still exit 0"
    assert "raise_error" in opa, "a refused connection must not abort with an error"
    assert opa.split() != ["CMD", "/opa", "eval", "--fail", "--format=values", "true"]


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


def test_docs_state_where_compose_evidence_comes_from(repo_root: Path) -> None:
    """Both docs must say CI supplies the executable evidence, and be honest about scope.

    Structural tests alone were previously the only evidence; that limitation had to be
    stated. Now that `compose-validation` runs the stack, the docs must say so without
    implying the authoring environment proved anything it did not.
    """
    for relname in ("IMAGES.md", "README.md"):
        plain = " ".join(
            (repo_root / "docker" / relname).read_text("utf-8").replace("*", "").split()
        )
        assert "compose-validation" in plain, relname
        assert "CI supplies the executable evidence" in plain, relname
        assert "Docker is not available in the environment that authors" in plain, relname
