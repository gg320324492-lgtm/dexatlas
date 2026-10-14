# Third-party test fixtures

These APKs are **not** part of DexAtlas source. They are analysis *inputs* for the
integration test suite, downloaded by `scripts/fetch-fixtures.sh`.

| File                      | Source                                                        | Licence     |
| ------------------------- | ------------------------------------------------------------- | ----------- |
| `TestActivity.apk`        | `androguard/androguard` @ `tests/data/APK`                   | Apache-2.0  |
| `Test-debug.apk`          | `androguard/androguard` @ `tests/data/APK`                   | Apache-2.0  |
| `AndroidManifest_ShortName.apk` | `androguard/androguard` @ `tests/data/APK`             | Apache-2.0  |

All three are self-contained test applications built by the androguard project for its
own tests. None contains third-party application code, credentials or user data.

Any fixture added here must be either authored by this project or carry an explicit
licence permitting redistribution. See `CONTRIBUTING.md`.
