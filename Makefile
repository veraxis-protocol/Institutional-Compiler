.PHONY: verify falsify

PYTHON ?= python

verify:
	$(PYTHON) -m oic.cli validate-schema
	$(PYTHON) -m oic.cli verify-bootstrap
	$(PYTHON) scripts/verify_bounded_semantic_code_start.py
	@set +e; $(PYTHON) -m oic.cli verify-manifest --all; code=$$?; set -e; \
	  test $$code -eq 3; echo "PASS manifest remains explicitly INCOMPLETE (exit 3)"

falsify:
	$(PYTHON) scripts/falsify_infrastructure.py
