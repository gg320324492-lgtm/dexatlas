"""Regression tests for the desktop sidecar endpoint resolution.

The packaged-exe acceptance (2026-11-25) found two real defects on the way
from the shell to the backend:

* the Rust side never spawned the sidecar in an installed layout — the
  repository-root lookup was chained into the spawn with ``and_then``, so an
  inferred-nothing cwd meant ``Command::new`` was never called (covered by
  ``cargo test`` in ``desktop/src-tauri``); and
* the frontend resolved the base URL **once**, when the module was loaded.
  The sidecar's port is only known *after* it has started, so the client
  locked itself onto the 8618 fallback and every later request went to
  somebody else's backend.

The desktop app has no test runner in this repository, so — like the other
desktop regressions (``test_desktop_version_badge.py``) — these are
source-level assertions.  They pin the two properties the packaged exe
depends on: the client re-resolves the base URL when the sidecar port
appears or changes, and it never locks the fallback permanently.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "desktop" / "src" / "api" / "client.ts"
ENDPOINT = ROOT / "desktop" / "src" / "api" / "sidecarEndpoint.ts"


def _endpoint_source() -> str:
    assert ENDPOINT.exists(), (
        "desktop/src/api/sidecarEndpoint.ts is missing: the sidecar port "
        "resolution must live in a module the client can re-run, not in a "
        "one-shot call at construction time"
    )
    return ENDPOINT.read_text(encoding="utf-8")


def test_the_client_subscribes_to_the_sidecar_status_event() -> None:
    """The port can change (the sidecar restarts); the client must listen."""

    endpoint = _endpoint_source()
    assert '"sidecar:status"' in endpoint, (
        "the endpoint module must listen to the sidecar:status event, which is "
        "how the shell announces the port it actually got"
    )
    assert "listen" in endpoint, "the event subscription must use tauri's listen()"

    client = CLIENT.read_text(encoding="utf-8")
    assert "subscribeSidecarStatus" in client, (
        "the client must subscribe to sidecar:status; a port resolved once at "
        "construction time is what locked it onto the 8618 fallback"
    )


def test_the_client_rewrites_the_base_url_when_the_port_changes() -> None:
    """A new port has to reach ``this.baseUrl``."""

    client = CLIENT.read_text(encoding="utf-8")
    assert re.search(r"this\.baseUrl\s*=\s*[^;]*port", client), (
        "the base URL must be rewritten from the sidecar port, not only at construction time"
    )
    assert client.count("applySidecarPort") >= 2, (
        "the port-application helper must be reachable from the event "
        "subscription, not just from the initial resolution"
    )


def test_the_client_does_not_lock_the_fallback_at_construction() -> None:
    """The one-shot resolver is exactly what broke the packaged exe."""

    client = CLIENT.read_text(encoding="utf-8")
    assert "resolveSidecarBaseUrl" not in client, (
        "the one-shot resolveSidecarBaseUrl() must be gone: it resolved the "
        "port before the sidecar had one and froze the 8618 fallback into the "
        "base URL for the rest of the session"
    )
    assert "waitForSidecarPort" in client, (
        "the client must wait (with a bound) for the sidecar port before its "
        "first request instead of falling back right away"
    )


def test_the_wait_for_the_sidecar_port_is_bounded() -> None:
    """An unbounded wait would hang the UI when no backend can start."""

    endpoint = _endpoint_source()
    assert re.search(r"SIDECAR_PORT_WAIT_MS\s*=\s*\d+", endpoint), (
        "the wait for the sidecar port must have an explicit, finite bound"
    )
    assert re.search(r"deadline", endpoint), (
        "the polling loop must compare against a deadline so the wait ends"
    )
    assert re.search(r"failed", endpoint), (
        "the wait must give up early when the shell says the backend failed to "
        "start, instead of waiting for a port that will never arrive"
    )


def test_the_sidecar_status_shape_has_a_single_definition() -> None:
    """The payload shape must be declared once, not copied around.

    ``sidecar.ts`` holds the shape of ``get_sidecar_status`` /
    ``sidecar:status``.  The port-resolution module used to declare a second,
    near-identical copy that had already drifted (it was the only one carrying
    the ``failed`` flag), so a change to the Rust payload could land in one
    place and not the other.
    """

    sidecar = (ROOT / "desktop" / "src" / "api" / "sidecar.ts").read_text(encoding="utf-8")
    endpoint = _endpoint_source()

    assert re.search(r"interface SidecarStatus\b", sidecar), (
        "sidecar.ts must keep declaring the sidecar status shape"
    )
    assert re.search(r"failed", sidecar), (
        "the SidecarStatus shape must carry the failed flag the Rust side sends"
    )
    assert not re.search(r"interface SidecarStatusPayload\b", endpoint), (
        "sidecarEndpoint.ts must not declare a second copy of the sidecar "
        "status shape; reuse SidecarStatus from sidecar.ts"
    )
    assert re.search(r'from\s+"\./sidecar"', endpoint), (
        "sidecarEndpoint.ts must reuse the type from sidecar.ts"
    )
