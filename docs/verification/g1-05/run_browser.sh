#!/bin/sh
# Run from source root; all older tests write only to a fresh temporary directory.
set -eu
G1_OUTPUT=${G1_OUTPUT:-$(mktemp -d /tmp/moneki-browser-XXXXXX)}
export EVIDENCE_DIR="$G1_OUTPUT/workspace"
export METRICS_EVIDENCE_DIR="$G1_OUTPUT/metrics"
export DAILY_EVIDENCE_DIR="$G1_OUTPUT/daily"
export TOP_PRODUCTS_EVIDENCE_DIR="$G1_OUTPUT/ranking"
export G1_04_INTEGRATION_EVIDENCE_DIR="$G1_OUTPUT/integration"
export G1_UI_EVIDENCE_DIR="$G1_OUTPUT/ui"
printf 'Browser output: %s\n' "$G1_OUTPUT"
cd frontend
npx playwright install chromium
npx playwright test --output="$G1_OUTPUT/results" "$@"
