"""A workspace for the agent's tests, built by hand.

The APK in these tests is not an APK: it is a workspace with the rows an
analysis would have written, and the files the backends would have written
beside them. That is what makes the task suite *fixed* — the same classes,
the same strings, the same citations on every machine, whether or not a
backend is installed, and without a third-party APK anywhere near it.

Three things are here:

* :func:`build_demo` — the workspace;
* :func:`builder_for` — the builder the agent writes its records through,
  seeded with the analysis's own records so that the agent's evidence ids
  continue the analysis's instead of restarting beside them;
* :func:`make_orchestrator` — an orchestrator over the workspace.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dexatlas.agent.orchestrator import Orchestrator
from dexatlas.agent.providers.base import (
    AssistantTurn,
    ModelProvider,
    ModelResponse,
    Observation,
)
from dexatlas.agent.providers.scripted import ScriptedProvider, answer, conclusion, tool_call
from dexatlas.agent.state import Budget, TaskStore
from dexatlas.agent.tool_executor import McpToolClient, ToolExecutor
from dexatlas.core.evidence import EvidenceBuilder
from dexatlas.core.models import (
    ApkMetadata,
    ClassKind,
    ClassRef,
    Evidence,
    EvidenceKind,
    EvidenceLevel,
    InvocationKind,
    ManifestComponent,
    ManifestInfo,
    ManifestPermission,
    MethodRef,
    MethodReference,
    Project,
    ProjectStatus,
    Provenance,
    ResourceString,
    StringConstant,
)
from dexatlas.core.pipeline import Analyzer

#: The hash of an APK that does not exist. Nothing here is a real APK.
FAKE_SHA256 = "b" * 64

#: The project id that hash would have.
PROJECT_ID = Project.new_id(FAKE_SHA256)

#: The dex file the analysis is pretended to have read.
DEX_FILE = "classes.dex"

#: The class with three methods that share a name.
CRYPTO = "com.example.demo.Crypto"

#: The class that calls into it.
MAIN = "com.example.demo.MainActivity"

#: The descriptor that tells one of the three overloads from the others.
SIGN_DESCRIPTOR = "(Ljava/lang/String;)Ljava/lang/String;"

#: The id of one of them.
SIGN_METHOD_ID = f"{CRYPTO}.sign{SIGN_DESCRIPTOR}"

#: The string the search task looks for.
COLLECT_URL = "https://api.example.com/collect"

#: The tool versions the analysis is pretended to have run with.
TOOL_VERSIONS = {"androguard": "4.1.4", "apktool": "2.9.3", "jadx": "1.5.0"}

JAVA_SOURCE = """package com.example.demo;

public final class Crypto {

    public static String sign(int value) {
        return "int";
    }

    public static String sign(String value) {
        return "string";
    }

    public static String sign(String value, String other) {
        return "two";
    }
}
"""

MANIFEST_XML = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
          package="com.example.demo"
          android:versionCode="42"
          android:versionName="1.4.2">
    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <application android:label="Demo">
        <activity android:name="com.example.demo.MainActivity" android:exported="true" />
        <service android:name="com.example.demo.SyncService" android:exported="false" />
    </application>
</manifest>
"""


@dataclass
class Demo:
    """The workspace the agent's tests run against."""

    analyzer: Analyzer
    project_id: str
    workspace: Path
    evidence: list[Evidence]
    """The analysis's own records, with the ids they carry."""

    versions: dict[str, str | None] = field(default_factory=lambda: dict(TOOL_VERSIONS))
    """The tool versions the analysis ran with.

    A backend that was not installed is ``None`` here, which is what an
    incomplete analysis looks like from the outside.
    """

    def builder(self) -> EvidenceBuilder:
        """A builder for this analysis, seeded with its records.

        The agent's records are additional records of the same analysis, so
        their ids continue the analysis's sequence. Two sets of records both
        starting at ``E-0001`` in one report would send a reader to the
        wrong row.
        """
        builder = EvidenceBuilder(
            project_id=self.project_id,
            tool_versions=dict(self.versions),
            apk_sha256=FAKE_SHA256,
            workspace=self.workspace,
            dex_files=[DEX_FILE],
        )
        builder.items.extend(self.evidence)
        return builder


def _provenance(locator: str, tool: str = "androguard") -> list[Provenance]:
    """One citation, with the tool that wrote it."""
    return [
        Provenance(
            tool=tool,
            tool_version=TOOL_VERSIONS.get(tool),
            apk_sha256=FAKE_SHA256,
            locator=locator,
        )
    ]


