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
# Rebuilding is expected to produce a byte-different APK — zip timestamps and aapt2
# ordering vary — so the script compares the analysis, not the bytes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${REPO_ROOT}/examples/demo-app"
OUTPUT="${SOURCE_DIR}/demo.apk"

if [[ -n "${DEXATLAS_APKTOOL_JAR:-}" ]]; then
  APKTOOL=(java -jar "${DEXATLAS_APKTOOL_JAR}")
elif command -v apktool >/dev/null 2>&1; then
  APKTOOL=(apktool)
else
  echo "Apktool not found." >&2
  echo "Set DEXATLAS_APKTOOL_JAR to its jar, or put apktool on PATH." >&2
  exit 1
fi

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "${BUILD_DIR}"' EXIT

echo "Building from ${SOURCE_DIR}..."
cp -r "${SOURCE_DIR}" "${BUILD_DIR}/demo"
rm -f "${BUILD_DIR}/demo/demo.apk"

"${APKTOOL[@]}" b "${BUILD_DIR}/demo" -o "${BUILD_DIR}/demo.apk"
mv "${BUILD_DIR}/demo.apk" "${OUTPUT}"

echo "Built ${OUTPUT} ($(wc -c < "${OUTPUT}" | tr -d ' ') bytes)"
echo
echo "Verify it with:"
echo "  dexatlas analyze ${OUTPUT}"
