"""Regression tests for the stale texts the packaged-exe recheck uncovered.

The second acceptance of the packaged desktop exe (2026-11-26; the report
lives in ``.scratch/phase5-exe-recheck.md``) passed all four of its criteria,
but reading the shipped UI surfaced three sentences that had stopped being
true:

1. the findings page's error text hard-coded ``127.0.0.1:8618`` — the port the
   workbench used to listen on — while the desktop app has been talking to the
   sidecar's *dynamic* port since PR #20;
2. the analysis page's footnote claimed the workbench has no
   ``/api/backends`` endpoint, but the endpoint exists (PR #18) and answers
   200 against the very sidecar the page is talking to; and
3. the reports page rendered the backend's UTC timestamp verbatim, so a report
   written at 18:46 UTC showed as ``2026-11-25 18:46:07`` on a UTC+8 machine
   instead of ``2026-11-26 02:46:07``.

The desktop app has no test runner in this repository, so — like
``test_desktop_stage_mapping.py`` — the behaviour is checked by executing the
shipped plain-ESM modules with Node, and the wiring is checked by reading the
page sources.  Every test here goes red on the pre-fix tree.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_SRC = ROOT / "desktop" / "src"
FINDINGS_PAGE = DESKTOP_SRC / "pages" / "FindingsPage.tsx"
ANALYSIS_PAGE = DESKTOP_SRC / "pages" / "Analysis.tsx"
REPORTS_PAGE = DESKTOP_SRC / "pages" / "ReportsPage.tsx"
SETTINGS_PAGE = DESKTOP_SRC / "pages" / "SettingsPage.tsx"
CLIENT = DESKTOP_SRC / "api" / "client.ts"
TYPES = DESKTOP_SRC / "api" / "types.ts"
ADDRESS_MODULE = DESKTOP_SRC / "backendAddress.js"
DATETIME_MODULE = DESKTOP_SRC / "datetime.js"
WORKBENCH_APP = ROOT / "src" / "dexatlas" / "workbench" / "app.py"

#: The probe: load the shipped module, call the named function with the given
#: arguments, print the results as JSON.  Reading the call list from stdin
#: keeps the shell out of it entirely.
PROBE = """
const mod = await import(process.argv[1]);
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const calls = JSON.parse(Buffer.concat(chunks).toString("utf8"));
const results = calls.map((call) => mod[call.fn](...call.args));
process.stdout.write(JSON.stringify(results));
"""

#: The timestamp the acceptance run saw: the backend stores
#: ``datetime.now(UTC).isoformat()``, so the fraction carries six digits and
#: the string ends with an explicit offset.
UTC_ISO = "2026-11-25T18:46:07.123456+00:00"


def _node() -> str:
    exe = shutil.which("node")
    if exe is None:
        pytest.fail(
            "Node.js is required for the desktop stale-copy tests: they execute "
            "desktop/src/backendAddress.js and desktop/src/datetime.js directly, "
            "because CI's Python job installs no npm dependencies and its Node "
            "predates TypeScript type stripping. Install Node and re-run rather "
            "than skipping the check."
        )
    return exe


def _call(
    module: Path,
    calls: list[dict[str, object]],
    *,
    tz: str | None = None,
) -> list[object]:
    """Run the shipped module under Node and return the raw results."""
    assert module.exists(), (
        f"{module.name} is missing: the desktop app has no place to put this "
        "logic, so the wording it is supposed to drive cannot exist yet"
    )
    env = dict(os.environ)
    if tz is not None:
        env["TZ"] = tz
    proc = subprocess.run(
        [_node(), "--input-type=module", "-e", PROBE, module.as_uri()],
        input=json.dumps(calls),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        timeout=120,
        env=env,
    )
    assert proc.returncode == 0, f"the probe on {module.name} failed on Node:\n{proc.stderr}"
    return json.loads(proc.stdout)


# ---------------------------------------------------------------------------
# 1. The findings page names the backend it actually called
# ---------------------------------------------------------------------------


def test_backend_address_follows_the_effective_base_url() -> None:
    """The address shown in an error is the one the request went to.

    The sidecar's port is chosen by the system, so it is only knowable from
    the client's *effective* base URL.  When the base URL is relative (the
    dev server proxies ``/api``), the port lives behind the proxy and the
    frontend cannot know it — that case must say so instead of inventing one.
    """
    results = _call(
        ADDRESS_MODULE,
        [
            {"fn": "backendAddress", "args": ["http://127.0.0.1:64074/api"]},
            {"fn": "backendAddress", "args": ["http://127.0.0.1:8618/api"]},
            {"fn": "backendAddress", "args": ["/api"]},
            {"fn": "backendAddress", "args": [""]},
            {"fn": "backendAddress", "args": [None]},
            {"fn": "backendAddress", "args": ["not an address"]},
        ],
    )
    assert results == [
        "http://127.0.0.1:64074",
        "http://127.0.0.1:8618",
        None,
        None,
        None,
        None,
    ]


def test_findings_page_error_text_has_no_hardcoded_port() -> None:
    """The findings page must not name a port it did not call."""
    source = FINDINGS_PAGE.read_text(encoding="utf-8")
    assert "8618" not in source, (
        "FindingsPage still names a fixed backend port: the desktop app talks to "
        "the sidecar's dynamic port, so a hard-coded 8618 points the reader at "
        "somebody else's backend"
    )
    assert "backendAddress" in source, (
        "FindingsPage must derive the address from the client's effective base "
        "URL instead of writing one down"
    )
    assert "effectiveBaseUrl" in source, (
        "FindingsPage must read the client's effective base URL — the sidecar "
        "port is only known there"
    )
    assert "后端地址未知" in source, (
        "FindingsPage must say the address is unknown when the base URL hides "
        "the port, rather than making one up"
    )


# ---------------------------------------------------------------------------
# 2. The analysis page's footnote agrees with the workbench
# ---------------------------------------------------------------------------


def test_the_workbench_does_serve_the_backends_endpoint() -> None:
    """The ground truth the footnote has to agree with."""
    app = WORKBENCH_APP.read_text(encoding="utf-8")
    assert '@app.get("/api/backends")' in app, (
        "the workbench no longer serves /api/backends — if this endpoint is "
        "gone, the footnote below has to say so instead"
    )


def test_analysis_page_footnote_agrees_with_the_workbench() -> None:
    """No "there is no /api/backends" — the endpoint answers 200."""
    source = ANALYSIS_PAGE.read_text(encoding="utf-8")
    for stale in ("无 /api/backends", "没有 /api/backends", "workbench 无 /api/backends"):
        assert stale not in source, (
            f"Analysis.tsx still claims {stale!r}: the workbench serves that "
            "endpoint (PR #18) and the acceptance run measured a 200"
        )
    assert "/api/backends" in source, (
        "Analysis.tsx should name the endpoint it is describing, so a reader can check it"
    )
    assert "tool_versions" in source, (
        "the footnote must still say where the *participation* comes from — "
        "/api/backends says which backends are installed, not which ones this "
        "analysis used"
    )


def test_the_api_layer_no_longer_claims_the_endpoint_is_missing() -> None:
    """client.ts, types.ts and SettingsPage.tsx carried the same stale sentence."""
    stale_markers = {
        CLIENT: ("仍没有 /api/backends",),
        TYPES: ("workbench 未提供该端点",),
        SETTINGS_PAGE: ("的 workbench 未提供该端点",),
    }
    for path, markers in stale_markers.items():
        source = path.read_text(encoding="utf-8")
        for marker in markers:
            assert marker not in source, (
                f"{path.name} still claims the endpoint is missing ({marker!r})"
            )
        assert "/api/backends" in source, f"{path.name} should name the endpoint it calls"


# ---------------------------------------------------------------------------
# 3. The reports page shows the timestamp in local time
# ---------------------------------------------------------------------------


def test_reports_page_renders_the_timestamp_through_the_helper() -> None:
    """No more slicing the UTC string to 19 characters."""
    source = REPORTS_PAGE.read_text(encoding="utf-8")
    assert "slice(0, 19)" not in source, (
        "ReportsPage still slices the raw UTC timestamp — that is the string "
        "the acceptance run read as a local time eight hours off"
    )
    assert "timestampParts" in source, "ReportsPage must render the timestamp through the helper"


def test_timestamp_is_shown_in_local_time_with_a_utc_label() -> None:
    """The same instant, two honest readings of it."""
    calls = [{"fn": "timestampParts", "args": [UTC_ISO]}]
    shanghai = _call(DATETIME_MODULE, calls, tz="Asia/Shanghai")[0]
    utc = _call(DATETIME_MODULE, calls, tz="UTC")[0]
    assert shanghai == {
        "local": "2026-11-26 02:46:07",
        "utc": "2026-11-25 18:46:07",
        "offset": "UTC+08:00",
    }
    assert utc == {
        "local": "2026-11-25 18:46:07",
        "utc": "2026-11-25 18:46:07",
        "offset": "UTC+00:00",
    }


def test_a_timestamp_without_a_zone_is_read_as_utc() -> None:
    """The backend always writes UTC; a zone-less string must not drift.

    ``new Date("2026-11-25T18:46:07")`` is *local* time per the ECMAScript
    spec, so a zone-less string read that way would shift by the machine's
    offset — the very bug this fix removes, one level down.
    """
    calls = [{"fn": "timestampParts", "args": ["2026-11-25T18:46:07"]}]
    shanghai = _call(DATETIME_MODULE, calls, tz="Asia/Shanghai")[0]
    assert shanghai == {
        "local": "2026-11-26 02:46:07",
        "utc": "2026-11-25 18:46:07",
        "offset": "UTC+08:00",
    }


def test_an_unreadable_timestamp_is_reported_as_unknown() -> None:
    """No timestamp, no invented one."""
    results = _call(
        DATETIME_MODULE,
        [
            {"fn": "timestampParts", "args": [""]},
            {"fn": "timestampParts", "args": ["not a timestamp"]},
            {"fn": "timestampParts", "args": [None]},
        ],
    )
    assert results == [None, None, None]
