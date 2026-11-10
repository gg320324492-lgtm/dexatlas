"""Tasks about where an answer was found — which file holds the code.

The questions in this module ask for a **location** rather than a value: which
Smali file a class lives in, which resource file declares a name, which method
holds a constant, which DEX a class was loaded from. The existing categories
ask what the answer *is*; these ask where a reader — and a system that answers
by retrieving source text — would have to go to find it.
``docs/benchmarks/task-set.md`` section 10.3 asked for exactly this: a task
set for a model with source retrieval needs questions about *where* the
answer was found, not only what it was.

The expectations are still read out of the sample's own files, and the file
that establishes an expectation is usually the very thing the answer names:
``examples/demo-app/res/values/strings.xml`` really is the file
``app_name`` is declared in, and ``examples/obfuscated-app/smali/a/a/b.smali``
really is the Smali file of the class the index calls ``a.a.b``. A second
person confirms an expectation by opening the file the answer names and
reading the line the task quotes.

The wrong answer a location question invites is a **neighbouring location**:
the other class in the same package, the other Smali directory, the other
method of the same class, the manifest element that carries the same text as
the resource declaration. ``must_not_contain`` names those neighbours, which
is the shape a wrong answer takes here.
"""

from __future__ import annotations

from benchmarks import probes
from benchmarks.model import Category, Configuration, Sample, Task

WHERESOURCE = Category.WHERESOURCE

#: The qualified name the index holds for the XmlHandler constructor, whose
#: construction site this module asks about.
XML_INIT = "com.example.wide.XmlHandler.<init>()V"


