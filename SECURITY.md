# Security policy

## Supported state

Only the current pre-release `main` lineage is maintained. There is no deployed
service, supported production release, or security certification.

## Private reporting

Do not disclose an unpatched vulnerability or confidential material in a public
issue. Use GitHub's [private vulnerability report](https://github.com/veraxis-protocol/Institutional-Compiler/security/advisories/new)
with the exact commit SHA, affected path, synthetic reproducer, and bounded
impact. If the form is unavailable, contact the owner privately through the
route published at [veraxis.io](https://veraxis.io/) before disclosure.

High-priority reports include fail-open schema/manifest validation, bootstrap
identity bypass, dependency/build compromise, credential exposure, or any path
that begins semantic execution despite the blocked gate. Reports are evidence,
not authorization to deploy, publish, acquire a corpus, or open the semantic
gate. No response-time commitment is established.

## Current boundary

The public bootstrap contains no production service and accepts no user documents.

The hosted Lab design must initially accept only public, synthetic, or non-confidential samples. It must reject confidential, privileged, regulated, export-controlled, and classified content until the corresponding security profile is reviewed and approved.

Security reports should not include confidential customer documents or raw proprietary policy text.