def build_demo(
    settings: Any,
    tmp_path: Path,
    *,
    injection: str = "",
    missing_backends: tuple[str, ...] = (),
) -> Demo:
    """Build the workspace the agent's tests run against.

    ``injection`` is text that reads like an instruction. When it is given,
    it is written into the analysed source and indexed as a string of the
    APK — which is where an instruction found inside an APK really lives.

    ``missing_backends`` names the backends that did not take part in the
    analysis, which is what an incomplete analysis looks like from the
    outside.
    """
    analyzer = Analyzer(settings)
    workspace = tmp_path / "analysis"
    (workspace / "jadx" / "sources" / "com" / "example" / "demo").mkdir(parents=True, exist_ok=True)
    source = JAVA_SOURCE
    if injection:
        source = source.replace(
            "public final class Crypto {",
            f'public final class Crypto {{\n\n    public static final String NOTICE = "{injection}";',
        )
    (workspace / "jadx" / "sources" / "com" / "example" / "demo" / "Crypto.java").write_text(
        source, encoding="utf-8"
    )
    (workspace / "apktool").mkdir(parents=True, exist_ok=True)
    (workspace / "apktool" / "AndroidManifest.xml").write_text(MANIFEST_XML, encoding="utf-8")

    manifest = ManifestInfo(
        package="com.example.demo",
        version_code="42",
        version_name="1.4.2",
        min_sdk="24",
        target_sdk="34",
        permissions=[
            ManifestPermission(name="android.permission.INTERNET"),
            ManifestPermission(name="android.permission.ACCESS_FINE_LOCATION"),
        ],
        components=[
            ManifestComponent(kind="activity", name="com.example.demo.MainActivity", exported=True),
            ManifestComponent(kind="service", name="com.example.demo.SyncService", exported=False),
        ],
    )

    versions = {
        name: (None if name in missing_backends else version)
        for name, version in TOOL_VERSIONS.items()
    }
    project = Project(
        id=PROJECT_ID,
        apk=ApkMetadata(
            sha256=FAKE_SHA256,
            size_bytes=1024,
            path=Path("demo.apk"),
            dex_files=[DEX_FILE],
        ),
        status=ProjectStatus.COMPLETED,
        tool_versions=versions,
    )

    crypto_provenance = _provenance(f"androguard:{DEX_FILE}#{CRYPTO}")
    main_provenance = _provenance(f"androguard:{DEX_FILE}#{MAIN}")
    classes = [
        ClassRef(
            name=CRYPTO,
            kind=ClassKind.CLASS,
            access_flags=["public", "final"],
            method_count=3,
            provenance=crypto_provenance,
        ),
        ClassRef(
            name=MAIN,
            kind=ClassKind.CLASS,
            access_flags=["public"],
            method_count=1,
            provenance=main_provenance,
        ),
    ]
    methods = [
        MethodRef(
            class_name=CRYPTO,
            name="sign",
            descriptor="(I)Ljava/lang/String;",
            access_flags=["public", "static"],
            decompiled=True,
            provenance=crypto_provenance,
        ),
        MethodRef(
            class_name=CRYPTO,
            name="sign",
            descriptor=SIGN_DESCRIPTOR,
            access_flags=["public", "static"],
            decompiled=True,
            provenance=crypto_provenance,
        ),
        MethodRef(
            class_name=CRYPTO,
            name="sign",
            descriptor="(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
            access_flags=["public", "static"],
            decompiled=True,
            provenance=crypto_provenance,
        ),
        MethodRef(
            class_name=MAIN,
            name="onCreate",
            descriptor="(Landroid/os/Bundle;)V",
            access_flags=["protected"],
            decompiled=True,
            provenance=main_provenance,
        ),
    ]
    references = [
        MethodReference(
            caller="com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V",
            callee=SIGN_METHOD_ID,
            kind=InvocationKind.STATIC,
            provenance=_provenance(
                f"androguard:{DEX_FILE}#com.example.demo.MainActivity.onCreate"
                "(Landroid/os/Bundle;)V"
            ),
        )
    ]
    strings = [
        StringConstant(
            value=COLLECT_URL,
            class_name=MAIN,
            method_name="onCreate",
            provenance=main_provenance,
        )
    ]
    if injection:
        strings.append(
            StringConstant(
                value=injection,
                class_name=CRYPTO,
                method_name="notice",
                provenance=crypto_provenance,
            )
        )

    store = analyzer.store
    store.save_project(project, workspace, manifest)
    counts = store.save_symbols(
        PROJECT_ID,
        classes,
        methods,
        [],
        references,
        strings,
        [ResourceString(name="app_name", value="Demo")],
    )
    project.class_count = counts.classes
    project.method_count = counts.methods
    project.reference_count = counts.references
    project.call_edge_count = counts.call_edges
    project.resource_count = counts.resources
    project.evidence_count = 3
    store.save_project(project, workspace, manifest)

    builder = EvidenceBuilder(
        project_id=PROJECT_ID,
        tool_versions=versions,
        apk_sha256=FAKE_SHA256,
        workspace=workspace,
        dex_files=[DEX_FILE],
    )
    builder.add(
        kind=EvidenceKind.DECLARATION,
        level=EvidenceLevel.VERIFIED,
        summary="Package com.example.demo (versionName=1.4.2, minSdk=24, targetSdk=34)",
        provenance=[
            Provenance(
                tool="apktool",
                tool_version=TOOL_VERSIONS["apktool"],
                apk_sha256=FAKE_SHA256,
                locator="apktool:AndroidManifest.xml",
            )
        ],
    )
    builder.add(
        kind=EvidenceKind.CROSS_REFERENCE,
        level=EvidenceLevel.VERIFIED,
        summary=f"{SIGN_METHOD_ID} is called from 1 location(s)",
        provenance=references[0].provenance,
    )
    builder.add(
        kind=EvidenceKind.CODE_LOCATED,
        level=EvidenceLevel.VERIFIED,
        summary=f"Class {CRYPTO}",
        provenance=[
            Provenance(
                tool="jadx",
                tool_version=TOOL_VERSIONS["jadx"],
                apk_sha256=FAKE_SHA256,
                locator="jadx:sources/com/example/demo/Crypto.java",
            )
        ],
    )
    evidence = builder.build()
    store.save_evidence(PROJECT_ID, evidence)

    return Demo(
        analyzer=analyzer,
        project_id=PROJECT_ID,
        workspace=workspace,
        evidence=evidence,
        versions=versions,
    )


