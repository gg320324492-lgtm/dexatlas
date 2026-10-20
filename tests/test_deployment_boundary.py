"""What the deployment publishes.

The REST API has no authentication: it lists every project, serves their
decompiled sources and accepts APKs to analyse. That is a reasonable trade for
a single-user tool on a laptop and an unreasonable one on a network, so the
default deployment has to keep it on this machine — and has to say so.

These tests check the published surface: the port mapping, the container's own
binding, and what the installation guide tells the reader.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
COMPOSE = REPO_ROOT / "docker-compose.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"
INSTALL = REPO_ROOT / "docs" / "install.md"


def test_the_compose_file_publishes_the_api_on_the_loopback_interface_only() -> None:
    """``8000:8000`` binds every interface of the host.

    The API answers to anyone who can reach it, so the mapping has to name
    the interface it is published on.
    """
    text = COMPOSE.read_text(encoding="utf-8")
    published = re.findall(r'"([^"\s]*:\d+:\d+)"', text)

    assert published, "the compose file publishes no port at all"
    for mapping in published:
        host = mapping.rsplit(":", 2)[0]
        assert host in {"127.0.0.1", "localhost"}, (
            f"the compose file publishes {mapping} on every interface"
        )


def test_the_container_still_binds_every_interface_of_its_own() -> None:
    """The server inside the container has to bind ``0.0.0.0``.

    A container that binds its own loopback interface cannot be reached
    through a published port: the mapping would find nothing to connect to.
    What is published, and to whom, is decided on the host.
    """
    text = DOCKERFILE.read_text(encoding="utf-8")

    assert '"--host", "0.0.0.0"' in text or "--host 0.0.0.0" in text, (
        "the container's own server must bind every interface of the container"
    )


def test_the_install_guide_publishes_on_the_loopback_interface_only() -> None:
    """The command the guide gives is the command most readers will run."""
    text = INSTALL.read_text(encoding="utf-8")
    commands = [line for line in text.splitlines() if "docker run" in line and " -p " in line]

    assert commands, "the installation guide shows no published port"
    for command in commands:
        assert "127.0.0.1:" in command or "localhost:" in command, (
            f"the installation guide publishes on every interface: {command.strip()}"
        )


def test_the_install_guide_says_the_api_has_no_authentication() -> None:
    """A reader has to be told, before they expose it, what they are exposing."""
    text = INSTALL.read_text(encoding="utf-8").lower()

    assert "no authentication" in text
    assert "reverse proxy" in text
    assert "loopback" in text or "127.0.0.1" in text
