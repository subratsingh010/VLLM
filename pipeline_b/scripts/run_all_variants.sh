#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PYTHON="$ROOT/.venv/bin/python"
DEFAULT_VARIANTS="fp16 int8_mlx int4_mlx"

usage() {
  echo "usage: $0 --batch-id ID --execute --confirm ID [--variants 'fp16 int8_mlx int4_mlx']" >&2
}

BATCH_ID=
CONFIRM=
EXECUTE=false
VARIANTS=$DEFAULT_VARIANTS
while [ "$#" -gt 0 ]; do
  case "$1" in
    --batch-id) BATCH_ID=${2:-}; shift 2 ;;
    --confirm) CONFIRM=${2:-}; shift 2 ;;
    --variants) VARIANTS=${2:-}; shift 2 ;;
    --execute) EXECUTE=true; shift ;;
    *) usage; exit 2 ;;
  esac
done

test -n "$BATCH_ID" || { usage; exit 2; }
test "$EXECUTE" = true || { echo "refusing to start expensive work without --execute" >&2; exit 2; }
test "$CONFIRM" = "$BATCH_ID" || { echo "--confirm must exactly match --batch-id" >&2; exit 2; }
case "$BATCH_ID" in
  *[!A-Za-z0-9._-]*|'') echo "batch id contains unsupported characters" >&2; exit 2 ;;
esac

for VARIANT in $VARIANTS; do
  case "$VARIANT" in
    fp16|int8_mlx|int4_mlx) ;;
    *) echo "unsupported batch variant: $VARIANT" >&2; exit 2 ;;
  esac
done

SERVER_PID=
ACTIVE_VARIANT=
ACTIVE_RUN_ID=
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  if [ -n "$ACTIVE_VARIANT" ] && [ -n "$ACTIVE_RUN_ID" ]; then
    STATUS_FILE="$ROOT/pipeline_b/results/$ACTIVE_VARIANT/$ACTIVE_RUN_ID/RUN_STATUS.json"
    if [ -f "$STATUS_FILE" ] && [ "$(jq -r '.status' "$STATUS_FILE")" = "serving_started" ]; then
      "$PYTHON" -m pipeline_b.scripts.mark_state \
        --variant "$ACTIVE_VARIANT" --run-id "$ACTIVE_RUN_ID" --target serving_stopped >/dev/null || true
    fi
  fi
}
trap cleanup EXIT INT TERM

cd "$ROOT"
for VARIANT in $VARIANTS; do
  RUN_ID="$VARIANT-$BATCH_ID"
  RUN="$ROOT/pipeline_b/results/$VARIANT/$RUN_ID"
  echo "=== $VARIANT: validate and prepare ($RUN_ID) ==="
  "$PYTHON" -m pipeline_b.scripts.validate_variant --variant "$VARIANT"
  "$PYTHON" -m pipeline_b.scripts.prepare_variant --variant "$VARIANT" --run-id "$RUN_ID"

  if [ "$VARIANT" = "int8_mlx" ] || [ "$VARIANT" = "int4_mlx" ]; then
    echo "=== $VARIANT: convert model ==="
    "$PYTHON" -m pipeline_b.scripts.quantize \
      --variant "$VARIANT" --run-id "$RUN_ID" --execute --confirm "$RUN_ID"
  fi

  echo "=== $VARIANT: verify artifacts ==="
  "$PYTHON" -m pipeline_b.scripts.verify_artifacts --variant "$VARIANT" --run-id "$RUN_ID"

  ACTIVE_VARIANT=$VARIANT
  ACTIVE_RUN_ID=$RUN_ID
  echo "=== $VARIANT: start server ==="
  "$ROOT/pipeline_b/scripts/serve_variant.sh" "$VARIANT" "$RUN_ID" \
    >"$RUN/serving/server.log" 2>&1 &
  SERVER_PID=$!

  PORT=$(jq -r --arg v "$VARIANT" '.variants[$v].port' "$ROOT/pipeline_b/config/variants.json")
  READY=false
  ATTEMPT=0
  while [ "$ATTEMPT" -lt 180 ]; do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "server exited before becoming ready; inspect $RUN/serving/server.log" >&2
      exit 1
    fi
    if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
      READY=true
      break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
  done
  test "$READY" = true || { echo "server readiness timed out; inspect $RUN/serving/server.log" >&2; exit 1; }

  echo "=== $VARIANT: official benchmark ==="
  "$ROOT/pipeline_b/scripts/benchmark_variant.sh" "$VARIANT" "$RUN_ID"

  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=
  ACTIVE_VARIANT=
  ACTIVE_RUN_ID=

  echo "=== $VARIANT: analyze and finalize ==="
  "$ROOT/pipeline_b/scripts/analyze_variant.sh" "$VARIANT" "$RUN_ID"
  "$PYTHON" -m pipeline_b.scripts.finalize_variant --variant "$VARIANT" --run-id "$RUN_ID"
  echo "=== $VARIANT complete: $RUN ==="
done

echo "All requested Pipeline B variants completed."
