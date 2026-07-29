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

The `compose-validation` CI job exercises this file on every run: it resolves the
configuration, pulls all three digest-pinned images, starts the services, waits for every
healthcheck to report healthy within a bounded timeout, prints `docker compose ps`, and
tears the stack down with `down -v --remove-orphans`. Service logs are printed on failure.

Docker is not available in the environment that authors these changes, so local evidence
is limited to the structural assertions in `tests/contract/test_compose_shell.py`. CI
supplies the executable evidence.

### A note on the OPA healthcheck

OPA's check makes a real HTTP request to its diagnostic `/health` endpoint using OPA's own
binary and Rego's `http.send` — the image is distroless, so there is no curl, wget, or
shell available. An earlier version ran `opa eval true`, which evaluates in-process and
would have reported healthy even if the server had failed to bind its port. A healthcheck
that cannot fail when the service is down is worse than none, because CI reports it green.
