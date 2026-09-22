# VEIP Conformance Runner v0.1

Purpose: run the frozen `VEIP_CANONICAL_FIXTURES_v0.3.json` corpus against an external VEIP engine without embedding VEIP adjudication semantics in the runner.

## Integrity-only mode

```bash
python veip_test.py VEIP_CANONICAL_FIXTURES_v0.3.json --validate-only
```

This verifies frozen expected result hashes, manifest hashes for successful adjudications, reason-code ordering, reserved-code non-emission, positive-state ceilings, and error matcher shape.

## Engine mode

```bash
python veip_test.py VEIP_CANONICAL_FIXTURES_v0.3.json \
  --engine-cmd "python path/to/adapter.py" \
  --json-report report.json
```

The external adapter receives one JSON object on stdin:

```json
{"entry_point":"adjudicate","input":{}}
```

or:

```json
{"entry_point":"explain_boundary","input":{}}
```

It must return one JSON result object on stdout. Successful results are compared byte-semantically to the frozen expected object. Engine errors are matched only on `error_code` and `engine_version`; `message` must be a nonempty string because v0.1 does not freeze exact error prose.

Exit codes: `0` all pass, `1` engine conformance failure, `2` corpus/runner invocation failure.

The runner is intentionally not an oracle generator and contains no implementation of VEIP state-transition semantics.



