#!/usr/bin/env python3
"""Generate a large synthetic APK, to press the analysis pipeline at a scale.

The samples under ``examples/`` are small on purpose: they are committed, so they
stay small. Everything they exercise — the manifest reader, the symbol index, the
cross-reference table — works fine on a three-kilobyte archive. What they cannot
exercise is the part of the pipeline that only misbehaves at scale: the three
limits in the Androguard adapter (``DEFAULT_METHOD_LIMIT``,
``DEFAULT_STRING_LIMIT``, ``DEFAULT_INSTRUCTION_LIMIT``), the cost of building the
index, and the agreement between a report's counts and the rows a query returns.

This script builds a throw-away APK of a size nobody would commit, so that part
of the pipeline can be measured rather than guessed at.

The APK is assembled from smali this script writes, so it is first-party code and
it carries no third-party material. Nothing it produces is committed: the output
goes to a directory the caller names, and the script never writes inside the
repository unless the caller asks for it.

Usage::

    uv run python scripts/generate-large-apk.py --scale medium --output-dir /tmp/big
    uv run python scripts/generate-large-apk.py --scale large --output-dir /tmp/big

The scale is also readable from the environment, so a CI job can pick one without
rewriting the command line::

    DEXATLAS_LARGE_APK_SCALE=large uv run python scripts/generate-large-apk.py

Every run also writes a **ground-truth manifest** next to the APK: a JSON file
naming every class it generated and how many call sites it wrote. That file is
what lets a test assert the index against what the APK actually contains, instead
of against a number somebody typed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

#: The package every generated class lives in. It is deliberately not
#: ``com.example.demo`` — the committed samples use that one, and a stress sample
#: that shares their package would be indistinguishable from them in a log.
PACKAGE = "com.example.large"

#: The class every generated method calls into. A call target that is a real
#: method in the same APK is what makes the cross-reference index meaningful: an
#: edge into a class the APK does not define would still parse, but it could not
#: be resolved against the symbol table.
HELPER_CLASS = f"{PACKAGE}.Helper"
HELPER_METHOD = "combine"

#: The same class in smali's own spelling. Smali names a type with the Dalvik
#: descriptor form — a leading ``L``, slashes instead of dots, a trailing
#: semicolon — and a dotted name there is a parse error, not a warning.
HELPER_TYPE = f"L{PACKAGE.replace('.', '/')}/Helper;"

#: The most methods one DEX file may hold. The format's method-id table is
#: addressed with a 16-bit index, so the hard ceiling is 65,536 entries — and
#: some of them are spent on the classes and methods this APK calls rather than
#: defines. The ceiling used here leaves room for those.
MAX_METHODS_PER_DEX = 60_000

#: The most strings one DEX file may hold, for the same reason: the string-id
#: table is addressed with a 16-bit index too.
MAX_STRINGS_PER_DEX = 60_000


@dataclass(frozen=True)
class Scale:
    """How big a generated APK is.

    The four knobs are separate because they stress different things:

    ``classes``
        how many classes the APK holds. A class costs a type descriptor and a
        name in the string pool, so this is the knob that moves the *string* count.
    ``methods_per_class``
        how many methods each class holds. This is the knob that moves the
        *method* count, and the one that decides whether the method limit in the
        Androguard adapter is reached.
    ``instructions_per_method``
        how many instructions each method's body holds. This is the knob that
        moves the *instruction* count, and it is what decides whether the
        instruction limit is reached — the limit counts instructions walked, not
        methods seen.
    ``string_pool``
        how many distinct literal strings the APK's methods load. Each one is a
        row in the string index, and each one is a distinct entry in a DEX
        file's string pool, so this knob moves both.
    """

    classes: int
    methods_per_class: int
    instructions_per_method: int
    string_pool: int

    @property
    def total_methods(self) -> int:
        return self.classes * self.methods_per_class

    @property
    def filler_per_method(self) -> int:
        """The non-call instructions in each method body.

        A work method is five structural instructions — load the class marker,
        load a pooled literal, make the call, move the result, return — plus
        filler. The filler exists so that a tier can reach a large *instruction*
        count without also producing one cross-reference per instruction: a
        hundred thousand cross-references is a database, and a hundred million is
        a crash.
        """
        return max(0, self.instructions_per_method - 5)


#: The tiers. ``smoke`` is the default because it is the one a CI job can afford
#: on every run; the rest are opt-in, because each of them costs minutes.
#:
#: ``medium``
#:     Comfortably inside every default limit. This is the tier that shows what
#:     the pipeline does when nothing is clipped.
#: ``large``
#:     More methods than ``DEFAULT_METHOD_LIMIT`` (200,000), so the method limit
#:     is reached by a real APK rather than by a lowered threshold.
#: ``xlarge``
#:     More instructions in a single DEX file than ``DEFAULT_INSTRUCTION_LIMIT``
#:     (5,000,000), so the instruction limit is reached the same way.
SCALES: dict[str, Scale] = {
    "smoke": Scale(classes=20, methods_per_class=8, instructions_per_method=6, string_pool=64),
    "medium": Scale(
        classes=300, methods_per_class=40, instructions_per_method=12, string_pool=2_048
    ),
    "large": Scale(
        classes=2_050, methods_per_class=100, instructions_per_method=12, string_pool=4_096
    ),
    "xlarge": Scale(
        classes=600, methods_per_class=100, instructions_per_method=88, string_pool=4_096
    ),
}

DEFAULT_SCALE = "smoke"

#: The environment variable that selects the tier.
SCALE_ENV_VAR = "DEXATLAS_LARGE_APK_SCALE"


def class_name(index: int) -> str:
    """The dotted name of the ``index``-th generated class."""
    return f"{PACKAGE}.C{index:05d}"


def smali_path_name(index: int) -> str:
    """The file name of the ``index``-th generated class inside a smali tree."""
    return f"C{index:05d}.smali"


def marker_string(index: int) -> str:
    """The one literal string unique to each class.

    It is the handle a test searches for: a string that belongs to exactly one
    class, so a search that finds it has found that class and not merely
    something that shares a word with it.
    """
    return f"marker-{PACKAGE}-C{index:05d}"


def pool_string(pool_index: int) -> str:
    """One of the APK's shared literal strings.

    The pool is what lets a tier change the number of *distinct* strings
    without changing the number of methods that load them.
    """
    return f"literal-{PACKAGE}-{pool_index:06d}"


def pool_index_for(class_index: int, method_index: int, pool: int) -> int:
    """Which pooled literal a given method loads.

    The stride is a prime, so consecutive classes do not march through the pool
    in lockstep and the whole pool is used once there are enough method bodies
    to cover it.
    """
    return (class_index * 7 + method_index) % pool


def _method_body(index: int, method_index: int, scale: Scale) -> list[str]:
    """The body of one work method, as smali lines.

    The body loads the class's marker and one pooled literal, does some filler
    arithmetic, calls the shared helper once, and returns. The call is what
    produces one cross-reference, and the filler is what produces instructions.
    """
    literal = pool_string(pool_index_for(index, method_index, scale.string_pool))
    lines = [
        "    .locals 2",
        f'    const-string v0, "{marker_string(index)}"',
        f'    const-string v0, "{literal}"',
    ]
    for _ in range(scale.filler_per_method):
        lines.append("    add-int/lit8 v1, v1, 0x1")
    lines.append(
        f"    invoke-static {{v0, p0}}, {HELPER_TYPE}->{HELPER_METHOD}"
        "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
    )
    lines.append("    move-result-object v0")
    lines.append("    return-object v0")
    return lines


def render_class(index: int, scale: Scale) -> str:
    """The smali source of one generated class."""
    name = class_name(index)
    parts = [
        f".class public final L{name.replace('.', '/')};",
        ".super Ljava/lang/Object;",
        f'.source "{name.split(".")[-1]}.java"',
        "",
        ".field private static final MARKER:Ljava/lang/String;",
        "",
        ".method public constructor <init>()V",
        "    .locals 0",
        "    invoke-direct {p0}, Ljava/lang/Object;-><init>()V",
        "    return-void",
        ".end method",
        "",
    ]
    for method_index in range(scale.methods_per_class - 1):
        parts.append(f".method public static m{method_index}(Ljava/lang/String;)Ljava/lang/String;")
        parts.extend(_method_body(index, method_index, scale))
        parts.append(".end method")
        parts.append("")
    return "\n".join(parts)


def render_helper() -> str:
    """The smali source of the class every generated method calls."""
    return "\n".join(
        [
            f".class public final L{HELPER_CLASS.replace('.', '/')};",
            ".super Ljava/lang/Object;",
            f'.source "{HELPER_CLASS.split(".")[-1]}.java"',
            "",
            f".method public static {HELPER_METHOD}"
            "(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
            "    .locals 0",
            "    return-object p0",
            ".end method",
            "",
        ]
    )


def render_manifest(package: str) -> str:
    """A minimal but real AndroidManifest.xml.

    It is not installable and is not meant to be: it exists so Apktool has
    something to build, and so the manifest reader has a package to read.
    """
    return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package}" android:versionCode="1" android:versionName="1.0">
    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />
    <application android:label="DexAtlas Large Sample">
        <activity android:name="{package}.C00000" android:exported="true" />
    </application>
</manifest>
"""


