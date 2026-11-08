"""Tasks about telling methods apart, and about code that does not say plainly
what it does.

The first half of this file is about **method identity**. A name is not a
method: ``sign`` can be several methods, and only the DEX descriptor tells
them apart. The five first-party samples do not happen to contain a class with
two same-named methods of different descriptors — the independent DEX reader
in :mod:`benchmarks.dexreader` lists every class and every method of every
sample, and there is no such pair — so these tasks are about the property the
descriptor carries rather than about picking between two overloads: a method's
identity is its name *and* its descriptor, and methods that share a name in
different classes, or in different DEX files, are different methods.

The second half is about **ambiguity in decompiled code**: code that says one
thing in its signature and another in its body, code that has no body at all,
and code whose origin the obfuscator has erased.
"""

from __future__ import annotations

from benchmarks import probes
from benchmarks.model import Category, Configuration, Sample, Task

OVERLOADS = Category.OVERLOADS
AMBIGUITY = Category.AMBIGUITY


def _tasks() -> list[Task]:
    return [
        Task(
            id="overloads.method-identity.crypto-sign",
            category=OVERLOADS,
            question="What is the full identity of Crypto.sign?",
            sample=Sample.DEMO,
            probe=probes.indexed_methods("com.example.demo.Crypto"),
            source=(
                "examples/demo-app/smali/com/example/demo/Crypto.smali: "
                "`.method public static sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;` "
                "— the name and the descriptor together are the method."
            ),
            must_contain=(
                "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)"
                "Ljava/lang/String;",
            ),
            note="A method's identifier is its name and its DEX descriptor.",
        ),
        Task(
            id="overloads.method-identity.apikey",
            category=OVERLOADS,
            question="What is the full identity of Constants.apiKey?",
            sample=Sample.STRINGS,
            probe=probes.indexed_methods("com.example.strings.Constants"),
            source=(
                "examples/strings-app/smali/com/example/strings/Constants.smali: "
                "`.method public static apiKey()Ljava/lang/String;`."
            ),
            must_contain=("com.example.strings.Constants.apiKey()Ljava/lang/String;",),
            note="The same name, a different descriptor, a different method.",
        ),
        Task(
            id="overloads.method-identity.descriptor-distinguishes",
            category=OVERLOADS,
            question="Do Crypto.digestOf and Crypto.obfuscate have the same descriptor?",
            sample=Sample.DEMO,
            probe=probes.indexed_methods("com.example.demo.Crypto"),
            source=(
                "examples/demo-app/smali/com/example/demo/Crypto.smali: digestOf and obfuscate "
                "are both `(Ljava/lang/String;)Ljava/lang/String;`, and sign is "
                "`(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;` — the descriptor "
                "is what separates them."
            ),
            must_contain=(
                "com.example.demo.Crypto.digestOf(Ljava/lang/String;)Ljava/lang/String;",
                "com.example.demo.Crypto.obfuscate(Ljava/lang/String;)Ljava/lang/String;",
                "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)"
                "Ljava/lang/String;",
            ),
            note="Three methods in one class, and the descriptor is what separates them.",
        ),
        Task(
            id="overloads.same-name-two-classes.describe",
            category=OVERLOADS,
            question="The multidex sample has methods called describe — which classes are they in?",
            sample=Sample.MULTIDEX,
            probe=probes.indexed_methods(),
            source=(
                "examples/multidex-app/smali/com/example/multidex/PrimaryHelper.smali and "
                "examples/multidex-app/smali_classes2/com/example/multidex/SecondaryHelper.smali: "
                "each declares `.method public static describe()Ljava/lang/String;`."
            ),
            must_contain=(
                "com.example.multidex.PrimaryHelper.describe()Ljava/lang/String;",
                "com.example.multidex.SecondaryHelper.describe()Ljava/lang/String;",
            ),
            note="Same name, same descriptor, different classes — so different methods.",
        ),
        Task(
            id="overloads.same-name-three-classes.handle",
            category=OVERLOADS,
            question="Which classes declare a method called handle?",
            sample=Sample.WIDE,
            probe=probes.indexed_methods(),
            source=(
                "examples/wide-app/smali/com/example/wide/Handler.smali, JsonHandler.smali and "
                "XmlHandler.smali: each declares "
                "`.method public handle(Ljava/lang/String;)Ljava/lang/String;`."
            ),
            must_contain=(
                "com.example.wide.Handler.handle(Ljava/lang/String;)Ljava/lang/String;",
                "com.example.wide.JsonHandler.handle(Ljava/lang/String;)Ljava/lang/String;",
                "com.example.wide.XmlHandler.handle(Ljava/lang/String;)Ljava/lang/String;",
            ),
            note="An interface and its two implementations share the name.",
        ),
        Task(
            id="overloads.same-name-obfuscated",
            category=OVERLOADS,
            question="Which classes declare a method called b taking a String?",
            sample=Sample.OBFUSCATED,
            probe=probes.indexed_methods(),
            source=(
                "examples/obfuscated-app/smali/a/b/a.smali: "
                "`.method public b(Ljava/lang/String;)Ljava/lang/String;`, and "
                "examples/obfuscated-app/smali/a/a/a.smali declares a method called a taking a "
                "String — the names carry nothing."
            ),
            must_contain=(
                "a.b.a.b(Ljava/lang/String;)Ljava/lang/String;",
                "a.a.a.a(Ljava/lang/String;)Ljava/lang/String;",
            ),
            note="A one-letter name is still only half of a method's identity.",
        ),
        Task(
            id="overloads.method-named-after-its-class",
            category=OVERLOADS,
            question="Does the class a.a.a have a method called a?",
            sample=Sample.OBFUSCATED,
            probe=probes.indexed_methods("a.a.a"),
            source=(
                "examples/obfuscated-app/smali/a/a/a.smali: the class a.a.a declares "
                "`.method public a(Ljava/lang/String;)Ljava/lang/String;` — the method's name "
                "is the class's name."
            ),
            must_contain=("a.a.a.a(Ljava/lang/String;)Ljava/lang/String;",),
            note="A method and a class can share a name without being the same thing.",
        ),
        Task(
            id="ambiguity.declared-type-contradicts-body",
            category=AMBIGUITY,
            question="What does SyncService.onBind return?",
            sample=Sample.DEMO,
            probe=probes.method_source("com.example.demo.SyncService", "onBind"),
            source=(
                "examples/demo-app/smali/com/example/demo/SyncService.smali: the method's "
                "descriptor is `(Landroid/content/Intent;)Landroid/os/IBinder;` and its body "
                'is `const-string v0, "com.example.demo.provider"; return-object v0` — it '
                "returns a string where the signature says a binder."
            ),
            must_contain=("Landroid/os/IBinder;", "com.example.demo.provider"),
            note=(
                "The descriptor and the body disagree. The decompiled Java reads as a method "
                "that cannot compile, and only the two together tell a reader what is there."
            ),
        ),
        Task(
            id="ambiguity.abstract-method-has-no-body",
            category=AMBIGUITY,
            question="Is there decompiled source for the Handler interface's handle method?",
            sample=Sample.WIDE,
            probe=probes.indexed_methods("com.example.wide.Handler"),
            source=(
                "examples/wide-app/smali/com/example/wide/Handler.smali: "
                "`.method public abstract handle(Ljava/lang/String;)Ljava/lang/String;` — "
                "the method has no code item at all."
            ),
            must_contain=(
                "com.example.wide.Handler.handle(Ljava/lang/String;)Ljava/lang/String; "
                "decompiled=False",
            ),
            note="No body, and the analysis says so rather than inventing one.",
        ),
        Task(
            id="ambiguity.obfuscation-erases-the-source-name",
            category=AMBIGUITY,
            question="What was the source file of the class a.a.a called?",
            sample=Sample.OBFUSCATED,
            configuration=Configuration.NO_JADX,
            probe=probes.class_source("a.a.a"),
            source=(
                "examples/obfuscated-app/smali/a/a/a.smali holds no `.source` line, unlike every "
                "other Smali file in the five samples — the obfuscator took the name with it."
            ),
            must_not_contain=(".source",),
            note="The answer is that the name is not there to be found.",
        ),
        Task(
            id="ambiguity.unobfuscated-class-keeps-the-source-name",
            category=AMBIGUITY,
            question="What was the source file of the demo application's Crypto class called?",
            sample=Sample.DEMO,
            configuration=Configuration.NO_JADX,
            probe=probes.class_source("com.example.demo.Crypto"),
            source=(
                "examples/demo-app/smali/com/example/demo/Crypto.smali: the second line is "
                '`.source "Crypto.java"`.'
            ),
            must_contain=('.source "Crypto.java"',),
            note="The same question, in a sample where the answer is still there.",
        ),
    ]


TASKS = _tasks()
