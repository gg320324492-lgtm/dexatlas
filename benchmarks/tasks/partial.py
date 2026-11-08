"""Tasks about a missing backend, and about questions that have no answer.

The first half is about **partial results**. This project runs its suite in
three configurations — every backend, the decompiler absent, the APK reader
absent — and the difference between them is not a smaller answer but a
*different* answer: with no decompiler the code is still readable, as Smali;
with no APK reader there is no manifest and no resource table at all, and the
analysis has to say that rather than produce an empty-looking report. Each
task below says which configuration it is asked in, because that is part of
the question.

The second half is about **questions that cannot be answered**, and it is the
category that catches a system which confabulates. Every task in it is
*scored*: the right answer is an absence, so an answer that comes back with
evidence fails. A system that names a caller for a method nothing calls, or a
receiver for an APK that declares none, does not pass by being plausible.

Each expectation names the file that establishes it — a Smali file in which no
instruction names the method, a manifest with no such element, a sample with
no ``res/`` directory at all.
"""

from __future__ import annotations

from benchmarks import probes
from benchmarks.model import Category, Configuration, Sample, Task

PARTIAL = Category.PARTIAL
UNANSWERABLE = Category.UNANSWERABLE

#: The qualified names the index holds for the methods nothing calls.
DIGEST_OF = "com.example.demo.Crypto.digestOf(Ljava/lang/String;)Ljava/lang/String;"
OBFUSCATE = "com.example.demo.Crypto.obfuscate(Ljava/lang/String;)Ljava/lang/String;"
ON_BIND = "com.example.demo.SyncService.onBind(Landroid/content/Intent;)Landroid/os/IBinder;"
HANDLER_NAME = "com.example.wide.Handler.name()Ljava/lang/String;"
SHARED_ORIGIN = "com.example.multidex.SharedConfig.origin()Ljava/lang/String;"