def render_apktool_yml(apk_name: str) -> str:
    """The Apktool build file.

    It is the same shape the committed samples use, so a build of a generated
    sample and a build of a committed sample go through the same Apktool path.
    """
    return f"""version: 3.0.3
apkFileName: {apk_name}
isFrameworkApk: false
usesFramework:
  ids:
  - 1
sdkInfo:
  minSdkVersion: 24
  targetSdkVersion: 34
packageInfo:
  renameManifestPackage: null
sharedLibrary: false
sparseResources: false
unknownFiles:
  dirs: []
  files: []
doNotCompress:
- resources.arsc
versionInfo:
  versionCode: 1
  versionName: 1.0
"""


def plan_dex_files(scale: Scale, max_methods_per_dex: int = MAX_METHODS_PER_DEX) -> list[list[int]]:
    """Split the classes into DEX files, and report the split.

    A DEX file cannot hold more than 65,535 method ids, so a large APK has to be
    more than one DEX file. This is not a detail: it is the reason the adapter's
    limits behave differently for methods than for instructions and strings, and
    a test that never produced a multi-dex APK would not see it.

    ``max_methods_per_dex`` is lowerable on purpose. A DEX file is allowed to
    hold far fewer methods than the format permits, and a small APK split into
    several small DEX files costs a fraction of a second to build — which is how
    a test can exercise multi-dex behaviour without building a multi-megabyte
    one.
    """
    per_dex = max(1, max_methods_per_dex // scale.methods_per_class)
    files: list[list[int]] = []
    current: list[int] = []
    for index in range(scale.classes):
        current.append(index)
        if len(current) == per_dex:
            files.append(current)
            current = []
    if current:
        files.append(current)
    return files


def write_sources(
    project_dir: Path, scale: Scale, max_methods_per_dex: int = MAX_METHODS_PER_DEX
) -> list[list[int]]:
    """Write the smali tree, and return the class-to-DEX-file plan."""
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "AndroidManifest.xml").write_text(render_manifest(PACKAGE), encoding="utf-8")
    (project_dir / "apktool.yml").write_text(render_apktool_yml("large.apk"), encoding="utf-8")

    plan = plan_dex_files(scale, max_methods_per_dex)
    for dex_index, class_indexes in enumerate(plan):
        directory = "smali" if dex_index == 0 else f"smali_classes{dex_index + 1}"
        package_dir = project_dir / directory / PACKAGE.replace(".", "/")
        package_dir.mkdir(parents=True, exist_ok=True)
        for class_index in class_indexes:
            (package_dir / smali_path_name(class_index)).write_text(
                render_class(class_index, scale), encoding="utf-8"
            )
    helper_dir = project_dir / "smali" / PACKAGE.replace(".", "/")
    helper_dir.mkdir(parents=True, exist_ok=True)
    (helper_dir / "Helper.smali").write_text(render_helper(), encoding="utf-8")
    return plan


