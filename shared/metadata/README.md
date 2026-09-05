# Reproducibility metadata

Each measured run writes immutable metadata here and into its pipeline results. Required fields include full model/tokenizer revisions, hashes and byte sizes, dependency-lock hash, Git commit, backend versions, generation settings, input hashes, host identity, load-time definition, and sampler availability. No measured run may reference mutable `main`.
