"""One command that starts the workbench.

``python -m dexatlas.workbench`` builds the front end if it has not been
built (it needs npm once, on the first start) and then serves both the API
and the built files with uvicorn. The workspace is the one the rest of
DexAtlas reads: ``DEXATLAS_WORKSPACE``, or ``.dexatlas`` beside the
repository.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from dexatlas.core.pipeline import Analyzer
from dexatlas.workbench.app import WEB_DIST, create_app

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8618

_BUILD_HINT = (
    "the workbench front end is not built yet; from the repository root run "
    "`npm install --prefix src/dexatlas/workbench/web` and then "
    "`npm run build --prefix src/dexatlas/workbench/web`"
)


def _repo_root() -> Path | None:
    """The checkout the workbench package is running from, if it is one."""
    for parent in [WEB_DIST.parent, *WEB_DIST.parent.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _npm_env() -> dict[str, str]:
    """npm's environment, with its cache and temp files off the system drive.

    The project keeps everything it writes inside its own scratch area, and
    npm's default cache is on the system drive. A checkout has that scratch
    area; an installed package does not, and keeps npm's default. ``TMP`` is
    what Windows tools read, ``TMPDIR`` what POSIX ones read.
    """
    env = dict(os.environ)
    root = _repo_root()
    if root is not None:
        cache = root / ".scratch" / "npm-cache"
        tmp = root / ".scratch" / "tmp"
        cache.mkdir(parents=True, exist_ok=True)
        tmp.mkdir(parents=True, exist_ok=True)
        env.setdefault("npm_config_cache", str(cache))
        for name in ("TMPDIR", "TEMP", "TMP"):
            env.setdefault(name, str(tmp))
    return env


def ensure_front_end_built() -> None:
    """Build the front end once, so the first start is still one command."""
    if (WEB_DIST / "index.html").is_file():
        return
    npm = shutil.which("npm")
    if npm is None:
        sys.exit("the workbench front end is not built and npm is not on PATH. " + _BUILD_HINT)
    web_root = WEB_DIST.parent
    print("building the workbench front end (first start only)...", flush=True)
    subprocess.run(
        [npm, "install", "--no-fund", "--no-audit"],
        cwd=web_root,
        env=_npm_env(),
        check=True,
    )
    subprocess.run(
        [npm, "run", "build"],
        cwd=web_root,
        env=_npm_env(),
        check=True,
    )
    if not (WEB_DIST / "index.html").is_file():
        sys.exit("the front end build finished but produced no web/dist/index.html")


def _port_is_free(host: str, port: int) -> bool:
    """Whether a TCP port can be bound right now.

    Asked before uvicorn is, so a port another workbench holds is refused
    with a remedy instead of a translated bind error from inside uvicorn's
    startup. The probe deliberately does not set the address reuse uvicorn
    binds with: on Windows, reuse makes a probe succeed on a port another
    live listener already holds, which would send the refusal one step too
    late and let uvicorn's own bind error come back.
    """
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def main(argv: list[str] | None = None) -> None:
    """Parse the arguments, build the front end once, serve with uvicorn."""
    parser = argparse.ArgumentParser(
        prog="python -m dexatlas.workbench",
        description="Start the DexAtlas web workbench.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="the interface to bind (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="the port to bind (default: %(default)s; 0 lets the system choose)",
    )
    args = parser.parse_args(argv)

    ensure_front_end_built()

    import uvicorn

    from dexatlas.config.settings import get_settings

    if args.port != 0 and not _port_is_free(args.host, args.port):
        # The error a newcomer meets otherwise is uvicorn's own bind
        # traceback, translated on a Windows console, naming no port and no
        # remedy. This one line is the whole fix: name the port, name the
        # flag, and offer the way out.
        print(
            f"error: port {args.port} on {args.host} is already in use; "
            f"pass --port <other> (for example --port {args.port + 1}) "
            "or --port 0 to let the system choose a free port",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    analyzer = Analyzer(get_settings())
    app = create_app(analyzer)
    if args.port == 0:
        # The port is the operating system's to choose, and uvicorn's own
        # startup line names the one that was bound; a banner printed here
        # would say :0, which is the argument, not the port.
        print(f"serving the workbench on http://{args.host}:<system-chosen port>", flush=True)
    else:
        print(f"serving the workbench on http://{args.host}:{args.port}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
