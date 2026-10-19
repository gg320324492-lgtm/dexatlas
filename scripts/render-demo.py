#!/usr/bin/env python3
"""Render a captured terminal session into a GIF.

    scripts/render-demo.py

Draws each frame with Pillow, then encodes with ffmpeg.

Why not ffmpeg's drawtext: it renders the *whole* text file for every filter, so drawing
N lines needs N overlays of the entire file at different offsets. The result is every
line repeated at every position — unusable. Pillow draws exactly the lines each frame
should show, which also makes the reveal animation and per-line colouring trivial.

Why not VHS: it renders through ttyd, which silently produces no file on Windows.

Colours follow the GitHub dark palette so the asset sits naturally in the README.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent

WIDTH = 1400
FPS = 12

#: Frames each line takes to appear. One would be a hard cut; three reads as typing
#: without making a 100-line session take a minute to watch.
FRAMES_PER_LINE = 3

#: The README teaser shows the opening only. Research on comparable projects found GIFs
#: placed below the fourth screen are never reached, so the README gets a short one and
#: the full session lives with the releases.
QUICK_LINES = 34

FONT_SIZE = 15
LINE_HEIGHT = 21
TEXT_LEFT = 22
TEXT_TOP = 54
CHROME_HEIGHT = 34

BACKGROUND = (0x0D, 0x11, 0x17)
CHROME = (0x16, 0x1B, 0x22)
TEXT = (0xC9, 0xD1, 0xD9)
MUTED = (0x8B, 0x94, 0x9E)
RULE = (0x30, 0x36, 0x3D)
COMMAND = (0x79, 0xC0, 0xFF)
SUCCESS = (0x3F, 0xB9, 0x50)
TITLE = MUTED
DOTS = ((0xFF, 0x5F, 0x56), (0xFF, 0xBD, 0x2E), (0x27, 0xC9, 0x3F))

FONT_CANDIDATES = (
    # Cascadia first: it is the only common Windows monospace with U+2713 ✓, which the
    # CLI prints on success. Consola, Courier New and Lucida Console all lack it and
    # render it as an empty box, which looks like a bug in the recording.
    "C:/Windows/Fonts/CascadiaMono.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
)


def load_font() -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, FONT_SIZE)
    raise SystemExit("no monospace font found; install DejaVu Sans Mono")


def bash_executable() -> str:
    """The MSYS bash that understands POSIX paths.

    ``bash`` on PATH may be a Windows shim that only accepts native paths, which is why
    passing a POSIX path to it fails.
    """
    candidates = [
        shutil.which("bash") or "",
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit("bash not found; it is required to run scripts/capture-demo.sh")


def _posix(path: Path) -> str:
    """A path the MSYS bash can open (``G:\\x`` becomes ``/g/x``)."""
    resolved = path.resolve()
    if sys.platform != "win32":
        return str(resolved)
    return f"/{resolved.drive.rstrip(':').lower()}/{resolved.as_posix()[2:].lstrip('/')}"


def capture_session() -> list[str]:
    """Run the live capture and return its lines."""
    result = subprocess.run(
        [bash_executable(), _posix(REPO_ROOT / "scripts" / "capture-demo.sh")],
        capture_output=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    # The capture is UTF-8: box-drawing characters and the check mark. Decoding with the
    # console code page would raise or silently mangle the glyphs that make it readable.
    stdout = result.stdout.decode("utf-8", errors="replace")
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
        raise SystemExit("capture-demo.sh failed")

    lines = stdout.splitlines()
    if len(lines) < 40:
        sys.stderr.write(stdout)
        raise SystemExit(f"capture produced only {len(lines)} lines — the CLI probably failed")
    print(f"Captured {len(lines)} lines from a live session.")
    return lines


def colour_for(line: str) -> tuple[int, int, int]:
    """Comments recede, commands stand out, output is the body, results are green."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return MUTED
    if stripped.startswith("$ "):
        return COMMAND
    if stripped.startswith("---"):
        return RULE
    # The CLI marks a completed analysis with a check; tint it so the eye lands on the
    # result rather than scrolling past it.
    if stripped.startswith(("✓", "OK ")):
        return SUCCESS
    return TEXT


