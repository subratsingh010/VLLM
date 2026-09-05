#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT/models/pipeline_a"
shasum -a 256 -c "$ROOT/pipeline_a/config/artifacts.sha256"
