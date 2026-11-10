"""Fetch a large release asset with parallel range requests.

The GitHub release CDN serves one connection at roughly 40 KB/s from some
networks; a single file takes half an hour. The CDN honours Range requests,
so the file is fetched as independent byte ranges and concatenated.

    uv run --no-sync python scripts/fetch-jadx.py
    uv run --no-sync python scripts/fetch-jadx.py --version 1.5.2 --dest .scratch/backends

The result is the same tree ``scripts/install-backends.sh`` produces, so the
two can be pointed at the same directory: one is for a CI runner with a fast
link, the other for a laptop on a slow one.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import shutil
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_VERSION = "1.5.2"
DEFAULT_DEST = ".scratch/backends"
WORKERS = 16
CHUNK = 4 * 1024 * 1024
RETRIES = 3


def url_for(version: str) -> str:
    """Where the release asset lives."""
    return f"https://github.com/skylot/jadx/releases/download/v{version}/jadx-{version}.zip"


def size_of(url: str) -> int:
    """How many bytes the asset is."""
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request) as response:
        return int(response.headers["Content-Length"])


def fetch(url: str, start: int, end: int, path: Path) -> tuple[int, int]:
    """One byte range, written to its own file."""
    request = urllib.request.Request(url=url, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(request) as response:
        data = response.read()
    if len(data) != end - start + 1:
        raise RuntimeError(f"range {start}-{end} returned {len(data)} bytes")
    path.write_bytes(data)
    return start, len(data)


def fetch_range(url: str, start: int, end: int, path: Path) -> tuple[int, int]:
    """One byte range, with the retries a slow link needs."""
    last: Exception | None = None
    for _attempt in range(1, RETRIES + 1):
        try:
            return fetch(url, start, end, path)
        except Exception as error:
            last = error
            print(f"    range {start}-{end} failed ({error}); retrying", flush=True)
    raise RuntimeError(f"range {start}-{end} failed {RETRIES} times: {last}")


def download(url: str, target: Path) -> int:
    """The whole asset, in ranges, written to one file."""
    total = size_of(url)
    print(f"total {total} bytes", flush=True)
    parts = target.with_suffix(target.suffix + ".parts")
    if parts.exists():
        shutil.rmtree(parts)
    parts.mkdir(parents=True)

    bounds = []
    index = 0
    while index < total:
        end = min(index + CHUNK, total) - 1
        bounds.append((index, end, parts / f"{index:012d}"))
        index = end + 1

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch_range, url, start, end, path) for start, end, path in bounds]
        for future in concurrent.futures.as_completed(futures):
            _start, size = future.result()
            done += size
            print(f"  {done / total * 100:5.1f}%  ({done}/{total})", flush=True)

    with target.open("wb") as out:
        for _, _, path in bounds:
            out.write(path.read_bytes())
    shutil.rmtree(parts)

    written = target.stat().st_size
    if written != total:
        print(f"FAILED: wrote {written} of {total}", flush=True)
        raise RuntimeError("the file that came back is not the file that was asked for")
    return written


def unpack(archive: Path, destination: Path) -> None:
    """The archive, unpacked where the backends live."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(destination)
    for binary in (destination / "bin").glob("*"):
        binary.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=DEFAULT_VERSION, help="the jadx release to fetch")
    parser.add_argument(
        "--dest",
        default=DEFAULT_DEST,
        help="where to unpack it; the jadx tree lands in <dest>/jadx",
    )
    parser.add_argument(
        "--keep-archive",
        action="store_true",
        help="keep the downloaded zip instead of deleting it",
    )
    arguments = parser.parse_args()

    destination = Path(arguments.dest).resolve()
    url = url_for(arguments.version)
    archive = destination / f"jadx-{arguments.version}.zip"

    print(f"fetching {url}")
    written = download(url, archive)
    print(f"ok: {archive} {written} bytes")

    unpack(archive, destination / "jadx")
    if not arguments.keep_archive:
        archive.unlink()

    launcher = destination / "jadx" / "bin" / "jadx.bat"
    if not launcher.is_file():
        launcher = destination / "jadx" / "bin" / "jadx"
    print(f"unpacked into {destination / 'jadx'}")
    print(f'point DexAtlas at it with: export DEXATLAS_JADX_PATH="{launcher}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
