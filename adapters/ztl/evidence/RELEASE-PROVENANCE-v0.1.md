# Release provenance evidence — ZTL v0.1

**Work order:** ZTL-OIC-WO-002, Deliverable A.
**Prepared by:** Vitaly Reznik (ZTL semantic boundary owner).
**Date:** 2026-07-29.
**Status of the field:** **CLOSED** — a signed immutable release reference exists.

---

## 1. Required evidence

| Field | Value |
|---|---|
| Repository | `github.com/inventor1975/ZTL` (public) |
| Tag name | `veraxis-ztl-input-v0.1.1-signed` |
| Target commit | `e819dec7e89d2dc67d6371e1eedb8e7aae854602` |
| Signature type | OpenPGP, EdDSA (Ed25519) |
| Signer identity | Vitaly Reznik `<vitalyreznik@gmail.com>` |
| Public-key fingerprint | `F170 414D DBB7 8F23 1929 1211 75B1 3F5A EC28 313A` |
| Key ID (short) | `75B13F5AEC28313A` |
| Public-key retrieval | (a) in-repo: `ZTL-signing-key.pub.asc` at the repository root; (b) GitHub account keys of `inventor1975` |
| Verification command | `git tag -v veraxis-ztl-input-v0.1.1-signed` |
| Toolchain | Lean `leanprover/lean4:v4.29.1`; GnuPG 2.x; git 2.x |
| Date signed | 2026-07-29 20:55:09 IDT |

## 2. Raw verification output

Reproduced verbatim, not paraphrased:

```
$ git tag -v veraxis-ztl-input-v0.1.1-signed
gpg: Signature made Wed 29 Jul 2026 08:55:09 PM IDT
gpg:                using EDDSA key F170414DDBB78F231929121175B13F5AEC28313A
gpg: Good signature from "Vitaly Reznik <vitalyreznik@gmail.com>" [ultimate]
object e819dec7e89d2dc67d6371e1eedb8e7aae854602
type commit
tag veraxis-ztl-input-v0.1.1-signed
tagger Vitaly Reznik <vitalyreznik@gmail.com> 1785347709 +0300

Signed provenance for the ZTL input package v0.1.
...
```

```
$ gpg --fingerprint 75B13F5AEC28313A
pub   ed25519 2026-07-29 [SC]
      F170 414D DBB7 8F23 1929  1211 75B1 3F5A EC28 313A
uid           [ultimate] Vitaly Reznik <vitalyreznik@gmail.com>
```

## 3. Why a new tag rather than a signed original

The work order requires that the existing annotated tag not be replaced or rewritten. It has not been.

`veraxis-ztl-input-v0.1` remains exactly as accepted upstream on 2026-07-21. Re-signing it is not an annotation change — it creates a **different tag object**, which would break every downstream pin taken against it. The signed tag therefore points at the **same commit** with the **same artifact hashes**, and adds provenance only.

| Tag | Object | Points at | Signed |
|---|---|---|---|
| `veraxis-ztl-input-v0.1` | `74bdae9bb6564524e41feb2d475cd7a6b40a31b0` | `e819dec` | no (annotated) |
| `veraxis-ztl-input-v0.1.1-signed` | `078fac045a3c7113df8089a29a146a887398c931` | `e819dec` | **yes** |

Artifacts under both tags are byte-identical:

| Artifact | SHA-256 |
|---|---|
| `VERAXIS-ZTL-CONFORMANCE-input-v0.1.md` | `33de416110be748a647216ef97b246e925b2dcde95e95cbefdd13cf51f69bb8c` |
| `VERAXIS-ZTL-fixtures-v0.1.json` | `717853cf2a84ede0cb0472192d2e4fac4303acf29775f0d41d972e15c3652f93` |
| `VERAXIS-ZTL-deps-v0.1.json` | `efe05b396cdb4a8731f51b5cc927a8fc998e01a789a2a6dff5657e5a2b5971a5` |

## 4. Limitations — stated, not softened

1. **The key is new and has no external attestation.** It was created 2026-07-29 for release signing. Nobody has cross-signed it; it appears in no web of trust. It proves continuity of releases from this maintainer's machine — nothing more. A consumer who has never seen this key before gains provenance only against future tampering, not retroactive assurance about 2026-07-21.
2. **The key is held without a passphrase**, so signing is non-interactive. Anyone with access to the maintainer's workstation can sign as this identity. This is a workstation key, not a hardware-backed or HSM identity, and must not be described as one.
3. **The original tag remains unsigned.** Provenance therefore covers the signed tag object; the annotated tag `veraxis-ztl-input-v0.1` itself carries no cryptographic proof of origin, only content that matches.
4. **Signing says nothing about the corpus.** It attests who published the reference, not that the theorems are correct, the fixtures adequate, or the corpus independently reproduced. Item "independent Tier-1 reproduction" remains **OPEN** and is not affected by anything in this document.
5. **No key rotation or revocation procedure is published yet.** If the key is lost or compromised there is currently no declared successor path. This is an open hardening item.

## 5. What this closes and what it does not

**Closes:** "signed release provenance" as a dependency-dossier field, under the limitations above.

**Does not close, and is not claimed to:** independent reproduction; interface freeze; the OIC semantic implementation gate; any statement about ZTL maturity.
