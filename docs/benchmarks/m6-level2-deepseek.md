# M6 level-2 acceptance rerun — DeepSeek-V4.1-Flash via the local model gateway

**Measured**: e13e048 · model `auto/deepseek-v4.1-flash` · gateway `http://127.0.0.1:3425/v1` (local, no key) · three rounds x 20 frozen tasks x 3 configurations · budget per request 16,384 tokens, per task 96,000 tokens, 80 plan steps, 32 iterations, 1,200 s per task.

**Acceptance line** ([service-regression-set.md](service-regression-set.md) §5): DexAtlas ≥16/20 (≥80%) per round and ≥54/60 (≥90%) across the three rounds combined. Empty answers and budget exhaustion count as failures; the task set may not be changed to raise the rate.

**Traces**: [r1](m6-level2-deepseek-traces-r1.json) · [r2](m6-level2-deepseek-traces-r2.json) · [r3](m6-level2-deepseek-traces-r3.json) — three configurations per round; the scorer alone read `benchmarks/tasks/`. This run postdates the de-platformisation cleanup and the agent-instruction hardening (DEX-file evidence record, `evidence_catalog` in `get_project_status`, literal-word and findings-precision rules, read-the-class-source rule); the earlier GLM-5.3-Flash run ([m6-level2-glm.md](m6-level2-glm.md)) and the MiniMax-M3.1-Flash baseline ([m6-level2-retest4.md](m6-level2-retest4.md)) remain committed and are reported separately, never combined.

## The eight metrics (three rounds combined, per configuration)

| Configuration | Correct answers | Evidence grounding | Unsupported assertions | False positives | Tool success | Tokens | Duration |
|---|---|---|---|---|---|---|---|
| A | 19/60 = 31.7% | 0.0% | 100.0% | 0.0% | 100.0% | 75,600 | 188.0s |
| B | 23/60 = 38.3% | 0.0% | 100.0% | 0.0% | 100.0% | 80,853 | 181.1s |
| DexAtlas | 56/60 = 93.3% | 94.7% | 5.3% | 0.0% | 99.2% | 738,812 | 504.6s |

## DexAtlas against the acceptance line

| Round | Score | Verdict |
|---|---|---|
| Round 1 | 18/20 = 90.0% | meets the per-round line |
| Round 2 | 20/20 = 100.0% | meets the per-round line |
| Round 3 | 18/20 = 90.0% | meets the per-round line |
| Three rounds combined | 56/60 = 93.3% | meets the ≥54/60 (≥90%) acceptance line |

## The tasks that did not pass every round

| Task | Rounds passed | Per-round outcome |
|---|---|---|
| `strings.api-key.demo` | 1/3 | r1: fail, r2: pass, r3: fail |
| `strings.telemetry-url.obfuscated` | 2/3 | r1: pass, r2: pass, r3: fail |
| `multidex.dex-file-count` | 2/3 | r1: fail, r2: pass, r3: pass |

## Disclosures

- The gateway is the operator's local model gateway; no API key was used, and none is recorded in the traces or this report.
- A/B and DexAtlas ran under the same task budget but different answer envelopes (the agent's JSON answers need more room), the same disclosure the earlier measurements carry.
- The three configurations saw the same questions and the same model; the marking scheme was held by the scorer alone.
- The GLM-5.3-Flash run ([m6-level2-glm.md](m6-level2-glm.md), 53/60 = 88.3%) and the MiniMax-M3.1-Flash baseline ([m6-level2-retest4.md](m6-level2-retest4.md), 49/60 = 81.7%) are different models on the same frozen set; the three are reported separately and never combined.
- No improvement is claimed beyond what these numbers support. This run's combined score is 56/60 = 93.3%, which meets the ≥54/60 (≥90%) acceptance line.
