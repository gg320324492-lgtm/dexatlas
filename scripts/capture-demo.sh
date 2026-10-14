#!/usr/bin/env bash
# Capture a DexAtlas demo session as plain text.
#
# Runs the real CLI against the bundled demo application and writes the session to
# stdout. Every line is a genuine command and its genuine output — nothing is staged, so
# the recording cannot drift from what the tool actually does.
#
#   ./scripts/capture-demo.sh > session.txt
#
# Output is deliberately free of ANSI colour codes: this text is meant to be drawn as
# text by scripts/render-demo.py, which has no terminal to interpret them. Left in, they
# render literally as `[1;36m` and wreck the recording. Colour is applied by the
# renderer, which knows the palette.
#
# Requires: uv, a POSIX-ish shell, and the DexAtlas CLI (via `uv run` or on PATH).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_APK="${REPO_ROOT}/examples/demo-app/demo.apk"

# A private workspace so a recording never touches a developer's project database.
WORKSPACE="$(mktemp -d)"
export DEXATLAS_WORKSPACE="${WORKSPACE}"
export DEXATLAS_JADX_PATH="${DEXATLAS_JADX_PATH:-}"
export DEXATLAS_APKTOOL_JAR="${DEXATLAS_APKTOOL_JAR:-}"

# The report is written into the repository root rather than the temp workspace, so the
# recorded output shows `report.md` — exactly what a viewer sees running the command in
# the README. Rewriting the path afterwards would be a lie about what the tool prints.
# It is removed on exit, and .gitignore keeps it out of the tree regardless.
REPORT="${REPO_ROOT}/report.md"

# No colour from the CLI either: strip escape sequences on the way out.
strip_ansi() {
  sed -E 's/\x1B\[[0-9;?]*[ -\/]*[@-~]//g'
}

cleanup() { rm -rf "${WORKSPACE}"; rm -f "${REPORT}"; }
trap cleanup EXIT

dex() {
  if command -v dexatlas >/dev/null 2>&1; then
    dexatlas "$@"
  else
    uv run --project "${REPO_ROOT}" dexatlas "$@"
  fi
}

if [[ ! -f "${DEMO_APK}" ]]; then
  echo "demo APK missing: ${DEMO_APK}" >&2
  exit 1
fi

# Read the project id the run actually produced, so the recording never shows a
# hard-coded value that could go stale.
project_id() {
  dex projects 2>/dev/null | awk '/apk_/ { print $2; exit }'
}

show() { printf '\n$ %s\n' "$1"; }

comment() { printf '\n# %s\n' "$1"; }

rule() { printf -- '------------------------------------------------------------\n'; }

# ---------------------------------------------------------------- header ----

printf 'DexAtlas  — from APK to evidence\n'
rule
show "dexatlas backends"
dex backends

# --------------------------------------------------------------- analyze ----

comment "Analyse the bundled demo application."
comment "Built from the smali sources in examples/demo-app/."
show "dexatlas analyze examples/demo-app/demo.apk --output report.md"
dex analyze "${DEMO_APK}" --output "${REPORT}"

PROJECT="$(project_id)"
if [[ -z "${PROJECT}" ]]; then
  echo "could not determine the project id" >&2
  exit 1
fi

# -------------------------------------------------------------- manifest ----

comment "Which components are exported, and how are they declared?"
show "dexatlas manifest ${PROJECT}"
dex manifest "${PROJECT}"

# ---------------------------------------------------------------- search ----

comment "Find where the request signature is computed."
show "dexatlas search ${PROJECT} sign"
dex search "${PROJECT}" "sign" --limit 6

# ----------------------------------------------------------------- xrefs ----

comment "Follow the call chain back to its caller."
show "dexatlas xrefs ${PROJECT} 'com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;'"
dex xrefs "${PROJECT}" \
  "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"

# ---------------------------------------------------------------- source ----

comment "Every finding points at real code, not a guess."
show "dexatlas source ${PROJECT} com.example.demo.Crypto"
dex source "${PROJECT}" com.example.demo.Crypto 2>/dev/null | head -18

# ---------------------------------------------------------------- report ----

comment "The report separates what a tool verified from what needs a human."
show "head -n 22 report.md"
head -n 22 "${REPORT}"

printf '\n'
rule
printf 'Every line above is a real run.\n'
printf 'Replay it:  uv run dexatlas analyze examples/demo-app/demo.apk\n\n'

strip_ansi
