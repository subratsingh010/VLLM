# Pipeline A report — BF16 Qwen3-1.7B

**Status:** saved capacity run audited and analyzed; quality evaluation not run.

This report uses only `pipeline_a/results/capacity-20260905-nocache`. Performance
metrics are the values saved by official `vllm bench serve`; the project wrapper
did not recalculate them. Prefix caching was disabled for this capacity run.

## Reproducibility and completeness

- Model: `Qwen/Qwen3-1.7B`
- Revision: `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`
- Precision: BF16 weights, no quantization
- Backend: vLLM 0.28.0 + vLLM-Metal 0.28.0
- Generation: temperature 0, top-p 1, ignore EOS, thinking disabled
- Warm-ups: 2 per point; seed: 20260905
- Percentiles: P50/P95/P99; exact random input/output lengths
- Audit: all 12 point directories contain parseable `official.json`, non-empty
  resource samples, a completed official stdout footer, and the expected request
  count. `rate-1.00` completed before interruption: 12 completed, 0 failed.
- Across the run: 180/180 measured requests completed and 0 failed. The official
  client did not save a distinct timeout counter, so timeout rate is unavailable;
  no timeout appeared as a failed request or saved error.

## Measured performance

All latency and token-timing values are milliseconds. Triples are P50/P95/P99.
Throughput columns are requests/s, output tokens/s, and total tokens/s.

### Token and output length

| Point | Input/output | Concurrency/rate | TTFT | TPOT | ITL | E2E | Req/s | Out/total tok/s | Failed |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| length-i64-o32 | 64/32 | C1 / unlimited | 257/277/282 | 45.8/49.4/50.0 | 46.1/54.2/61.3 | 1,690/1,791/1,808 | 0.591 | 18.90/63.78 | 0 |
| length-i512-o64 | 512/64 | C1 / unlimited | 1,040/1,323/1,343 | 50.2/53.4/54.2 | 50.5/58.0/61.0 | 4,290/4,551/4,639 | 0.232 | 14.83/136.22 | 0 |
| length-i2048-o128 | 2,048/128 | C1 / unlimited | 8,698/13,074/13,191 | 75.2/116.5/127.0 | 65.1/162.4/219.6 | 18,603/27,870/29,321 | 0.050 | 6.38/109.07 | 0 |
| output-i512-o16 | 512/16 | C1 / unlimited | 1,921/2,183/2,267 | 52.9/59.0/59.1 | 54.2/65.9/68.4 | 2,719/2,980/3,055 | 0.365 | 5.83/196.92 | 0 |
| output-i512-o128 | 512/128 | C1 / unlimited | 3,806/5,437/6,000 | 91.5/147.7/158.9 | 79.5/196.8/271.1 | 15,364/24,319/25,188 | 0.064 | 8.25/42.01 | 0 |

### Concurrency

| Point | Input/output | Concurrency/rate | TTFT | TPOT | ITL | E2E | Req/s | Out/total tok/s | Failed |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| concurrency-1 | 512/64 | C1 / unlimited | 2,667/3,226/3,789 | 56.1/58.6/59.0 | 54.4/68.7/72.5 | 6,187/6,753/7,438 | 0.160 | 10.23/94.02 | 0 |
| concurrency-2 | 512/64 | C2 / unlimited | 4,920/5,360/5,425 | 239.8/257.0/259.3 | 233.0/299.1/326.5 | 20,146/21,524/21,593 | 0.114 | 7.27/66.81 | 0 |
| concurrency-4 | 512/64 | C4 / unlimited | 7,816/9,336/9,336 | 217.0/237.1/238.1 | 216.4/277.6/338.4 | 21,521/23,845/23,854 | 0.186 | 11.92/109.49 | 0 |

### Request rate

| Point | Input/output | Concurrency/rate | TTFT | TPOT | ITL | E2E | Req/s | Out/total tok/s | Failed |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| rate-0.10 | 512/64 | C4 / 0.10 | 2,538/4,410/4,650 | 124.9/172.6/173.1 | 114.3/194.6/210.2 | 9,132/15,285/15,558 | 0.095 | 6.08/55.87 | 0 |
| rate-0.25 | 512/64 | C4 / 0.25 | 2,263/4,224/4,307 | 194.7/230.4/239.7 | 162.2/193.8/1,759.5 | 15,958/17,263/17,283 | 0.193 | 12.34/113.37 | 0 |
| rate-0.50 | 512/64 | C4 / 0.50 | 2,227/3,490/3,507 | 200.4/227.5/228.0 | 153.3/187.3/1,662.6 | 15,986/16,228/16,260 | 0.223 | 14.30/131.38 | 0 |
| rate-1.00 | 512/64 | C4 / 1.00 | 3,300/3,664/3,686 | 198.9/234.8/235.3 | 155.4/261.3/1,642.0 | 15,880/18,460/18,470 | 0.234 | 15.00/137.78 | 0 |

