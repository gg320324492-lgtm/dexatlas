"""Tasks about an APK whose classes are spread over more than one DEX, and
about where a piece of evidence says it came from.

The multidex sample is the interesting one: ``SharedConfig`` is defined in
**both** DEX files, and the two definitions disagree — ``origin()`` returns
``"primary-dex"`` in one and ``"secondary-dex"`` in the other, and
``timeoutMillis()`` returns 1000 in one and 5000 in the other. The two Smali
files say so in their own comments, and they are the sample's own files.

Which of the two a reader sees depends on the backend that answered. JADX
decompiles the APK and keeps the class it read last, so the Java says
``secondary-dex``. Apktool's Smali fallback searches its decoded directories
in sorted order, and ``smali/`` sorts before ``smali_classes2/``, so the
Smali says ``primary-dex``. Two tasks below ask the same question in two
configurations, and their expected answers differ — which is the whole point
of a configuration being part of a task.

The provenance tasks are the other half: a record that says where it came
from, and a record that can be checked against the APK it was made from.
"""

from __future__ import annotations

from benchmarks import probes
from benchmarks.model import Category, Configuration, Sample, Task

MULTIDEX = Category.MULTIDEX
PROVENANCE = Category.PROVENANCE

#: The digest of examples/demo-app/demo.apk, computed over the file's bytes.
DEMO_SHA256 = "80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9"


