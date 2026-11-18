# Case studies

Three complete walkthroughs of DexAtlas analyses, written from real runs.
Every number below was produced by the commands shown, on the sample named,
and every conclusion carries the evidence record or locator it came from.

These documents are written to be **reviewed by a potential user**: each one
states the problem it answers, the scope it covers, the reproducible commands
it ran, the evidence behind every claim, its conclusions, its limits, and
what to do next. Reading them requires no DexAtlas installation — only the
willingness to check a locator.

**What these studies are not:** they are not penetration tests, and they do
not classify any sample as malware or assert that anything is exploitable.
Static facts — an exported component, a credential-shaped string, a call
edge — are reported as facts about the bytes, with the judgement left to the
reader. Samples are first-party; their suspicious-looking constants are inert
placeholders committed beside the APK.

**Attachments:** [`attachments/`](attachments/) holds four evidence packages
and the loose report files the walkthroughs link to — **four packages, twelve
report files, sixteen files in all**. Which file belongs to which study is
spelled out in the walkthroughs themselves: study 1 links `demo-report.*`,
study 2 links `obfuscated-report.*` and `multidex-report.*` (the multi-DEX
appendix), study 3 links `api-integration-report.*`. Open the HTML with no
network, or unzip a package and check its manifest hashes; a reader does not
need to run DexAtlas to review the evidence, only to reproduce it.

| # | Case study | Sample | What it shows |
|---|---|---|---|
| 1 | [From upload to evidence chain](demo-app-walkthrough.md) | [`examples/demo-app/demo.apk`](../../examples/demo-app/demo.apk) | The full tool chain: analyze, manifest, search, source, cross-references, and the eleven evidence records behind them — the complete end-to-end walkthrough |
| 2 | [Reading an obfuscated app](obfuscated-app.md) | [`examples/obfuscated-app/obfuscated.apk`](../../examples/obfuscated-app/obfuscated.apk), plus a multi-DEX appendix on [`examples/multidex-app/multidex.apk`](../../examples/multidex-app/multidex.apk) | What survives name obfuscation, what the string index still finds, how the index records a class defined in two DEX files at once — and where the capability boundary sits |
| 3 | [Integrating from Python](api-integration.md) | [`examples/demo-app/demo.apk`](../../examples/demo-app/demo.apk), via the REST API and the MCP server | The wire contract: upload → analyze → poll → query → report over HTTP, the same analysis over eleven read-only MCP tools, and a minimal Python client |

Three walkthroughs cover three first-party APKs — `demo-app`, `obfuscated-app`
and `multidex-app` (the multi-DEX appendix) — with case studies 1 and 3 both
analysing the same `demo-app` APK. The four evidence packages come from
**four separate analyses**, one package per analysis, and every manifest
records the run it was made from: `run_e8e49384ab5246ab` (study 1's
attachment), `run_dd897202eba74e28` (study 2's), `run_4fde2fa0b5254ccb`
(study 2's multi-DEX appendix) and `run_fc8e432d4d094350` (study 3's).

Those four are the runs the packages were made from, not the only runs the
material mentions: the three walkthroughs quote seven runs in total, because
each study also quotes the session it narrates before the packaged one.

Two things a reader will hit while checking that. Studies 1 and 3 analyse the
same bytes, so every count in their two reports agrees while the run id and
the timing differ — same input, two runs, two ids. And a package's manifest
records the hash of the `report.json` **inside the package**, which is
byte-for-byte the loose `report.json` of that same analysis. The measured
hashes and the run ids are in [the third-package
report](../reports/case-studies-third-package.md); the earlier
[correspondence report](../reports/case-studies-run-correspondence.md)
records what the attachment set looked like **before** that round and is
kept for the comparison.

All three APK samples are **first-party**: built from smali sources committed
beside them, rebuildable with `scripts/build-test-apks.sh`, and free of
third-party code. They exist so that a reader can reproduce every step
without fetching anything.

## Reproducing

```bash
uv sync --extra dev --extra analysis
uv run dexatlas analyze examples/demo-app/demo.apk
```

Backend versions used in all three studies: androguard 4.1.4, apktool 2.11.1,
jadx 1.5.2, Python 3.12, on Windows 11. Analysis times are reported per run
and will differ on other machines; the symbol and evidence counts are
deterministic for a given sample and backend set.

## Reading them as a potential user

- **Case 1** answers "what will I get, and can I check it?" — start there.
- **Case 2** answers "what happens when the names are gone?" — the honest
  boundary of a static index on obfuscated input.
- **Case 3** answers "how do I call this from my own code?" — the REST and
  MCP contracts, with the same evidence records behind them.

Every study's *Limits* section states what the analysis does not establish;
the AI-assisted analysis case study is planned against the M6 agent records
and is deliberately absent until those records exist — no simulated results
are presented in their place.