def _tasks() -> list[Task]:
    return [
        Task(
            id="wheresource.endpoint-method.demo",
            category=WHERESOURCE,
            question="In which method does the demo application set its API endpoint constant?",
            sample=Sample.DEMO,
            probe=probes.method_source("com.example.demo.MainActivity", "<init>"),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali: the <init> "
                'method holds `const-string p0, "https://api.example.com/v1"` — the onCreate '
                "method, not the constructor, is where the key string lives."
            ),
            must_contain=("https://api.example.com/v1", "<init>"),
            must_not_contain=("sk_live",),
            note="The constructor, and the record's own locator names it whichever form the source comes back in.",
        ),
        Task(
            id="wheresource.app-name-resource-file.demo",
            category=WHERESOURCE,
            question="In which resource file is the demo application's app_name declared?",
            sample=Sample.DEMO,
            probe=probes.resource_rows("app_name"),
            source=(
                "examples/demo-app/res/values/strings.xml: the file's only element is "
                '`<string name="app_name">DexAtlas Demo</string>` — the manifest carries the '
                "label, but the resource declaration is this file."
            ),
            must_contain=("app_name", "res/values/strings.xml"),
            must_not_contain=("AndroidManifest.xml",),
            note="The declaration file, not the value and not the manifest label.",
        ),
        Task(
            id="wheresource.service-smali-file.demo",
            category=WHERESOURCE,
            configuration=Configuration.NO_JADX,
            question=(
                "With no decompiler installed, which file holds the demo "
                "application's SyncService source?"
            ),
            sample=Sample.DEMO,
            probe=probes.class_source("com.example.demo.SyncService"),
            source=(
                "examples/demo-app/smali/com/example/demo/SyncService.smali: the onBind "
                'method holds `const-string v0, "com.example.demo.provider"`, and the file '
                "sits in the smali/ directory that a decode without a decompiler produces."
            ),
            must_contain=(
                "com.example.demo.provider",
                "smali/com/example/demo/SyncService.smali",
            ),
            must_not_contain=("MainActivity",),
            note=(
                "In the no-decompiler configuration the Smali file is the only source "
                "there is, and the answer has to name it."
            ),
        ),
        Task(
            id="wheresource.api-key-returner.strings",
            category=WHERESOURCE,
            question="In which method does the strings sample return its API key?",
            sample=Sample.STRINGS,
            probe=probes.method_source("com.example.strings.Constants", "apiKey"),
            source=(
                "examples/strings-app/smali/com/example/strings/Constants.smali: the "
                'apiKey method holds `const-string v0, "sk_live_PLACEHOLDER_NOT_A_REAL_KEY"`; '
                'the fallbackKey method below it returns the "sk_test_" value instead.'
            ),
            must_contain=("apiKey",),
            must_not_contain=("fallbackKey",),
            note=(
                "The method located by name; the decompiled body folds the constant into "
                "the field it returns, so the value is the Smali's fact, not the Java's."
            ),
        ),
        Task(
            id="wheresource.base-url-field-file.strings",
            category=WHERESOURCE,
            question=(
                "In which file are the strings sample's hard-coded endpoint fields declared?"
            ),
            sample=Sample.STRINGS,
            probe=probes.class_source("com.example.strings.Constants"),
            source=(
                "examples/strings-app/smali/com/example/strings/Constants.smali: the field "
                "declaration `.field public static final BASE_URL:Ljava/lang/String; = "
                '"https://api.example.com/v2"` is in the class the file defines.'
            ),
            must_contain=("BASE_URL", "Constants.java"),
            must_not_contain=("MainActivity",),
            note="The declaring class's file, not a class that uses the field.",
        ),
        Task(
            id="wheresource.bearer-header-builder.strings",
            category=WHERESOURCE,
            question="Where is the strings sample's Bearer header built?",
            sample=Sample.STRINGS,
            probe=probes.method_source("com.example.strings.Constants", "authHeader"),
            source=(
                "examples/strings-app/smali/com/example/strings/Constants.smali: the "
                'authHeader method holds `const-string v1, "Bearer "` and appends the '
                "apiKey call's result to it."
            ),
            must_contain=("Bearer", "authHeader"),
            must_not_contain=("fallbackKey",),
            note="The method that assembles the header, named by its own locator.",
        ),
        Task(
            id="wheresource.obfuscated-class-file.obfuscated",
            category=WHERESOURCE,
            question=(
                "In which DEX does the obfuscated sample keep the class a.a.b, "
                "and which file does the decompiler put it in?"
            ),
            sample=Sample.OBFUSCATED,
            probe=probes.class_provenance("a.a.b"),
            source=(
                "examples/obfuscated-app/smali/a/a/b.smali: the file declares "
                "`.class public La/a/b;` under smali/, which makes it a classes.dex class, "
                "and the class name is the file name: the decompiled output for a.a.b sits "
                "at sources/a/a/b.java. The neighbouring paths a/a/a and a/b/a are other classes."
            ),
            expect_count=2,
            must_contain=("a/a/b.java", "classes.dex"),
            must_not_contain=("a/b/a", "a/a/a"),
            note=(
                "The obfuscated name is also the file name here; a wrong answer names a "
                "neighbouring class's file."
            ),
        ),
        Task(
            id="wheresource.generic-text-message-file.obfuscated",
            category=WHERESOURCE,
            configuration=Configuration.NO_JADX,
            question=(
                "With no decompiler installed, which file holds the obfuscated "
                "sample's 'generic_text_message' string?"
            ),
            sample=Sample.OBFUSCATED,
            probe=probes.class_source("a.a.b"),
            source=(
                "examples/obfuscated-app/smali/a/a/b.smali: the method named a holds "
                '`const-string v1, "generic_text_message"`; the neighbouring files '
                "a/a/a.smali, a/a/b/a.smali and a/b/a.smali do not carry it."
            ),
            must_contain=("generic_text_message", "a/a/b.smali"),
            must_not_contain=("a/b/a", "a/a/a"),
            note="A string located in a file whose class name gives nothing away.",
        ),
        Task(
            id="wheresource.handler-declaration-file.wide",
            category=WHERESOURCE,
            question="In which file is the Handler interface's handle method declared?",
            sample=Sample.WIDE,
            probe=probes.method_source("com.example.wide.Handler", "handle"),
            source=(
                "examples/wide-app/smali/com/example/wide/Handler.smali: the file declares "
                "`.method public abstract handle(Ljava/lang/String;)Ljava/lang/String;` — the "
                "implementations in JsonHandler.smali and XmlHandler.smali hold bodies, and "
                "the file's own comment says they are the two implementations."
            ),
            must_contain=("Handler.smali", "abstract"),
            must_not_contain=("JsonHandler", "XmlHandler"),
            note=(
                "A declaration is not an implementation. An abstract method has no decompiled "
                "body, so the record for it comes from the Smali — and the files that hold the "
                "implementing bodies are the wrong answer to this question."
            ),
        ),
        Task(
            id="wheresource.xml-handler-construction-site.wide",
            category=WHERESOURCE,
            question=("In which method, and in which DEX file, is XmlHandler constructed?"),
            sample=Sample.WIDE,
            probe=probes.callers(XML_INIT),
            source=(
                "examples/wide-app/smali/com/example/wide/HandlerFactory.smali: the create "
                "method holds `invoke-direct {v0}, Lcom/example/wide/XmlHandler;-><init>()V` "
                "in its not-json branch."
            ),
            expect_count=1,
            must_contain=("com.example.wide.HandlerFactory.create", "classes.dex"),
            note="One construction site, located by method and by DEX file.",
        ),
        Task(
            id="wheresource.payload-loader-file.multidex",
            category=WHERESOURCE,
            question=(
                "In which DEX file does the multidex sample keep PayloadLoader — "
                "and where does the decompiler put it?"
            ),
            sample=Sample.MULTIDEX,
            probe=probes.class_provenance("com.example.multidex.PayloadLoader"),
            source=(
                "examples/multidex-app/smali_classes2/com/example/multidex/PayloadLoader.smali "
                "defines the class, and the directory's own name, smali_classes2, is the second "
                "DEX — so the class comes from classes2.dex, and the decompiled class sits at "
                "sources/com/example/multidex/PayloadLoader.java. There is no PayloadLoader "
                "under the first DEX or the first Smali directory."
            ),
            must_contain=("classes2.dex", "PayloadLoader.java"),
            must_not_contain=("classes.dex#com.example.multidex.PayloadLoader",),
            note=(
                "The Smali directory names the DEX; a record that points the class at the "
                "first DEX is the wrong answer."
            ),
        ),
    ]


TASKS = tuple(_tasks())
