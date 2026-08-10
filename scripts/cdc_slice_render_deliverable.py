#!/usr/bin/env python3
"""Render the CDC-shaped deliverable template with placeholders only.

The template follows the shape of the CDC/CRC *note d'orientation* and carries
the French section labels the challenge names. It proves that the template
renders, that findings and provenance references can be bound, and that
limitations and nonclaims render — without containing any mission finding.

Every result slot renders as an explicit placeholder:

``NOT_YET_OBSERVED`` · ``NOT_YET_ADJUDICATED`` · ``NOT_AUTHORIZED_AS_OFFICIAL``

Passing a run record is possible but not required; when none is supplied the
template renders in placeholder mode. No synthetic favourable finding is ever
substituted for an absent one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

NOT_YET_OBSERVED: Final = "NOT_YET_OBSERVED"
NOT_YET_ADJUDICATED: Final = "NOT_YET_ADJUDICATED"
NOT_AUTHORIZED_AS_OFFICIAL: Final = "NOT_AUTHORIZED_AS_OFFICIAL"

# The five standard mission deliverables named by the challenge. Only the
# orientation note is templated at this stage.
DELIVERABLES_FR: Final[tuple[tuple[str, str], ...]] = (
    ("note d'orientation", "orientation note"),
    ("rapport provisoire", "provisional report"),
    ("rapport définitif", "final report"),
    ("fiche de synthèse des constatations", "findings summary sheet"),
    ("lettre de transmission", "transmittal letter"),
)

HEADER: Final = f"""# Note d'orientation — CDC-TEST-MISSION-001

## Statut du document / Document status

```text
statut / status              = PROJET_POUR_REVUE / DRAFT_FOR_REVIEW
document officiel / official = {NOT_AUTHORIZED_AS_OFFICIAL}
mode d'assurance             = SYNTHETIC_EVALUATION_ONLY
mission                      = CDC-TEST-MISSION-001
contrat / contract           = VEIP-CDC-SLICE-EVALUATION-CONTRACT-v0.1
```

Ce document est un projet généré par machine à partir d'une exécution
synthétique. Il ne constitue pas un acte officiel, n'établit aucune constatation
d'audit et ne confère aucune autorité de la Cour des comptes. La revue,
l'édition, la validation et la signature par le contrôleur restent requises.

This is a machine-drafted synthetic document. It is not an official record, it
states no audit finding, and it confers no CDC authority. Controller review,
editing, validation and sign-off remain required.
"""

READING_GUIDE: Final = """
## Guide de lecture / Reading guide

Un refus, un état non résolu ou une transition bloquée est un résultat
enregistré — ni un défaut, ni une constatation.

A refusal, an unresolved state or a blocked transition is a recorded outcome,
not a defect and not a finding. `REQUEST_EVIDENCE` leaves the matter unresolved;
`DISMISS` cannot enter relied-upon outputs; `ESCALATE` blocks the ordinary
adoption path; `ACCEPT_CANDIDATE` admits a candidate only and does not make it
official.
"""

FOOTER: Final = """
## Limites et non-revendications / Limitations and nonclaims

Ce projet n'établit pas : déploiement CDC, validation CDC, aptitude à la
production, conformité VEIP de production, autorité juridique, identité réelle
du réviseur, suffisance des preuves, statut de constatation officielle,
confiance en production, actualité d'exécution, remplacement de fournisseur,
extensibilité à l'ensemble des CRC, ni conformité hors-ligne.

This draft establishes none of: CDC deployment, CDC validation, production
readiness, production VEIP conformance, legal authority, real-world reviewer
identity, evidence sufficiency, official finding status, production reliance,
runtime currentness, supplier replacement, CRC-wide scalability, or
offline/no-egress conformance.
"""


def render(run_record: dict[str, Any] | None) -> str:
    """Render the template. With no record, every result slot is a placeholder."""
    parts: list[str] = [HEADER]

    parts.append("\n## Livrables de mission / Mission deliverables\n\n")
    parts.append("| Livrable (FR) | Deliverable (EN) | État / State |\n|---|---|---|\n")
    for french, english in DELIVERABLES_FR:
        state = "TEMPLATED" if french == "note d'orientation" else NOT_YET_OBSERVED
        parts.append(f"| {french} | {english} | {state} |\n")

    parts.append("\n## Constatations candidates / Candidate findings\n\n")
    procedures: list[dict[str, Any]] = list((run_record or {}).get("procedures", []))
    parts.append(
        "| Cas / Case | Décision / Decision | Motif / Reason | "
        "État épistémique / Epistemic | Adjudication |\n|---|---|---|---|---|\n"
    )
    if not procedures:
        for case_id in ("S-01", "S-02", "S-03", "S-04", "S-05", "S-06", "S-07", "S-08"):
            parts.append(
                f"| {case_id} | {NOT_YET_OBSERVED} | {NOT_YET_OBSERVED} | "
                f"{NOT_YET_OBSERVED} | {NOT_YET_ADJUDICATED} |\n"
            )
    else:
        for procedure in procedures:
            parts.append(
                "| {case} | {decision} | {reason} | {epistemic} | {adj} |\n".format(
                    case=procedure.get("case_id", procedure.get("procedure_id", NOT_YET_OBSERVED)),
                    decision=procedure.get("decision", NOT_YET_OBSERVED),
                    reason=procedure.get("reason_code", NOT_YET_OBSERVED),
                    epistemic=procedure.get("epistemic_state", NOT_YET_OBSERVED),
                    adj=NOT_YET_ADJUDICATED,
                )
            )

    parts.append("\n## Traçabilité / Provenance references\n\n")
    parts.append(
        "| Référence / Reference | Valeur / Value |\n|---|---|\n"
        f"| source / admission | {NOT_YET_OBSERVED} |\n"
        f"| contrôle admis / admitted control | {NOT_YET_OBSERVED} |\n"
        f"| empreinte de preuve / evidence digest | {NOT_YET_OBSERVED} |\n"
        f"| garantie ZTL / ZTL warrant | {NOT_YET_OBSERVED} |\n"
    )

    parts.append(READING_GUIDE)
    parts.append(FOOTER)
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    """Render the deliverable template."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-record", type=Path, default=None)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)

    record: dict[str, Any] | None = None
    if args.run_record is not None:
        if not args.run_record.is_file():
            print(f"run record not found: {args.run_record}", file=sys.stderr)
            return 2
        loaded: Any = json.loads(args.run_record.read_text(encoding="utf-8"))
        record = loaded

    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(render(record), encoding="utf-8")
    print(str(args.destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