## Host-resource observations

| Point | Peak sampled CPU | Minimum available memory | Peak system memory | Peak swap | Peak KV usage |
|---|---:|---:|---:|---:|---:|
| length-i64-o32 | 3.9% | 1.01 GiB | 93.7% | 8.65 GiB | 0.26% |
| length-i512-o64 | 6.9% | 1.04 GiB | 93.5% | 8.80 GiB | 1.36% |
| length-i2048-o128 | 13.5% | 1.03 GiB | 93.5% | 8.87 GiB | 5.05% |
| output-i512-o16 | 5.4% | 1.05 GiB | 93.5% | 8.77 GiB | 1.25% |
| output-i512-o128 | 11.9% | 1.06 GiB | 93.4% | 9.08 GiB | 1.51% |
| concurrency-1 | 10.0% | 1.01 GiB | 93.7% | 8.77 GiB | 1.36% |
| concurrency-2 | 11.6% | 1.05 GiB | 93.5% | 8.69 GiB | 2.73% |
| concurrency-4 | 14.8% | 0.97 GiB | 93.9% | 9.08 GiB | 5.46% |
| rate-0.10 | 6.5% | 0.98 GiB | 93.9% | 9.02 GiB | 4.06% |
| rate-0.25 | 5.7% | 1.19 GiB | 92.6% | 8.94 GiB | 5.42% |
| rate-0.50 | 7.3% | 1.25 GiB | 92.2% | 8.85 GiB | 5.35% |
| rate-1.00 | 7.7% | 1.07 GiB | 93.3% | 8.80 GiB | 5.46% |

CPU is psutil process CPU and is not Metal utilization. The sampler's model RSS
captured only visible host processes (roughly 147–631 MiB) and does not represent
MLX's wired/unified-memory allocation, so it is not used as total model memory.
No reliable non-privileged Metal utilization measurement was available.

## Saturation and operating envelope

Measured facts:

- At the token-length points, P95 TTFT rose from 277 ms to 1,323 ms and then
  13,074 ms; output throughput fell from 18.90 to 14.83 and then 6.38 tokens/s.
- Moving from concurrency 1 to 2 increased P95 E2E from 6.75 s to 21.52 s while
  output throughput fell from 10.23 to 7.27 tokens/s. Concurrency 4 recovered to
  11.92 tokens/s, but P95 E2E remained 23.85 s and P95 TTFT reached 9.34 s.
- From 0.50 to 1.00 offered requests/s, achieved request throughput increased only
  from 0.223 to 0.234 requests/s and output throughput from 14.30 to 15.00 tokens/s,
  while P95 E2E rose from 16.23 s to 18.46 s.

Interpretation:

- The predefined knee rule flags `length-i512-o64` and `concurrency-2`. The sparse
  length matrix means this locates only the first tested degradation, not a precise
  maximum context boundary.
- Unlimited-rate concurrency 2 is the clearest saturation knee. A practical
  latency-sensitive envelope from these tested points is concurrency 1.
- The rate sweep shows an emerging throughput plateau at 0.50 requests/s. The
  strict predefined rule did not flag it because the next P95 rise was below 25%,
  but 1.00 offered requests/s adds little throughput and worsens tail latency.
- Results are noisy/non-monotonic under heavy macOS memory pressure. They support
  a conservative operating envelope, not a theoretical maximum.

## KV cache interpretation

At startup, vLLM-Metal reserved a reported 4.98 GB for paged KV state: 2,713
blocks, 16 tokens per block, across 28 layers. That corresponds to 43,408 token
positions of aggregate active-sequence capacity. It is not the model context
window, disk size, prompt limit, or number of tokens per request. The configured
per-request maximum remained 4,096 tokens.

For example, four simultaneous maximum-length 4,096-token sequences would require
about 16,384 cached token positions, below the reported aggregate capacity. Actual
peak KV usage in this matrix was only 5.46%, because concurrency was capped at four
and tested sequences were at most 2,176 tokens. PagedAttention allocates logical
blocks to active sequences as needed, reducing fragmentation; disabling prefix
caching prevented completed prompt prefixes from being reused between capacity
points but did not disable the per-request KV cache required for decoding.

The nominal 43,408-token figure therefore did not constrain this workload. CPU,
unified-memory pressure, decoding cost, and scheduling/queuing became limiting well
before the reserved KV capacity was exhausted.

## Generated artifacts

- `analysis/capacity-20260905-nocache/capacity.csv`
- `analysis/capacity-20260905-nocache/operating_envelope.json`
- Token-length, concurrency, and request-rate PNG capacity curves in that folder
