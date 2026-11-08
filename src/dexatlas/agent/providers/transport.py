"""How the providers reach an endpoint.

The transport is a seam: a provider hands it a URL, a JSON payload, the
headers and a timeout, and it answers with the decoded JSON document. The
default implementation talks HTTP over the standard library, so the package
grows no dependency for the sake of a model call; a test can hand a provider a
different one and assert on the request without a socket.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from dexatlas.agent.providers.base import ProviderError

#: The shape of a transport: a URL, a payload, the headers and a timeout in,
#: and the decoded JSON document out.
Transport = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]

#: How much of an error body is kept for the message.
MAX_ERROR_BODY = 2000


def urllib_transport(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    """POST a JSON payload and hand back the decoded answer.

    Every failure becomes a :class:`ProviderError`, because a provider that
    raises something else takes the orchestration down with it, and a model
    endpoint that is down is an ordinary thing to survive.
    """
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:MAX_ERROR_BODY]
        raise ProviderError(
            f"the model endpoint answered {exc.code}: {detail}",
            # A server that is busy or broken may answer differently next time;
            # a request the endpoint refused will be refused again.
            retryable=exc.code == 429 or exc.code >= 500,
        ) from exc
    except TimeoutError as exc:
        raise ProviderError("the model endpoint did not answer in time", retryable=True) from exc
    except urllib.error.URLError as exc:
        raise ProviderError(
            f"the model endpoint could not be reached: {exc.reason}", retryable=True
        ) from exc

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            f"the model endpoint answered with something that is not JSON: {raw[:200]!r}",
            retryable=False,
        ) from exc
    if not isinstance(decoded, dict):
        raise ProviderError(
            "the model endpoint answered with a JSON document that is not an object",
            retryable=False,
        )
    return decoded


__all__ = ["MAX_ERROR_BODY", "Transport", "urllib_transport"]
