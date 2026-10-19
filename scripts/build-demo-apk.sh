#!/usr/bin/env bash
# Rebuild the bundled demo APK from source.
#
# The APK in this directory is committed so a stranger can run an analysis immediately
# after cloning. This script proves it is not a mystery binary: every class in it is the
# smali in this directory, and rebuilding reproduces it.
#
# Requires Apktool (https://github.com/iBotPeaches/Apktool/releases) and a JDK 21+.
#
#   DEXATLAS_APKTOOL_JAR=/path/to/apktool.jar ./scripts/build-demo-apk.sh
#
# There are five first-party samples under examples/; scripts/build-test-apks.sh
# builds all of them. This script builds only the demo application, and delegates to
# it so there is one implementation of the build.
#
# Rebuilding is expected to produce a byte-different APK — zip timestamps and aapt2
# ordering vary — so the test suite compares the analysis, not the bytes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec bash "${REPO_ROOT}/scripts/build-test-apks.sh" demo-app
