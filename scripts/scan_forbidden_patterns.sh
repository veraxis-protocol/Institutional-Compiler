#!/usr/bin/env bash
#
# Coarse credential tripwire for committed files.
#
# SCOPE AND LIMITATIONS -- read before relying on this.
#
# This is a regex scan (via `git grep`) over files tracked by git at the current commit.
# It is a cheap tripwire for the most obvious mistakes. It is NOT a secret-scanning
# product and must not be described as one. Specifically, it does NOT detect:
#
#   * a secret committed in an earlier commit -- it scans the working tree only, never
#     git history;
#   * a secret that is base64-, hex-, or otherwise encoded;
#   * a secret split across lines or assembled at runtime;
#   * a high-entropy string matching no known pattern;
#   * a credential in a binary file (`-I` skips binaries);
#   * anything in a file that is not tracked by git.
#
# It also produces false positives: any line resembling an assignment to a credential-ish
# name is flagged, including fixtures and documentation. Suppress a reviewed false
# positive with an inline `pragma: allowlist secret` comment and justify it in the pull
# request.
#
# Passing this check is not evidence that the repository contains no secrets.
#
# Portable across bash 3.2 (macOS) and bash 5 (CI).

set -uo pipefail

cd "$(git rev-parse --show-toplevel)"

fail=0

# Pathspecs excluded from the scan:
#   this script            - it contains the patterns themselves
#   requirements/*.txt     - lockfiles are full of hex hashes
#   docs/tdd/*.pdf         - binary, and bootstrap-controlled
EXCLUDES=(
  ':(exclude)scripts/scan_forbidden_patterns.sh'
  ':(exclude)requirements/*.txt'
  ':(exclude)docs/tdd/*.pdf'
)

report() {
  label="$1"
  pattern="$2"
  case_flag="${3:-}"

  if [ "${case_flag}" = "-i" ]; then
    hits="$(git grep -n -I -i -E -e "${pattern}" -- . "${EXCLUDES[@]}" 2>/dev/null)"
  else
    hits="$(git grep -n -I -E -e "${pattern}" -- . "${EXCLUDES[@]}" 2>/dev/null)"
  fi

  # Drop reviewed false positives and documented placeholders. `.env.example` must stay
  # readable, so a value that is obviously a placeholder is not a finding.
  hits="$(
    printf '%s\n' "${hits}" \
      | grep -v 'pragma: allowlist secret' \
      | grep -v -i -E '[:=][[:space:]]*.?(CHANGEME|PLACEHOLDER|REPLACE_ME|<[a-z_-]+>|xxxx)' \
      | grep -v '^$'
  )"

  if [ -n "${hits}" ]; then
    echo "::error::forbidden pattern detected (${label})"
    printf '%s\n' "${hits}"
    fail=1
  fi
}

# Private keys of any kind.
report "private key block" '-----BEGIN [A-Z ]*PRIVATE KEY-----'

# Provider-shaped tokens with distinctive prefixes.
report "AWS access key id"    'AKIA[0-9A-Z]{16}'
report "GitHub token"         'gh[pousr]_[A-Za-z0-9]{36,}'
report "Slack token"          'xox[abprs]-[0-9A-Za-z-]{10,}'
report "Google API key"       'AIza[0-9A-Za-z_-]{35}'
report "Stripe live key"      'sk_live_[0-9A-Za-z]{16,}'
report "generic bearer token" 'Bearer [A-Za-z0-9._~+/-]{40,}'

# Assignments to credential-shaped names with a substantial value. Placeholders such as
# CHANGEME, <redacted>, and empty values stay under the length threshold or are excluded
# below, so `.env.example` and documentation remain usable.
report "credential assignment" \
  '(password|passwd|secret|api_key|apikey|access_token|private_key)[ ]*[:=][ ]*.?[A-Za-z0-9/+=_-]{16,}' \
  -i

# A real .env must never be committed. `.env.example` is expected and permitted.
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "::error::.env is tracked by git; only .env.example may be committed"
  fail=1
fi

if [ "${fail}" -ne 0 ]; then
  echo
  echo "Credential pattern scan FAILED."
  echo "If a hit is a reviewed false positive, append 'pragma: allowlist secret' to the"
  echo "line and justify it in the pull request."
  exit 1
fi

echo "Credential pattern scan passed."
echo
echo "LIMITATIONS: this scan covers tracked, non-binary working-tree files only. It does"
echo "not scan git history, encoded or split values, or binary files. Passing it is not"
echo "evidence that the repository contains no secrets."
