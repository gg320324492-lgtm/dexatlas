# Case studies

Two complete walkthroughs of DexAtlas analyses, written from real runs. Every
number below was produced by the commands shown, on the sample named, and every
conclusion carries the evidence record or locator it came from.

| # | Case study | Sample | What it shows |
|---|---|---|---|
| 1 | [From upload to evidence chain](demo-app-walkthrough.md) | [`examples/demo-app/demo.apk`](../../examples/demo-app/demo.apk) | The full path: analyze, manifest, search, source, cross-references, and the eleven evidence records behind them |
| 2 | [Reading an obfuscated app](obfuscated-app.md) | [`examples/obfuscated-app/obfuscated.apk`](../../examples/obfuscated-app/obfuscated.apk), plus a multi-DEX appendix on [`examples/multidex-app/multidex.apk`](../../examples/multidex-app/multidex.apk) | What survives name obfuscation, what the string index still finds, and how the index records a class that is defined in two DEX files at once |

Both samples are **first-party**: built from smali sources committed beside
them, rebuildable with `scripts/build-test-apks.sh`, and free of third-party
code. They exist so that a reader can reproduce every step without fetching
anything.

## Reproducing

```bash
uv sync --extra analysis
uv run dexatlas analyze examples/demo-app/demo.apk
```

Backend versions used in both studies: androguard 4.1.4, apktool 2.11.1,
jadx 1.5.2, Python 3.12, on Windows 11. Analysis times are reported per run and
will differ on other machines; the symbol and evidence counts are deterministic
for a given sample and backend set.
