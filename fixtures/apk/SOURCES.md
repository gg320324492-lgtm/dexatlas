# Third-party test fixtures

These APKs are **not** part of DexAtlas source. They are analysis *inputs* for the
integration test suite, downloaded by `scripts/fetch-fixtures.sh`.

| File                      | Source                                                        | Licence     |
| ------------------------- | ------------------------------------------------------------- | ----------- |
| `TestActivity.apk`        | `androguard/androguard` @ `tests/data/APK`                   | Apache-2.0  |
| `multidex.apk`            | `androguard/androguard` @ `tests/data/APK`                   | Apache-2.0  |

All are self-contained test applications built by the androguard project for its own
tests. None contains third-party application code, credentials or user data.

`multidex.apk` carries two dexes. It is what makes the Smali fallback test real:
Apktool decodes it to `smali/` and `smali_classes2/`, and the bug that test guards
against could only ever be caught by an APK with a second dex.

Any fixture added here must be either authored by this project or carry an explicit
licence permitting redistribution. See `CONTRIBUTING.md`.
