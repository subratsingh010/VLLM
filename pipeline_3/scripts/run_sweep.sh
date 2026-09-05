#!/bin/sh
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: $0 TUNING_RUN_DIR --dry-run|--execute [--resume]" >&2
  exit 2
fi
RUN=$(CDPATH= cd -- "$1" && pwd)
MODE=$2
EXTRA=${3:-}
test -f "$RUN/PLAN.json" || { echo "missing tuning plan: $RUN/PLAN.json" >&2; exit 1; }
test "$MODE" = "--dry-run" || test "$MODE" = "--execute" || { echo "choose --dry-run or --execute" >&2; exit 2; }
test -z "$EXTRA" || test "$EXTRA" = "--resume" || { echo "only --resume is allowed" >&2; exit 2; }
SERVE_CMD=$(jq -r '.serve_cmd' "$RUN/PLAN.json")
BENCH_CMD=$(jq -r '.bench_cmd' "$RUN/PLAN.json")
test "$(jq -r '.candidate_count' "$RUN/PLAN.json")" -le 6 || { echo "candidate safety limit exceeded" >&2; exit 1; }
DRY=
if [ "$MODE" = "--dry-run" ]; then DRY=--dry-run; fi
RESUME=
if [ "$EXTRA" = "--resume" ]; then RESUME=--resume; fi
export VLLM_METAL_MEMORY_FRACTION=0.70
exec /Users/subrat/.venv-vllm-metal/bin/vllm bench sweep serve \
  --serve-cmd "$SERVE_CMD" \
  --bench-cmd "$BENCH_CMD" \
  --serve-params "$RUN/serve_params.json" \
  --bench-params "$RUN/bench_params.json" \
  --link-vars max_num_seqs=max_concurrency \
  --output-dir "$RUN/official_sweep" \
  --experiment-name tuning \
  --num-runs 1 \
  --server-ready-timeout 180 \
  $DRY $RESUME
