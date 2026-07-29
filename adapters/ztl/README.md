# adapters/ztl

ZTL adapter. **Provisional project-controlled dependency** (TDD-OIC-001 v1.1 §3.4, §3.5).

## Dossier

`ZTL-DOSSIER-v0.1.md` in this directory supplies the fields required by `DEPENDENCIES.md`.
It is a copy for local reading; the canonical, pinnable source is upstream.

## Pin

| Item | Value |
|---|---|
| Repository | `github.com/inventor1975/ZTL` |
| Annotated tag | `veraxis-ztl-input-v0.1` |
| Tag target commit | `e819dec7e89d2dc67d6371e1eedb8e7aae854602` |
| Lean toolchain | `leanprover/lean4:v4.29.1` |
| Conformance input (SHA-256) | `33de416110be748a647216ef97b246e925b2dcde95e95cbefdd13cf51f69bb8c` |
| Fixtures (SHA-256) | `717853cf2a84ede0cb0472192d2e4fac4303acf29775f0d41d972e15c3652f93` |
| Dependency closure (SHA-256) | `efe05b396cdb4a8731f51b5cc927a8fc998e01a789a2a6dff5657e5a2b5971a5` |

The tag is annotated, **not GPG-signed**.

## Interface (pinned surface)

```
judge(text, marking)  -> { verdict, grade, disposition, unverified, formula, why }
check(text, marking)
join(text_a, text_b, operator, marking)
grade(phi, marking)
formalize(text)
```

**Adapter contract:** consume `disposition` (`EARNED` / `REFUTED` / `OPEN`) as the operational
signal, `grade` (`hereditary` / `sound` / `until-verification`) as the warranty qualifier, and
`unverified` as `missing_inputs`. The raw `verdict` field is an internal kernel detail.

Reading `verdict` alone breaks invariant I-04: `judge("p & q", {p:T, q:Z})` returns
`verdict='F'` with `disposition='OPEN'` — an adapter mapping that `F` to DENY converts
"not yet established" into "established false". See dossier §6.3.

## Boundary

ZTL does not validate source authenticity, determine authority, interpret prose, create
institutional admission, or decide ALLOW/DENY on its own. Those are OIC's planes.

## Open items

| Item | State |
|---|---|
| Independent Tier-1 reproduction | **OPEN** — cannot be closed by the ZTL side |
| GPG signature on the release tag | **OPEN** |
| Joint ZTL↔Envelope mapping conformance test | PROPOSED (dossier §6.3) |
| ZTL↔OIC time-model alignment | PROPOSED (dossier §6.4) |
| `MissingGround` granularity vs review docket | QUESTION for OIC |

No statement in this directory asserts that ZTL has been independently reviewed or reproduced.
