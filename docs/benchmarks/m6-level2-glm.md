# M6 level-2 acceptance rerun — GLM-5.3-Flash via the local model gateway

**Measured**: 065e89f · model `auto/glm-5.3-flash` · gateway `http://127.0.0.1:3425/v1` (local, no key) · three rounds x 20 frozen tasks x 3 configurations · budget per request 16,384 tokens, per task 24,000 tokens, 40 plan steps, 16 iterations.

**Acceptance line** ([service-regression-set.md](service-regression-set.md) §5): DexAtlas ≥16/20 (≥80%) per round and ≥54/60 (≥90%) across the three rounds combined. Empty answers and budget exhaustion count as failures; the task set may not be changed to raise the rate.

**Traces**: [r1](m6-level2-glm-traces-r1.json) · [r2](m6-level2-glm-traces-r2.json) · [r3](m6-level2-glm-traces-r3.json) — three configurations per round; the scorer alone read `benchmarks/tasks/`. This run postdates the de-platformisation cleanup (`065e89f`); the earlier MiniMax-M3.1-Flash measurements ([m6-level2-retest4.md](m6-level2-retest4.md)) remain committed as the historical baseline and are not mixed with these numbers.

## The eight metrics (three rounds combined, per configuration)

| Configuration | Correct answers | Evidence grounding | Unsupported assertions | False positives | Tool success | Tokens | Duration |
|---|---|---|---|---|---|---|---|
| A | 16/60 = 26.7% | 0.0% | 100.0% | 0.0% | 100.0% | 214,580 | 930.9s |
| B | 22/60 = 36.7% | 0.0% | 100.0% | 0.0% | 100.0% | 215,869 | 869.5s |
| DexAtlas | 51/60 = 85.0% | 95.5% | 4.5% | 0.0% | 100.0% | 949,093 | 1976.4s |

## DexAtlas against the acceptance line

| Round | Score | Verdict |
|---|---|---|
| Round 1 | 17/20 = 85.0% | meets the per-round line |
| Round 2 | 17/20 = 85.0% | meets the per-round line |
| Round 3 | 17/20 = 85.0% | meets the per-round line |
| Three rounds combined | 51/60 = 85.0% | below the ≥54/60 (≥90%) acceptance line |

## The tasks that did not pass every round

| Task | Rounds passed | Per-round outcome |
|---|---|---|
| `multidex.dex-file-count` | 0/3 | r1: fail, r2: fail, r3: fail |
| `strings.api-key.demo` | 1/3 | r1: fail, r2: fail, r3: pass |
| `overloads.method-identity.descriptor-distinguishes` | 1/3 | r1: fail, r2: fail, r3: pass |
| `manifest.permission.count-obfuscated` | 2/3 | r1: pass, r2: pass, r3: fail |
| `unanswerable.demo-declares-no-receiver` | 2/3 | r1: pass, r2: pass, r3: fail |

## Disclosures

- The gateway is the operator's local model gateway; no API key was used, and none is recorded in the traces or this report.
- A/B and DexAtlas ran under the same task budget but different answer envelopes (the agent's JSON answers need more room), the same disclosure the earlier measurements carry.
- The three configurations saw the same questions and the same model; the marking scheme was held by the scorer alone.
- No improvement is claimed beyond what these numbers support: the three-round total is 51/60 = 85.0%, which is **below** the ≥54/60 (≥90%) acceptance line. The per-round line (≥16/20) was met in every round.
- The historical MiniMax-M3.1-Flash three-round result (49/60 = 81.7%) remains the committed baseline; this run is a different model and the two are not combined.
