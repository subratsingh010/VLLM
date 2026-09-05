#!/bin/sh
set -eu
if [ "$#" -ne 2 ]; then
  echo "usage: $0 VARIANT RUN_ID" >&2
  exit 2
fi
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
RUN="$ROOT/pipeline_b/results/$1/$2"
VARIANT=$1
RUN_ID=$2
test -d "$RUN/benchmark" || { echo "benchmark directory missing: $RUN" >&2; exit 1; }
STATE=$(jq -r '.status' "$RUN/RUN_STATUS.json")
test "$STATE" = "benchmarked" || { echo "run state must be benchmarked, got: $STATE" >&2; exit 1; }
cd "$ROOT"
.venv/bin/python -m benchmark.capacity_analysis \
  --run-dir "$RUN/benchmark" --output-dir "$RUN/analysis"
.venv/bin/python -m pipeline_b.scripts.mark_state --variant "$VARIANT" --run-id "$RUN_ID" --target analyzed >/dev/null
