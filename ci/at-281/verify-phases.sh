#!/usr/bin/env bash
# The protected verify context must never pass on skipped, canceled, or failed jobs.
set -euo pipefail

failed=0
for phase in PYTHON_QUALITY_RESULT PYTEST_RESULT OPENAPI_RESULT OPENSPEC_EVIDENCE_RESULT SECURITY_METADATA_RESULT CONTAINER_RESULT; do
  result="${!phase:-missing}"
  printf '%s: %s\n' "$phase" "$result"
  if [[ "$result" != success ]]; then
    failed=1
  fi
done
exit "$failed"
