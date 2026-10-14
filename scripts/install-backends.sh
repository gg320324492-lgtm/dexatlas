#!/usr/bin/env bash
# Install the external analysis backends CI needs, and report what was installed.
#
# Shared by the test and integration jobs so the two cannot drift. Pinning is deliberate:
# an unpinned download would make a green run meaningless and a red run unexplainable.

set -euo pipefail

JADX_VERSION="${JADX_VERSION:-1.5.2}"
APKTOOL_VERSION="${APKTOOL_VERSION:-2.11.1}"
INSTALL_ROOT="${INSTALL_ROOT:-${RUNNER_TEMP:-/tmp}/dexatlas-backends}"

mkdir -p "${INSTALL_ROOT}"

# The jadx archive unpacks directly into bin/ and lib/ — there is no version-named
# top-level directory, so it gets its own directory rather than a rename afterwards.
if [[ ! -x "${INSTALL_ROOT}/jadx/bin/jadx" ]]; then
  echo "Installing JADX ${JADX_VERSION}..."
  curl -fsSL --retry 3 -o "${INSTALL_ROOT}/jadx.zip" \
    "https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/jadx-${JADX_VERSION}.zip"
  mkdir -p "${INSTALL_ROOT}/jadx"
  unzip -q "${INSTALL_ROOT}/jadx.zip" -d "${INSTALL_ROOT}/jadx"
  chmod +x "${INSTALL_ROOT}/jadx/bin/"*
  rm -f "${INSTALL_ROOT}/jadx.zip"
fi

if [[ ! -f "${INSTALL_ROOT}/apktool.jar" ]]; then
  echo "Installing Apktool ${APKTOOL_VERSION}..."
  curl -fsSL --retry 3 -o "${INSTALL_ROOT}/apktool.jar" \
    "https://github.com/iBotPeaches/Apktool/releases/download/v${APKTOOL_VERSION}/apktool_${APKTOOL_VERSION}.jar"
fi

# Both need a JRE on PATH, which the caller is responsible for providing.
command -v java >/dev/null 2>&1 || { echo "java not found on PATH" >&2; exit 1; }

JADX_VERSION_ACTUAL="$("${INSTALL_ROOT}/jadx/bin/jadx" --version 2>/dev/null | head -1 || echo unknown)"
APKTOOL_VERSION_ACTUAL="$(java -jar "${INSTALL_ROOT}/apktool.jar" --version 2>/dev/null | head -1 || echo unknown)"

echo "jadx    ${JADX_VERSION_ACTUAL}"
echo "apktool ${APKTOOL_VERSION_ACTUAL}"

if [[ "${JADX_VERSION_ACTUAL}" == "unknown" || "${APKTOOL_VERSION_ACTUAL}" == "unknown" ]]; then
  echo "a backend failed to run after installation" >&2
  exit 1
fi

# Make the install discoverable to DexAtlas without hard-coded paths per job.
export PATH="${INSTALL_ROOT}/jadx/bin:${PATH}"
export DEXATLAS_JADX_PATH="${INSTALL_ROOT}/jadx/bin/jadx"
export DEXATLAS_APKTOOL_JAR="${INSTALL_ROOT}/apktool.jar"

{
  echo "${INSTALL_ROOT}/jadx/bin" >> "${GITHUB_PATH:-/dev/null}" || true
  echo "DEXATLAS_JADX_PATH=${INSTALL_ROOT}/jadx/bin/jadx" >> "${GITHUB_ENV:-/dev/null}" || true
  echo "DEXATLAS_APKTOOL_JAR=${INSTALL_ROOT}/apktool.jar" >> "${GITHUB_ENV:-/dev/null}" || true
} 2>/dev/null || true
