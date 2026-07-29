# Local infrastructure shell

Infrastructure only: PostgreSQL 17, MinIO, and OPA. There is **no application container**
and no ZTL or VEIP container. Starting this stack enables no compiler behaviour — the
semantic implementation gate is BLOCKED (`STATUS.md`).

OPA starts with no bundle, no policy, and no data. PostgreSQL starts with an empty
database and no migrations. Nothing here evaluates a control or stores an artifact.

## Setup

```bash
cp docker/.env.example docker/.env
```

Then edit `docker/.env` and replace every `CHANGEME` value. `.env` is git-ignored and
must never be committed. Compose fails fast with a named variable if any required value
is missing, so the stack has no silent default credential.

## Start

```bash
docker compose -f docker/compose.yaml --env-file docker/.env up -d
```

## Check health

```bash
docker compose -f docker/compose.yaml --env-file docker/.env ps
```

Wait for every service to report `healthy`. To follow a single service:

```bash
docker compose -f docker/compose.yaml --env-file docker/.env logs -f postgres
```

## Validate the file without starting anything

```bash
docker compose -f docker/compose.yaml --env-file docker/.env config --quiet
```

## Stop (data preserved)

```bash
docker compose -f docker/compose.yaml --env-file docker/.env down
```

Containers are removed; the named volumes `oic-postgres-data` and `oic-minio-data`
survive, so restarting brings the data back.

## Destroy (data lost)

```bash
docker compose -f docker/compose.yaml --env-file docker/.env down -v
```

**`-v` deletes the named volumes and everything in them.** Every PostgreSQL database and
every MinIO object created by this stack is destroyed. There is no undo and no backup:
nothing in this repository snapshots those volumes. Today the stack holds only local
development scratch data, so the practical blast radius is one developer's local state —
but that is a property of the current phase, not a guarantee of the command.

To remove the volumes without touching containers:

```bash
docker volume rm oic-postgres-data oic-minio-data
```

## Exposed ports

Every port binds to `127.0.0.1` only. No service is reachable from another host by
default.

| Service | Local address | Purpose |
|---|---|---|
| PostgreSQL | `127.0.0.1:5432` | Database |
| MinIO | `127.0.0.1:9000` | S3-compatible API |
| MinIO console | `127.0.0.1:9001` | Web console |
| OPA | `127.0.0.1:8181` | Server API (no policy loaded) |
| OPA diagnostics | `127.0.0.1:8282` | Health and metrics |

Override any port in `.env`. Do not rebind to `0.0.0.0` without a security review.

## Image pinning

Images are pinned by digest. See [`IMAGES.md`](IMAGES.md) for the digest table, how to
re-resolve a digest, and how to update a pin.

## What is deliberately absent

| Absent | Why |
|---|---|
| Application container | No semantic implementation exists to run |
| ZTL container | Interface provisional and unfrozen (ADR-009) |
| VEIP container | Interface provisional and unfrozen (ADR-010) |
| OPA policy or bundle | This repository generates no Rego and evaluates no control |
| Database schema or migrations | No persistence model is admitted yet |
| Seed or corpus data | Preflight corpus provenance is OPEN (`STATUS.md`) |

## Verification status

These images have **not** been pulled or run by the work order that added this file:
Docker was unavailable in that environment. `docker compose config` and `docker compose
up` were not executed. The compose file was validated by YAML parse and structural
assertions only (`tests/contract/test_compose_shell.py`). A reviewer with Docker should
run the start and health commands above and record the outcome.