def dex_pool_size(dex_bytes: bytes) -> int:
    """The number of strings in a DEX file's string pool.

    The DEX header carries the size of the string-id table at a fixed offset.
    Reading it is a dozen lines of ``struct`` and needs no analysis library —
    which matters, because this script is meant to run with nothing installed
    but a JDK.
    """
    if len(dex_bytes) < 0x3C or dex_bytes[:4] != b"dex\n":
        return 0
    return int.from_bytes(dex_bytes[0x38:0x3C], "little")


def dex_pool_sizes(apk: Path) -> list[int]:
    """The string-pool size of every DEX file in an APK, in dex order."""
    import zipfile

    with zipfile.ZipFile(apk) as archive:
        names = sorted(n for n in archive.namelist() if n.endswith(".dex"))
        return [dex_pool_size(archive.read(name)) for name in names]


def find_apktool(explicit: str | None) -> list[str]:
    """The command that runs Apktool.

    A jar is run through ``java``; a bare ``apktool`` on ``PATH`` is run as it
    is. The jar is preferred because that is how the CI jobs install it.
    """
    jar = explicit or os.environ.get("DEXATLAS_APKTOOL_JAR", "")
    if jar:
        if not Path(jar).is_file():
            raise SystemExit(f"apktool jar not found: {jar}")
        java = shutil.which("java")
        if java is None:
            raise SystemExit("java not found on PATH; Apktool needs a JDK 21+")
        return [java, "-jar", jar]
    if shutil.which("apktool"):
        return ["apktool"]
    raise SystemExit(
        "Apktool not found. Set DEXATLAS_APKTOOL_JAR to its jar, or put apktool on PATH."
    )