def render_frames(lines: list[str], directory: Path, font: ImageFont.FreeTypeFont) -> list[Path]:
    """One PNG per frame, with the session revealing line by line."""
    height = TEXT_TOP + (len(lines) + 1) * LINE_HEIGHT
    # libx264 with yuv420p requires even dimensions; an odd height fails the encode.
    height += height % 2
    frames: list[Path] = []

    for index in range(len(lines) + 1):
        visible = min(index + 1, len(lines))
        image = Image.new("RGB", (WIDTH, height), BACKGROUND)
        draw = ImageDraw.Draw(image)

        # Window chrome, so the asset reads as a terminal rather than a text dump.
        draw.rectangle([0, 0, WIDTH, CHROME_HEIGHT], fill=CHROME)
        for dot, x in zip(DOTS, (14, 32, 50), strict=True):
            draw.rectangle([x, 11, x + 11, 22], fill=dot)
        # Right-align the title using its measured width: the font differs by platform,
        # so a fixed offset would leave it off-centre on half the systems.
        title = "dexatlas  from APK to evidence"
        title_width = draw.textlength(title, font=font)
        draw.text((WIDTH - 20 - title_width, 9), title, font=font, fill=TITLE)

        for row, line in enumerate(lines[:visible]):
            draw.text(
                (TEXT_LEFT, TEXT_TOP + row * LINE_HEIGHT),
                line,
                font=font,
                fill=colour_for(line),
            )

        frame = directory / f"frame-{index:05d}.png"
        image.save(frame)
        frames.append(frame)

    return frames


def encode(frames: list[Path], out: Path, workdir: Path) -> Path:
    """Frames to GIF, through a high-quality H.264 intermediate.

    ffmpeg cannot take a directory of numbered PNGs as one input without a pattern that
    matches the sequence exactly, so the frame list is written to a concat demuxer file
    and streamed by path. That has no ambiguity about ordering or start numbers.

    Returns the intermediate, which is the same video the GIF was made from — a
    published video is then the identical recording, not a second take.
    """
    intermediate = workdir / f"{out.stem}.mp4"
    listing = workdir / "frames.txt"
    listing.write_text(
        "\n".join(f"file '{frame.as_posix()}'" for frame in frames) + "\n", encoding="utf-8"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-r",
            str(FPS),
            "-i",
            str(listing),
            "-c:v",
            "libx264",
            # yuv420p is what browsers and GitHub will actually play, and it
            # requires even dimensions.
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "20",
            "-preset",
            "slow",
            str(intermediate),
        ],
        check=True,
        capture_output=True,
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    # palettegen/paletteuse keeps colours accurate; a naive GIF conversion muddies them.
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(intermediate),
            "-vf",
            f"fps={FPS},scale={WIDTH}:-1:flags=lanczos,split[a][b];"
            "[a]palettegen=max_colors=128:stats_mode=diff[p];"
            "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
            "-loop",
            "0",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return intermediate


def render(
    lines: list[str],
    out: Path,
    font: ImageFont.FreeTypeFont,
    video: Path | None = None,
) -> None:
    """Render the session to an asset, and optionally to a video of the same frames."""
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        work = Path(tmp)
        frames = render_frames(lines, work, font)
        print(f"  {len(frames)} frames")
        intermediate = encode(frames, out, work)
        if video is not None:
            video.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(intermediate, video)
        for frame in frames:
            frame.unlink(missing_ok=True)


def main() -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required: https://www.gyan.dev/ffmpeg/builds/")

    font = load_font()
    captured = capture_session()
    asset_dir = REPO_ROOT / "docs" / "assets"

    print(f"Rendering demo-quick.gif (first {QUICK_LINES} lines)...")
    render(captured[:QUICK_LINES], asset_dir / "demo-quick.gif", font)

    # The video is the same recording as the full GIF, encoded from the same frames,
    # so the two cannot drift apart.
    print("Rendering demo.gif and demo.mp4 (full session)...")
    render(captured, asset_dir / "demo.gif", font, video=asset_dir / "demo.mp4")

    for asset in sorted(asset_dir.glob("*.gif")) + sorted(asset_dir.glob("*.mp4")):
        size_kb = asset.stat().st_size / 1024
        print(f"  {asset.relative_to(REPO_ROOT)}  {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