def builder_for(demo: Demo) -> Callable[[str], EvidenceBuilder]:
    """The factory the orchestrator asks for a builder with."""

    def build(_project_id: str) -> EvidenceBuilder:
        return demo.builder()

    return build


def make_orchestrator(
    demo: Demo,
    provider: ModelProvider,
    *,
    store: TaskStore,
    limits: Budget | None = None,
    executor: ToolExecutor | None = None,
    progress: Callable[[Any], None] | None = None,
    **kwargs: Any,
) -> Orchestrator:
    """An orchestrator over the demo workspace."""
    client = McpToolClient(demo.analyzer)
    return Orchestrator(
        provider=provider,
        client=client,
        builder_for=builder_for(demo),
        store=store,
        executor=executor or ToolExecutor(client, timeout=5.0),
        limits=limits or Budget(max_tokens=4000, max_iterations=6, max_seconds=30.0),
        progress=progress,
        **kwargs,
    )


def observation_evidence_ids(request: Any) -> list[str]:
    """The evidence ids the tools' answers carried, in order.

    A model can only cite an evidence id it has been given, and the id travels
    with the observation it belongs to.
    """
    ids: list[str] = []
    for turn in request.turns:
        if not isinstance(turn, Observation):
            continue
        try:
            document = json.loads(turn.content)
        except json.JSONDecodeError:
            continue
        if isinstance(document, dict):
            identifier = document.get("evidence_id")
            if isinstance(identifier, str):
                ids.append(identifier)
    return ids


def last_evidence_id(request: Any) -> str:
    """The evidence id of the last thing the tools read."""
    ids = observation_evidence_ids(request)
    return ids[-1] if ids else ""


def calls_made(request: Any) -> int:
    """How many tool calls the model has asked for so far."""
    return sum(len(turn.tool_calls) for turn in request.turns if isinstance(turn, AssistantTurn))


def scripted_provider(
    calls: list[tuple[str, dict[str, Any]]],
    *,
    statement: str = "the analysis says so",
    limitations: list[str] | None = None,
) -> ScriptedProvider:
    """A provider that asks for the task's tools, then answers.

    The script is the same on every run and on every machine: the calls are
    named here, and the answer cites the evidence the last call produced. The
    id is read out of the request rather than written down, so the script
    does not have to know what the ids will be.
    """

    def ask(request: Any) -> ModelResponse:
        made = calls_made(request)
        name, arguments = calls[made]
        return tool_call(name, arguments, call_id=f"call-{made + 1}")

    def reply(request: Any) -> ModelResponse:
        evidence_id = last_evidence_id(request)
        return answer(
            [conclusion(statement, evidence_ids=[evidence_id] if evidence_id else [])],
            limitations=limitations,
        )

    return ScriptedProvider(responses=[ask] * len(calls) + [reply])


__all__ = [
    "COLLECT_URL",
    "CRYPTO",
    "DEX_FILE",
    "FAKE_SHA256",
    "JAVA_SOURCE",
    "MAIN",
    "MANIFEST_XML",
    "PROJECT_ID",
    "SIGN_DESCRIPTOR",
    "SIGN_METHOD_ID",
    "TOOL_VERSIONS",
    "Demo",
    "build_demo",
    "builder_for",
    "calls_made",
    "last_evidence_id",
    "make_orchestrator",
    "observation_evidence_ids",
    "scripted_provider",
]