def build_apk(project_dir: Path, output: Path, apktool: list[str]) -> float:
    """Assemble the smali tree into an APK. Returns the seconds it took."""
    started = time.monotonic()
    result = subprocess.run(
        [*apktool, "b", str(project_dir), "-o", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"apktool failed with exit code {result.returncode}")
    return time.monotonic() - started


def count_dex_files(apk: Path) -> list[str]:
    """The DEX files inside a built APK."""
    import zipfile

    with zipfile.ZipFile(apk) as archive:
        return sorted(name for name in archive.namelist() if name.endswith(".dex"))


def write_manifest(
    path: Path,
    *,
    scale_name: str,
    scale: Scale,
    plan: list[list[int]],
    apk: Path,
) -> dict[str, object]:
    """Write the ground truth: what the APK contains, in numbers.

    A test that checks the index against these numbers is checking it against
    what the generator actually wrote, not against a number somebody typed into
    a test file and then forgot to update.

    The per-DEX figures matter as much as the totals. The adapter applies two
    of its three limits to one DEX file at a time, so a test that only knows
    the APK's totals cannot tell whether a limit was reached.
    """
    work_methods = scale.methods_per_class - 1
    pool_sizes = dex_pool_sizes(apk)
    dex_files: list[dict[str, int | str]] = []
    for index, class_indexes in enumerate(plan):
        # The helper class lives in the first DEX file.
        helper_here = 1 if index == 0 else 0
        classes_here = len(class_indexes) + helper_here
        methods_here = len(class_indexes) * scale.methods_per_class + helper_here
        # A constructor is two instructions, a work method is the tier's count.
        instructions_here = len(class_indexes) * (2 + work_methods * scale.instructions_per_method)
        if helper_here:
            instructions_here += 1
        # Every work method loads two literals; each load is one use site, and
        # one use site is one row in the string index.
        const_strings_here = len(class_indexes) * work_methods * 2
        used_pool_values = {
            pool_index_for(class_index, method_index, scale.string_pool)
            for class_index in class_indexes
            for method_index in range(work_methods)
        }
        pool_here = pool_sizes[index] if index < len(pool_sizes) else 0
        dex_files.append(
            {
                "name": "classes.dex" if index == 0 else f"classes{index + 1}.dex",
                "class_count": classes_here,
                "method_count": methods_here,
                "instruction_count": instructions_here,
                "string_pool_size": pool_here,
                "string_uses": const_strings_here,
                # A pool entry used k times yields k rows, and an entry used
                # never yields one row. So the rows are the used values plus
                # one per use.
                "string_rows": len(used_pool_values) + const_strings_here,
            }
        )

    payload = {
        "scale": scale_name,
        "package": PACKAGE,
        "classes": [class_name(i) for i in range(scale.classes)],
        # The helper class is part of the APK too: one more class, and one more
        # method — the one every generated method calls. It has no constructor,
        # so it contributes no call of its own.
        "helper_class": HELPER_CLASS,
        "class_count": scale.classes + 1,
        "methods_per_class": scale.methods_per_class,
        "method_count": scale.total_methods + 1,
        # Every generated method makes exactly one call: the constructor calls
        # Object.<init>, the work methods call the helper.
        "expected_references": scale.total_methods,
        "instructions_per_method": scale.instructions_per_method,
        # A constructor is two instructions (the call and the return); a work
        # method is the tier's per-method count; the helper is one return.
        "expected_instructions": (
            scale.classes * (2 + work_methods * scale.instructions_per_method) + 1
        ),
        # Every work method loads two literals — its class's marker and one from
        # the shared pool — and each load is its own row in the string index.
        "expected_string_uses": scale.classes * work_methods * 2,
        "string_pool": scale.string_pool,
        "dex_files": dex_files,
        "apk_path": str(apk),
        "apk_size_bytes": apk.stat().st_size,
        "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "marker_sample": marker_string(0),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build(
    *,
    scale_name: str,
    scale: Scale,
    output_dir: Path,
    apktool: list[str],
    keep_sources: bool,
    max_methods_per_dex: int = MAX_METHODS_PER_DEX,
) -> tuple[Path, Path, dict[str, object]]:
    """Generate the APK and its ground-truth manifest. Returns their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    apk = output_dir / "large.apk"
    manifest_path = output_dir / "large.manifest.json"

    build_dir = Path(tempfile.mkdtemp(prefix="dexatlas-large-src-"))
    try:
        plan = write_sources(build_dir, scale, max_methods_per_dex)
        seconds = build_apk(build_dir, apk, apktool)
    finally:
        if not keep_sources:
            shutil.rmtree(build_dir, ignore_errors=True)
        else:
            print(f"sources kept in {build_dir}")

    payload = write_manifest(
        manifest_path,
        scale_name=scale_name,
        scale=scale,
        plan=plan,
        apk=apk,
    )
    payload["build_seconds"] = round(seconds, 2)
    payload["dex_file_count"] = len(count_dex_files(apk))
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return apk, manifest_path, payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a large synthetic APK for scale testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Scales: "
            + ", ".join(
                f"{name} ({scale.classes} classes x {scale.methods_per_class} methods, "
                f"{scale.instructions_per_method} instructions/method)"
                for name, scale in SCALES.items()
            )
        ),
    )
    parser.add_argument(
        "--scale",
        choices=sorted(SCALES),
        default=None,
        help=f"The tier to build. Defaults to ${SCALE_ENV_VAR} or '{DEFAULT_SCALE}'.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write the APK and its manifest. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--classes",
        type=int,
        default=None,
        help="Override the tier's class count.",
    )
    parser.add_argument(
        "--methods-per-class",
        type=int,
        default=None,
        help="Override the tier's method count per class.",
    )
    parser.add_argument(
        "--instructions-per-method",
        type=int,
        default=None,
        help="Override the tier's instruction count per method.",
    )
    parser.add_argument(
        "--string-pool",
        type=int,
        default=None,
        help="Override the tier's number of distinct literal strings.",
    )
    parser.add_argument(
        "--apktool-jar",
        default=None,
        help="Path to apktool.jar. Defaults to $DEXATLAS_APKTOOL_JAR, then apktool on PATH.",
    )
    parser.add_argument(
        "--max-methods-per-dex",
        type=int,
        default=MAX_METHODS_PER_DEX,
        help=(
            "How many methods to put in one DEX file. Lowering it splits a small "
            f"sample into several DEX files. Default: {MAX_METHODS_PER_DEX}."
        ),
    )
    parser.add_argument(
        "--keep-sources",
        action="store_true",
        help="Keep the generated smali tree instead of deleting it.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the ground-truth manifest as JSON instead of a summary.",
    )
    return parser.parse_args(argv)


def resolve_scale(args: argparse.Namespace) -> tuple[str, Scale]:
    """Pick the tier, and apply the overrides on top of it."""
    name = args.scale or os.environ.get(SCALE_ENV_VAR, DEFAULT_SCALE)
    if name not in SCALES:
        raise SystemExit(f"unknown scale: {name}; known scales: {', '.join(sorted(SCALES))}")
    base = SCALES[name]
    overrides = {
        "classes": args.classes,
        "methods_per_class": args.methods_per_class,
        "instructions_per_method": args.instructions_per_method,
        "string_pool": args.string_pool,
    }
    applied = {key: value for key, value in overrides.items() if value is not None}
    if not applied:
        return name, base
    return name, Scale(**{**asdict(base), **applied})


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    name, scale = resolve_scale(args)
    apktool = find_apktool(args.apktool_jar)

    temporary = args.output_dir is None
    output_dir = args.output_dir or Path(tempfile.mkdtemp(prefix="dexatlas-large-"))

    apk, manifest_path, payload = build(
        scale_name=name,
        scale=scale,
        output_dir=output_dir,
        apktool=apktool,
        keep_sources=args.keep_sources,
        max_methods_per_dex=args.max_methods_per_dex,
    )

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"scale          {name}")
        print(f"classes        {scale.classes:,}")
        print(f"methods        {scale.total_methods:,}")
        print(f"instructions   {scale.instructions_per_method:,} per method")
        print(f"dex files      {payload['dex_file_count']}")
        print(f"methods/dex    {args.max_methods_per_dex}")
        print(f"apk            {apk} ({payload['apk_size_bytes']:,} bytes)")
        print(f"built in       {payload['build_seconds']}s")
        print(f"manifest       {manifest_path}")
        if temporary:
            print(f"(temporary directory: {output_dir})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
