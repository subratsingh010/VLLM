# Pipeline B scripts

These commands implement separate, user-controlled stages. They never chain model
conversion, serving, and benchmarking automatically.

- `validate_variant.py`: configuration/source validation only.
- `prepare_variant.py`: create a new immutable run directory.
- `quantize.py`: plan by default; convert only with `--execute --confirm RUN_ID`.
- `verify_artifacts.py`: verify format, quantization metadata, size, and SHA-256.
- `serve_variant.sh`: start one manually selected, verified variant.
- `benchmark_variant.sh`: require a healthy server, then invoke official vLLM.
- `validate_benchmark.py`: check all official outputs and request counts.
- `analyze_variant.sh`: analyze a structurally complete saved benchmark.
- `finalize_variant.py`: mark an analyzed run eligible for comparison.
- `mark_state.py`: explicit server-stop recovery/state recording.
