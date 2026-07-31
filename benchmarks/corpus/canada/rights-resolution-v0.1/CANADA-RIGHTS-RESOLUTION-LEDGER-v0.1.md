# Canada Rights Resolution Ledger v0.1

Status: **INITIAL_STATE_NO_TRANSITIONS_RECORDED**

Unresolved source units: **10**. Excluded: CA-3.

CA-3 is already CLEAR_REPOSITORY_FREEZE and frozen. It is out of scope for this ledger, which tracks only unresolved sources.

## Ledger

| Source | Publisher | Current state | Rights disposition | Blocking reason | Unlocking artifact |
|---|---|---|---|---|---|
| CA-1 | TBS-SCT | **EVIDENCE_RECAPTURE_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher-cited licence notice was unreachable, so no reuse-permission evidence exists. | `TBS-TERMS-RECAPTURE-PROTOCOL-v0.1` |
| CA-2 | TBS-SCT | **EVIDENCE_RECAPTURE_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher-cited licence notice was unreachable, so no reuse-permission evidence exists. | `TBS-TERMS-RECAPTURE-PROTOCOL-v0.1` |
| CA-4 | TBS-SCT | **EVIDENCE_RECAPTURE_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher-cited licence notice was unreachable, so no reuse-permission evidence exists. | `TBS-TERMS-RECAPTURE-PROTOCOL-v0.1` |
| CA-5-APPROVALS | CanadaBuys (PSPC) | **PUBLISHER_PERMISSION_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher's robots policy refuses automated retrieval by this project. | `CANADABUYS-PERMISSION-REQUEST-v0.1` |
| CA-5-DELEGATION | CanadaBuys (PSPC) | **PUBLISHER_PERMISSION_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher's robots policy refuses automated retrieval by this project. | `CANADABUYS-PERMISSION-REQUEST-v0.1` |
| CA-5-LIMITS | CanadaBuys (PSPC) | **PUBLISHER_PERMISSION_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher's robots policy refuses automated retrieval by this project. | `CANADABUYS-PERMISSION-REQUEST-v0.1` |
| CA-5-SIGNING | CanadaBuys (PSPC) | **PUBLISHER_PERMISSION_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher's robots policy refuses automated retrieval by this project. | `CANADABUYS-PERMISSION-REQUEST-v0.1` |
| CA-6-ARCHIVE | CanadaBuys (PSPC) | **PUBLISHER_PERMISSION_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher's robots policy refuses automated retrieval by this project. | `CANADABUYS-PERMISSION-REQUEST-v0.1` |
| CA-6-CH6 | CanadaBuys (PSPC) | **PUBLISHER_PERMISSION_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher's robots policy refuses automated retrieval by this project. | `CANADABUYS-PERMISSION-REQUEST-v0.1` |
| CA-6-GLOSSARY | CanadaBuys (PSPC) | **PUBLISHER_PERMISSION_REQUIRED** | BLOCKED_PENDING_CLEARANCE | The publisher's robots policy refuses automated retrieval by this project. | `CANADABUYS-PERMISSION-REQUEST-v0.1` |

## Allowed states

- `EVIDENCE_RECAPTURE_REQUIRED`
- `PUBLISHER_PERMISSION_REQUIRED`
- `COUNSEL_REVIEW_REQUIRED`
- `READY_FOR_OWNER_DISPOSITION`
- `REMAINS_BLOCKED`

## Transition rule

Every transition must record:

- `previous_state`
- `proposed_next_state`
- `evidence_reference`
- `evidence_sha256`
- `reviewer_identity`
- `review_utc`
- `rationale`

Conditionally required:

- `evidence_sha256` — Required whenever the evidence reference is a captured artifact. A permission letter or counsel memorandum records its own document identifier instead.
- `owner_disposition_reference` — Required for any transition into READY_FOR_OWNER_DISPOSITION or out of it.

**Owner assertion alone is insufficient: True.** No owner statement may promote a source on its own. Every promotion must cite the recaptured evidence, the publisher permission, or the counsel record that the source's current state requires. An owner disposition selects among options that evidence has already opened; it does not open them.

**Dispositions do not move here.** No transition in this ledger changes a rights disposition. All ten sources remain BLOCKED_PENDING_CLEARANCE until a separate, authorized work order revises the rights clearance record itself.

## State gates

| State | Gate |
|---|---|
| `COUNSEL_REVIEW_REQUIRED` | Leaves this state only on a counsel disposition in the form the question specifies. |
| `EVIDENCE_RECAPTURE_REQUIRED` | Leaves this state only on a successful recapture carrying a byte length, a SHA-256 and a SHA-512. |
| `PUBLISHER_PERMISSION_REQUIRED` | Leaves this state only on a recorded publisher response. An unanswered category is not granted. |
| `READY_FOR_OWNER_DISPOSITION` | Reachable only once every prerequisite artifact for the source exists. Entry and exit both require an owner disposition reference. |
| `REMAINS_BLOCKED` | The terminal fail-closed state. Reachable from anywhere and requires no new evidence. |

