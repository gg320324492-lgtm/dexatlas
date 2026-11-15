"""A minimal Python client for the DexAtlas REST API.

It wraps the calls an integration actually makes — upload and analyse, wait
for the project, search the index, export the report — with no dependency
beyond ``httpx`` (already in the ``dev`` extra):

    uv run --no-sync python examples/api_client.py examples/demo-app/demo.apk

It needs a running API:

    uv run --no-sync uvicorn dexatlas.api.app:app --port 8000

The point of this file is to be copied into your own project, not imported as
a framework. Every method maps to one endpoint; there is no state, no retry
policy and no abstraction beyond the verbs.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
POLL_SECONDS = 2.0
POLL_TIMEOUT_SECONDS = 600.0


class DexAtlasClient:
    """The endpoints of the upload → analyse → query → report flow."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def analyze(self, apk_path: str | Path) -> dict[str, Any]:
        """POST /analyze — upload an APK and start a background analysis.

        Returns the job body: ``project_id``, ``status`` and ``detail``.
        Uploading the same bytes twice returns the existing project rather
        than a new job, so this is idempotent by content hash.
        """
        path = Path(apk_path)
        with path.open("rb") as handle:
            response = httpx.post(
                f"{self.base_url}/analyze",
                files={"file": (path.name, handle)},
                timeout=self.timeout,
            )
        response.raise_for_status()
        return response.json()

    def wait_for_project(
        self,
        project_id: str,
        *,
        poll_seconds: float = POLL_SECONDS,
        timeout_seconds: float = POLL_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """GET /projects/{id} until the analysis leaves ``pending``.

        Returns the project body with its counts and tool versions. Raises
        ``TimeoutError`` if the analysis is still not finished after
        ``timeout_seconds``.
        """
        deadline = time.monotonic() + timeout_seconds
        while True:
            project = self.get_project(project_id)
            if project["status"] != "pending":
                return project
            if time.monotonic() > deadline:
                msg = f"analysis of {project_id} did not finish in {timeout_seconds}s"
                raise TimeoutError(msg)
            time.sleep(poll_seconds)

    def get_project(self, project_id: str) -> dict[str, Any]:
        """GET /projects/{id} — one project's status and counts."""
        response = httpx.get(f"{self.base_url}/projects/{project_id}", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def search(self, project_id: str, query: str) -> dict[str, Any]:
        """GET /projects/{id}/search?q=… — the symbol index."""
        response = httpx.get(
            f"{self.base_url}/projects/{project_id}/search",
            params={"q": query},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def manifest(self, project_id: str) -> dict[str, Any]:
        """GET /projects/{id}/manifest — the parsed AndroidManifest.xml."""
        response = httpx.get(
            f"{self.base_url}/projects/{project_id}/manifest", timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def evidence(self, project_id: str) -> dict[str, Any]:
        """GET /projects/{id}/evidence — every evidence record, with provenance."""
        response = httpx.get(
            f"{self.base_url}/projects/{project_id}/evidence", timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def report(self, project_id: str, *, fmt: str = "json") -> Any:
        """GET /projects/{id}/report?format=… — the exported report.

        ``fmt="json"`` returns the parsed JSON report; ``fmt="markdown"``
        returns the Markdown text. The two carry the same records.
        """
        response = httpx.get(
            f"{self.base_url}/projects/{project_id}/report",
            params={"format": fmt},
            timeout=self.timeout,
        )
        response.raise_for_status()
        if fmt == "json":
            return response.json()
        return response.text


def main() -> int:
    """Upload the APK given on the command line and walk its result."""
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    client = DexAtlasClient()
    job = client.analyze(sys.argv[1])
    print(f"analyze: {job['status']:>9}  {job['project_id']}")

    project = client.wait_for_project(job["project_id"])
    print(
        f"project: {project['status']}  {project['class_count']} classes, "
        f"{project['method_count']} methods, {project['call_edge_count']} call edges, "
        f"{project['evidence_count']} evidence records"
    )

    hits = client.search(project["id"], "sk_live")
    for hit in hits["results"]:
        print(f"search:  {hit['kind']:>7}  {hit['name']}")

    report = client.report(project["id"], fmt="json")
    print(
        f"report:  schema {report['schema_version']}, "
        f"run {report['run']['id']} ({report['run']['completeness']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
