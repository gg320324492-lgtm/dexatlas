#!/usr/bin/env bash
# Build every self-authored test APK from its smali sources.
#
# These samples are the first-party fixtures the Phase 1 acceptance checklist calls
# for: five APKs built by this project, each exercising a different part of the
# analysis pipeline. They are committed so a stranger can analyse something
# immediately after cloning, and this script proves none of them is a mystery
# binary — every class in them is the smali in the tree beside it.
#
# Requires Apktool (https://github.com/iBotPeaches/Apktool/releases) and a JDK 21+.
#
#   DEXATLAS_APKTOOL_JAR=/path/to/apktool.jar ./scripts/build-test-apks.sh
#   ./scripts/build-test-apks.sh multidex-app    # just one of them
#
# Rebuilding is expected to produce a byte-different APK — zip timestamps and aapt2
# ordering vary — so the test suite compares the analysis, not the bytes.
#
# The five samples, and what each one is for:
#
#   demo-app       the general case: components, permissions, cross-references
#   multidex-app   two dexes, so smali/ and smali_classes2/ both exist
#   obfuscated-app one-letter packages, classes and methods, no source hints
#   strings-app    mostly string constants, for the search index
#   wide-app       an interface with two implementations and a factory

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${DEXATLAS_APKTOOL_JAR:-}" ]]; then
  APKTOOL=(java -jar "${DEXATLAS_APKTOOL_JAR}")
elif command -v apktool >/dev/null 2>&1; then
  APKTOOL=(apktool)
else
  echo "Apktool not found." >&2
  echo "Set DEXATLAS_APKTOOL_JAR to its jar, or put apktool on PATH." >&2
  exit 1
fi

#: sample directory name -> the APK file name inside it
SAMPLES=(
  "demo-app:demo.apk"
  "multidex-app:multidex.apk"
  "obfuscated-app:obfuscated.apk"
  "strings-app:strings.apk"
  "wide-app:wide.apk"
)

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "${BUILD_DIR}"' EXIT

#: An optional argument selects a single sample; with none, every sample is built.
ONLY="${1:-}"

if [[ -n "${ONLY}" ]]; then
  known=0
  for entry in "${SAMPLES[@]}"; do
    [[ "${entry%%:*}" == "${ONLY}" ]] && known=1
  done
  if [[ "${known}" -eq 0 ]]; then
    echo "Unknown sample: ${ONLY}" >&2
    echo "Known samples: ${SAMPLES[*]%%:*}" >&2
    exit 1
  fi
fi

for entry in "${SAMPLES[@]}"; do
  name="${entry%%:*}"
  apk_name="${entry##*:}"
  source_dir="${REPO_ROOT}/examples/${name}"
  output="${source_dir}/${apk_name}"

  if [[ -n "${ONLY}" && "${name}" != "${ONLY}" ]]; then
    continue
  fi

  if [[ ! -d "${source_dir}" ]]; then
    echo "Skipping ${name}: no such directory" >&2
    continue
  fi

  echo "Building ${name} -> ${apk_name}"
  cp -r "${source_dir}" "${BUILD_DIR}/${name}"
  rm -f "${BUILD_DIR}/${name}/${apk_name}"

  "${APKTOOL[@]}" b "${BUILD_DIR}/${name}" -o "${BUILD_DIR}/${apk_name}" >/dev/null
  mv "${BUILD_DIR}/${apk_name}" "${output}"

  dex_count="$(python -c "
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    print(sum(1 for n in archive.namelist() if n.endswith('.dex')))
" "${output}")"

  echo "  ${output} ($(wc -c < "${output}" | tr -d ' ') bytes, ${dex_count} dex)"
done

echo
if [[ -n "${ONLY}" ]]; then
  echo "Verify it with:"
  echo "  dexatlas analyze examples/${ONLY}/"
else
  echo "Verify them with:"
  echo "  dexatlas analyze examples/demo-app/demo.apk"
fi