def _tasks() -> list[Task]:
    return [
        Task(
            id="multidex.dex-file-count",
            category=MULTIDEX,
            question="How many DEX files does the multidex sample hold?",
            sample=Sample.MULTIDEX,
            probe=probes.dex_files(),
            source=(
                "examples/multidex-app/multidex.apk holds classes.dex and classes2.dex; the "
                "sample's two Smali directories, smali/ and smali_classes2/, are the two of "
                "them."
            ),
            expect_count=2,
            note="One DEX is the ordinary case; this sample exists to be two.",
        ),
        Task(
            id="multidex.classes-only-in-second-dex",
            category=MULTIDEX,
            question="Which classes does the multidex sample keep in its second DEX file?",
            sample=Sample.MULTIDEX,
            probe=probes.classes_from_dex("classes2.dex"),
            source=(
                "examples/multidex-app/smali_classes2/com/example/multidex/ holds "
                "PayloadLoader.smali, SecondaryHelper.smali and SharedConfig.smali."
            ),
            must_contain=(
                "com.example.multidex.PayloadLoader",
                "com.example.multidex.SecondaryHelper",
            ),
            note="Three classes, one of which also exists in the first DEX file.",
        ),
        Task(
            id="multidex.shared-config-in-both-dex",
            category=MULTIDEX,
            question="Which DEX files hold the SharedConfig class?",
            sample=Sample.MULTIDEX,
            probe=probes.class_provenance("com.example.multidex.SharedConfig"),
            source=(
                "examples/multidex-app/smali/com/example/multidex/SharedConfig.smali and "
                "examples/multidex-app/smali_classes2/com/example/multidex/SharedConfig.smali "
                "both define the class."
            ),
            must_contain=(
                "androguard -> androguard:classes.dex#com.example.multidex.SharedConfig",
                "androguard -> androguard:classes2.dex#com.example.multidex.SharedConfig",
            ),
            note="Both DEX files, and the record has to say so rather than pick one.",
        ),
        Task(
            id="multidex.shared-config-method-in-both-dex",
            category=MULTIDEX,
            question="Which DEX files hold the SharedConfig.origin method?",
            sample=Sample.MULTIDEX,
            probe=probes.method_provenance("com.example.multidex.SharedConfig", "origin"),
            source=(
                "Both SharedConfig.smali files declare "
                "`.method public static origin()Ljava/lang/String;`."
            ),
            expect_count=2,
            note="A method can be in two DEX files at once; one record, two sources.",
        ),
        Task(
            id="multidex.shared-config-java-comes-from-second-dex",
            category=MULTIDEX,
            question="What does SharedConfig.origin return, in the decompiled Java?",
            sample=Sample.MULTIDEX,
            probe=probes.class_source("com.example.multidex.SharedConfig"),
            source=(
                "examples/multidex-app/smali_classes2/com/example/multidex/SharedConfig.smali: "
                'the origin method holds `const-string v0, "secondary-dex"`.'
            ),
            must_contain=("secondary-dex", "classes2.dex"),
            note=(
                "The decompiler keeps the class it read last, so the Java is the classes2.dex "
                'definition — the one whose Smali says "secondary-dex".'
            ),
        ),
        Task(
            id="multidex.shared-config-smali-comes-from-first-dex",
            category=MULTIDEX,
            configuration=Configuration.NO_JADX,
            question="What does SharedConfig.origin return, in the Smali?",
            sample=Sample.MULTIDEX,
            probe=probes.class_source("com.example.multidex.SharedConfig"),
            source=(
                "examples/multidex-app/smali/com/example/multidex/SharedConfig.smali: the origin "
                'method holds `const-string v0, "primary-dex"`, and that file\'s own comment '
                "says the primary dex wins because the directories are searched in sorted order."
            ),
            must_contain=("primary-dex", "smali/com/example/multidex/SharedConfig.smali"),
            note=(
                "The same question as the task above, in a configuration without the "
                "decompiler — and the answer is the other one."
            ),
        ),
        Task(
            id="multidex.class-count-is-not-the-dex-count",
            category=MULTIDEX,
            question="How many classes does the multidex sample define?",
            sample=Sample.MULTIDEX,
            probe=probes.indexed_classes(),
            source=(
                "The five sample Smali files name five classes — PrimaryHelper, SecondaryHelper, "
                "PayloadLoader, and SharedConfig twice — but only four names, because "
                "SharedConfig is defined in both DEX files."
            ),
            expect_count=4,
            note="Five definitions, four classes: the duplicate is merged.",
        ),
        Task(
            id="provenance.crypto-has-two-sources",
            category=PROVENANCE,
            question="Where does the demo application's Crypto class come from?",
            sample=Sample.DEMO,
            probe=probes.class_provenance("com.example.demo.Crypto"),
            source=(
                "examples/demo-app/smali/com/example/demo/Crypto.smali is the DEX reader's view "
                "and the decompiler wrote sources/com/example/demo/Crypto.java."
            ),
            must_contain=(
                "androguard -> androguard:classes.dex#com.example.demo.Crypto",
                "jadx -> jadx:sources/com/example/demo/Crypto.java",
            ),
            expect_count=2,
            note="Two backends, two files, one class.",
        ),
        Task(
            id="provenance.r-class-comes-only-from-the-decompiler",
            category=PROVENANCE,
            question="Where does the demo application's R class come from?",
            sample=Sample.DEMO,
            probe=probes.class_provenance("com.example.demo.R"),
            source=(
                "The independent DEX reader in benchmarks/dexreader.py lists four classes in "
                "examples/demo-app/demo.apk — Crypto, MainActivity, NetworkClient and "
                "SyncService — and no R: the class is the decompiler's, made from the "
                "resource table."
            ),
            must_contain=("jadx -> jadx:sources/com/example/demo/R.java",),
            must_not_contain=("androguard",),
            expect_count=1,
            note="A class that exists in the report and not in the DEX.",
        ),
        Task(
            id="provenance.method-locator-names-the-method",
            category=PROVENANCE,
            question="Where does the record for Crypto.sign point?",
            sample=Sample.DEMO,
            probe=probes.method_provenance("com.example.demo.Crypto", "sign"),
            source=(
                "The DEX file's own record of the method: the locator names the DEX file, "
                "the class inside it and the method inside that."
            ),
            must_contain=(
                "androguard:classes.dex#com.example.demo.Crypto#com.example.demo.Crypto.sign("
                "Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
            ),
            note="A locator that names the DEX file and the method inside it.",
        ),
        Task(
            id="provenance.records-name-the-apk-they-were-made-from",
            category=PROVENANCE,
            question="Which APK were the demo application's records made from?",
            sample=Sample.DEMO,
            probe=probes.provenance_digests("com.example.demo.Crypto"),
            source=(
                "The SHA-256 of examples/demo-app/demo.apk, computed over the file's bytes: "
                f"{DEMO_SHA256}."
            ),
            must_contain=(f"apk_sha256={DEMO_SHA256}",),
            note="A record that cannot be tied to an APK is a record of nothing.",
        ),
        Task(
            id="provenance.tool-versions-are-recorded",
            category=PROVENANCE,
            question="Which versions of the backends did the analysis run?",
            sample=Sample.DEMO,
            probe=probes.recorded_tool_versions(),
            source=(
                "The versions are the ones the backends report; the APK's own files do not "
                "carry them, so this is a fact about the analysis rather than about the "
                "sample."
            ),
            must_contain=("jadx=", "apktool=", "androguard="),
            note="A version belongs to the tool that ran, not to the file.",
        ),
        Task(
            id="provenance.smali-locator-names-the-apktool-tree",
            category=PROVENANCE,
            configuration=Configuration.NO_JADX,
            question="Where does the demo application's Smali come from?",
            sample=Sample.DEMO,
            probe=probes.class_source("com.example.demo.Crypto"),
            source=(
                "Apktool decodes the APK into its own tree; the Smali for this class is at "
                "smali/com/example/demo/Crypto.smali inside it."
            ),
            must_contain=("locator=apktool:smali/com/example/demo/Crypto.smali",),
            note="The locator names the artefact, not the machine that made it.",
        ),
    ]


TASKS = _tasks()
