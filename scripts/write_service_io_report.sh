#!/usr/bin/env sh
set -eu

OUTPUT_FILE="${OUTPUT_FILE:-test_outputs/service_inputs_outputs.md}"

mkdir -p "$(dirname "$OUTPUT_FILE")"

{
  printf '# Service Test Inputs And Outputs\n\n'
  printf 'Generated with `make service-io-report`.\n\n'
  printf '```text\n'
  ./scripts/smoke_test.sh
  printf '```\n'
} > "$OUTPUT_FILE"

printf 'Wrote %s\n' "$OUTPUT_FILE"