def _tasks() -> list[Task]:
    return [
        Task(
            id="partial.no-jadx-the-source-is-smali",
            category=PARTIAL,
            configuration=Configuration.NO_JADX,
            question="What does the demo application's Crypto class look like when the "
            "decompiler is not installed?",
            sample=Sample.DEMO,
            probe=probes.class_source("com.example.demo.Crypto"),
            source=(
                "examples/demo-app/smali/com/example/demo/Crypto.smali — with no decompiler "
                "there is nothing to turn it into Java, and the Smali is the code."
            ),
            must_contain=("kind=smali",),
            note="The code is still readable; it is just not Java.",
        ),
        Task(
            id="partial.no-jadx-the-index-is-unchanged",
            category=PARTIAL,
            configuration=Configuration.NO_JADX,
            question="How many methods does the demo application have, when the decompiler "
            "is not installed?",
            sample=Sample.DEMO,
            probe=probes.indexed_methods(),
            source=(
                "examples/demo-app/smali/com/example/demo/ holds eight method definitions — "
                "three in Crypto, three in MainActivity, one in NetworkClient, one in "
                "SyncService — and the DEX reader holds all eight without a decompiler."
            ),
            expect_count=8,
            note=(
                "The symbol index does not depend on the decompiler, so losing the "
                "decompiler costs the Java and nothing else."
            ),
        ),
        Task(
            id="partial.no-jadx-nothing-is-decompiled",
            category=PARTIAL,
            configuration=Configuration.NO_JADX,
            question="Is any of the demo application's methods decompiled, when the "
            "decompiler is not installed?",
            sample=Sample.DEMO,
            probe=probes.indexed_methods(),
            source=(
                "Decompiled source comes from the decompiler alone; with none installed no "
                "method has any."
            ),
            must_contain=("decompiled=False",),
            must_not_contain=("decompiled=True",),
            note="A method with no decompiled source says so, rather than looking empty.",
        ),
        Task(
            id="partial.no-jadx-the-failure-is-recorded",
            category=PARTIAL,
            configuration=Configuration.NO_JADX,
            question="Does the analysis record that the decompiler was missing?",
            sample=Sample.DEMO,
            probe=probes.recorded_errors(),
            source=(
                "A backend that cannot be found is a value, not an exception: the analysis "
                "records the failure and carries on with what it has."
            ),
            must_contain=("jadx", "not_installed"),
            note="The gap is recorded, not hidden.",
        ),
        Task(
            id="partial.no-apktool-there-is-no-manifest",
            category=PARTIAL,
            configuration=Configuration.NO_APKTOOL,
            question="What package does the demo application declare, when the APK reader "
            "is not installed?",
            sample=Sample.DEMO,
            probe=probes.manifest_value("package"),
            source=(
                "The manifest is read by Apktool; with Apktool absent there is no manifest to "
                "read, and the analysis holds none."
            ),
            expect_empty=True,
            note="Nothing is not the same as something with the wrong value.",
        ),
        Task(
            id="partial.no-apktool-there-are-no-resources",
            category=PARTIAL,
            configuration=Configuration.NO_APKTOOL,
            question="What are the demo application's resource strings, when the APK reader "
            "is not installed?",
            sample=Sample.DEMO,
            probe=probes.resource_rows(),
            source=(
                "examples/demo-app/res/values/strings.xml holds one string, and Apktool is "
                "what decodes the resource table it came from."
            ),
            expect_empty=True,
            note="The resource table is gone with the backend that reads it.",
        ),
        Task(
            id="partial.no-apktool-the-java-is-still-there",
            category=PARTIAL,
            configuration=Configuration.NO_APKTOOL,
            question="What does the demo application's Crypto class look like when the APK "
            "reader is not installed?",
            sample=Sample.DEMO,
            probe=probes.class_source("com.example.demo.Crypto"),
            source=(
                "The decompiler reads the DEX files itself; it does not need Apktool, so the "
                "Java is still there."
            ),
            must_contain=("kind=java",),
            note="Losing one backend costs that backend's contribution, not the whole.",
        ),
        Task(
            id="partial.no-apktool-the-failure-is-recorded",
            category=PARTIAL,
            configuration=Configuration.NO_APKTOOL,
            question="Does the analysis record that the APK reader was missing?",
            sample=Sample.DEMO,
            probe=probes.recorded_errors(),
            source=(
                "A backend that cannot be found is a value, not an exception: the analysis "
                "records the failure and carries on with what it has."
            ),
            must_contain=("apktool", "not_installed"),
            note="The gap is recorded, not hidden.",
        ),
        Task(
            id="unanswerable.crypto-digestof-has-no-callers",
            category=UNANSWERABLE,
            question="Which method calls Crypto.digestOf?",
            sample=Sample.DEMO,
            probe=probes.callers(DIGEST_OF),
            source=(
                "No instruction in any of examples/demo-app/smali/ names Crypto.digestOf: the "
                "method declares it, and nothing calls it."
            ),
            expect_empty=True,
            must_not_contain=(
                "MainActivity",
                "NetworkClient",
                "SyncService",
                "Crypto.sign",
                "Crypto.obfuscate",
            ),
            note="Naming a caller here would be a fabrication.",
        ),
        Task(
            id="unanswerable.crypto-obfuscate-has-no-callers",
            category=UNANSWERABLE,
            question="Which method calls Crypto.obfuscate?",
            sample=Sample.DEMO,
            probe=probes.callers(OBFUSCATE),
            source=("No instruction in any of examples/demo-app/smali/ names Crypto.obfuscate."),
            expect_empty=True,
            must_not_contain=(
                "MainActivity",
                "NetworkClient",
                "SyncService",
                "Crypto.sign",
                "Crypto.digestOf",
            ),
            note="A plausible-sounding answer here would be a fabrication.",
        ),
        Task(
            id="unanswerable.syncservice-onbind-has-no-callers",
            category=UNANSWERABLE,
            question="Which method calls SyncService.onBind?",
            sample=Sample.DEMO,
            probe=probes.callers(ON_BIND),
            source=("No instruction in any of examples/demo-app/smali/ names SyncService.onBind."),
            expect_empty=True,
            must_not_contain=("MainActivity", "NetworkClient", "Crypto"),
            note="The method is declared by a service and called by the framework, not by the APK.",
        ),
        Task(
            id="unanswerable.handler-name-has-no-callers",
            category=UNANSWERABLE,
            question="Which method calls the Handler interface's name method?",
            sample=Sample.WIDE,
            probe=probes.callers(HANDLER_NAME),
            source=(
                "No instruction in any of examples/wide-app/smali/ names Handler.name — the "
                "factory calls handle, and the implementations implement it."
            ),
            expect_empty=True,
            must_not_contain=("HandlerFactory", "JsonHandler", "XmlHandler"),
            note="The interface declares it; nothing in the APK calls it.",
        ),
        Task(
            id="unanswerable.shared-config-origin-has-no-callers",
            category=UNANSWERABLE,
            question="Which method calls SharedConfig.origin?",
            sample=Sample.MULTIDEX,
            probe=probes.callers(SHARED_ORIGIN),
            source=(
                "No instruction in examples/multidex-app/smali/ or "
                "examples/multidex-app/smali_classes2/ names SharedConfig.origin."
            ),
            expect_empty=True,
            must_not_contain=("PrimaryHelper", "SecondaryHelper", "PayloadLoader"),
            note="Two definitions of the method, and neither of them is called.",
        ),
        Task(
            id="unanswerable.demo-mentions-no-google-accounts",
            category=UNANSWERABLE,
            question="Does the demo application mention Google's accounts service?",
            sample=Sample.DEMO,
            probe=probes.search_results("accounts.google.com"),
            source=(
                'No file under examples/demo-app/ contains the string "accounts.google.com": '
                "the four Smali files and res/values/strings.xml hold the whole of the "
                "sample's text."
            ),
            expect_empty=True,
            note="A search that finds nothing has to say so.",
        ),
        Task(
            id="unanswerable.demo-declares-no-receiver",
            category=UNANSWERABLE,
            question="Does the demo application declare a broadcast receiver?",
            sample=Sample.DEMO,
            probe=probes.manifest_components(kind="receiver"),
            source=(
                "examples/demo-app/AndroidManifest.xml declares an <activity> and a <service> "
                "and no <receiver>."
            ),
            expect_empty=True,
            note="The obfuscated sample has one; this one does not.",
        ),
        Task(
            id="unanswerable.demo-declares-no-provider",
            category=UNANSWERABLE,
            question="Does the demo application declare a content provider?",
            sample=Sample.DEMO,
            probe=probes.manifest_components(kind="provider"),
            source=(
                "examples/demo-app/AndroidManifest.xml declares no <provider>, although "
                'SyncService.onBind returns the string "com.example.demo.provider" — a name '
                "that looks like one and is not a declaration."
            ),
            expect_empty=True,
            note="A string that looks like a component is not a component.",
        ),
        Task(
            id="unanswerable.strings-app-declares-no-activity",
            category=UNANSWERABLE,
            question="Does the strings sample declare an activity?",
            sample=Sample.STRINGS,
            probe=probes.manifest_components(kind="activity"),
            source=(
                "examples/strings-app/AndroidManifest.xml has an <application> and no "
                "<activity> element."
            ),
            expect_empty=True,
            note="The right answer is that there is none.",
        ),
        Task(
            id="unanswerable.multidex-declares-no-resources",
            category=UNANSWERABLE,
            question="Does the multidex sample declare any resource strings?",
            sample=Sample.MULTIDEX,
            probe=probes.resource_rows(),
            source=(
                "examples/multidex-app/ holds no res/ directory: the sample declares no "
                "resource strings."
            ),
            expect_empty=True,
            note="Zero, and zero is an answer that has to be given as zero.",
        ),
        Task(
            id="unanswerable.apk-is-not-signed",
            category=UNANSWERABLE,
            question="Which organisation signed the demo application?",
            sample=Sample.DEMO,
            probe=probes.apk_certificate(),
            source=(
                "examples/demo-app/demo.apk holds no META-INF certificate file, so there is "
                "no signer to name."
            ),
            expect_empty=True,
            note="A plausible certificate authority here would be a fabrication.",
        ),
    ]


TASKS = _tasks()
