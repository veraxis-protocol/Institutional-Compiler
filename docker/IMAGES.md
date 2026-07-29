# Pinned container images

Every image in [`compose.yaml`](compose.yaml) is pinned by **digest**, not only by tag.
The tag is retained for readability; Docker resolves the digest, so a retagged or
replaced upstream image cannot change what runs locally without a visible diff here.

| Service | Image | Tag | Digest |
|---|---|---|---|
| `postgres` | `postgres` | `17.6-alpine3.22` | `sha256:ef257d85f76e48da1c64832459b59fcaba1a4dac97bf5d7450c77753542eee94` |
| `minio` | `minio/minio` | `RELEASE.2025-04-22T22-12-26Z` | `sha256:a1ea29fa28355559ef137d71fc570e508a214ec84ff8083e39bc5428980b015e` |
| `opa` | `openpolicyagent/opa` | `1.4.2` | `sha256:35a093d9ae828373cf88f68ecaa8189ab26287468074a3b78f0601d9c8b7a4f5` |

PostgreSQL 17 is required by the work order; `17.6-alpine3.22` is the specific patch
release pinned. OPA is the first executable target per ADR-004, but this stack loads no
policy into it.

## How these digests were resolved

Resolved from the Docker Hub registry API, which requires no local Docker installation:

```bash
repo="library/postgres"; tag="17.6-alpine3.22"
token="$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${repo}:pull" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')"
curl -sI -H "Authorization: Bearer ${token}" \
  -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json" \
  "https://registry-1.docker.io/v2/${repo}/manifests/${tag}" | grep -i docker-content-digest
```

For `minio/minio` and `openpolicyagent/opa`, use the repository path as written in the
table (no `library/` prefix).

## Verifying a pin with Docker present

```bash
docker manifest inspect postgres:17.6-alpine3.22 --verbose | grep -m1 digest
```

The reported digest must equal the one in the table and in `compose.yaml`.

## Updating a pin

1. Resolve the new digest with one of the commands above.
2. Update both `compose.yaml` and this table in the same commit.
3. State the reason for the bump in the pull request.

Never update the tag without updating the digest, and never remove the digest to "let it
float". A floating tag is not a pin.

## Verification status of these pins

The `compose-validation` CI job pulls every digest in this table on each run, then starts
the services and waits for their healthchecks. A digest that no longer resolves, or an
image that no longer starts, fails the build.

Docker is not available in the environment that authors these changes, so local evidence
is limited to structural assertions in `tests/contract/test_compose_shell.py`. CI supplies
the executable evidence.
