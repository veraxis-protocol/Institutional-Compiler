# IR Lineage v0.1

## The chain

Every canonical semantic assertion must be reconstructable, without re-reading the source
document, back to the exact bytes it came from and the authority that made those bytes
interpretable:

```
IR assertion
  → interpretation basis + interpretation evidence
  → admitted Candidate Normative Unit
  → admission receipt
  → candidate source anchor
  → exact source bytes / version / digest
  → authority evidence
```

No IR field is provenance-free. The chain is closed at both ends: an assertion with no
source support cannot be `ESTABLISHED`, and an admission binding with no authority
evidence cannot carry `ADMITTED`.

## Minimum lineage projection

For one assertion, the minimum set of fields that must be recoverable from the IR unit
alone:

| Link | Fields |
| --- | --- |
| assertion | `assertion_id`, `slot`, `interpretation_status`, `value`, `alternatives[].value` |
| interpretation | `interpretation_basis`, `interpretation_evidence_refs[]` |
| normalization, when present | `normalization.kind`, `normalization.raw_source_text`, `normalization.normalized_value` |
| source support | `source_support.anchor_id`, `source_support.quote`, `source_support.content_hash` |
| material qualifiers | `material_qualifiers[].qualifier_kind`, `.text`, `.source_support` |
| candidate | `admission.candidate_unit_id`, `admission.candidate_projection_digest` |
| admission | `admission.admission_receipt_id`, `admission.admission_state`, `admission.evaluation_time`, `admission.evaluation_scope` |
| source instance | `admission.source_id`, `admission.source_version`, `admission.source_digest` |
| authority | `admission.authority_evidence_refs[]`, `admission.authority_evidence_digests[]` |
| rules | `admission.ruleset_id`, `admission.ruleset_digest`, `admission.evaluator_id`, `admission.evaluator_version`, `interpretation_ruleset.ruleset_id`, `interpretation_ruleset.ruleset_digest` |
| unit | `ir_unit_id`, `interpretation_time`, `supersedes_ir_unit_id` |

Three of these are load-bearing in a way that is easy to lose:

* **`normalization.raw_source_text`.** A normalized value alone is unauditable. Keeping the
  raw text beside it means a reviewer can check the transformation rather than trust it.
* **`source_support.content_hash`.** Without it, a quote is only a claim about a document;
  with it, the quote is bound to exact bytes.
* **`interpretation_evidence_refs`.** Without them, an `ESTABLISHED` value cannot be
  distinguished from a confident guess.

## Reconstruction properties

1. **Assertion → bytes.** `source_support.quote` is literally contained in the admitted
   candidate span, and `content_hash` equals `admission.source_digest`. Every corpus
   vector is checked for this at build time and again in the contract suite.
2. **Assertion → authority.** `interpretation_evidence_refs` name instruments whose
   `applies_to` binds the same `source_id`, `source_version` and `source_digest` as the
   admission binding. A warrant for one source instance never reaches another.
3. **Unit → admission.** The admission binding reproduces the receipt fields needed to
   verify the receipt identity independently, without re-running admission.
4. **Unit → rules.** Both ruleset digests are carried, so a later reader can tell which
   admission rules and which interpretation rules produced this unit.
5. **Unit → predecessor.** `supersedes_ir_unit_id` links a successor to the unit it
   replaces. The predecessor is never edited.

## What lineage deliberately does not do

Lineage records where meaning came from. It does not certify that the meaning is correct,
that the issuer was entitled to issue the evidence, or that the institution would agree on
review. Those are separate questions, and none of them is answered here.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`
