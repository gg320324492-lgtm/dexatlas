"""Tasks about tracing a call back to its callers.

The expectations are read out of the Smali beside each APK: an
``invoke-static`` line naming a method is the fact that the method has a
caller, and a method that no line in any Smali file names has none. The
Smali is the APK's own bytecode, disassembled and committed next to it, so
this is a reading of the sample rather than a reading of the tool.

One thing the tasks are careful about is the difference between a call *site*
and a call *edge*. A method called twice from one place is two sites and one
edge, and an answer that counts the wrong one is a different answer.
"""

from __future__ import annotations

from benchmarks import probes
from benchmarks.model import Category, Sample, Task

XREFS = Category.XREFS

#: The qualified name the index holds for a method: class, name, descriptor.
SIGN = "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
POST = "com.example.demo.NetworkClient.post(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
API_KEY = "com.example.strings.Constants.apiKey()Ljava/lang/String;"
HANDLE = "com.example.wide.Handler.handle(Ljava/lang/String;)Ljava/lang/String;"
JSON_INIT = "com.example.wide.JsonHandler.<init>()V"
XML_INIT = "com.example.wide.XmlHandler.<init>()V"


def _tasks() -> list[Task]:
    return [
        Task(
            id="xrefs.crypto-sign-callers",
            category=XREFS,
            question="Which method calls Crypto.sign?",
            sample=Sample.DEMO,
            probe=probes.callers(SIGN),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali: the onCreate "
                "method holds `invoke-static {v0, v1}, "
                "Lcom/example/demo/Crypto;->sign(Ljava/lang/String;Ljava/lang/String;)"
                "Ljava/lang/String;`."
            ),
            must_contain=("com.example.demo.MainActivity.onCreate", "com.example.demo.Crypto.sign"),
            must_not_contain=("com.example.demo.NetworkClient",),
            note="One caller, and the caller has to be named.",
        ),
        Task(
            id="xrefs.network-post-callers",
            category=XREFS,
            question="Which method calls NetworkClient.post?",
            sample=Sample.DEMO,
            probe=probes.callers(POST),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali: onCreate holds "
                "`invoke-static {v1, v0}, Lcom/example/demo/NetworkClient;->post("
                "Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;`."
            ),
            must_contain=("com.example.demo.MainActivity.onCreate",),
            note="The same caller, for a different target.",
        ),
        Task(
            id="xrefs.constants-apikey-callers",
            category=XREFS,
            question="Which method calls Constants.apiKey?",
            sample=Sample.STRINGS,
            probe=probes.callers(API_KEY),
            source=(
                "examples/strings-app/smali/com/example/strings/Constants.smali: the authHeader "
                "method holds `invoke-virtual {v0}, "
                "Lcom/example/strings/Constants;->apiKey()Ljava/lang/String;`."
            ),
            must_contain=("com.example.strings.Constants.authHeader",),
            must_not_contain=("baseUrl",),
            note="A call inside the class that declares the constant.",
        ),
        Task(
            id="xrefs.handler-handle-callers",
            category=XREFS,
            question="Which method calls the Handler interface's handle method?",
            sample=Sample.WIDE,
            probe=probes.callers(HANDLE),
            source=(
                "examples/wide-app/smali/com/example/wide/HandlerFactory.smali: the dispatch "
                "method holds `invoke-interface {p0, p1}, "
                "Lcom/example/wide/Handler;->handle(Ljava/lang/String;)Ljava/lang/String;`."
            ),
            must_contain=("com.example.wide.HandlerFactory.dispatch",),
            note="The call goes through the interface, not through an implementation.",
        ),
        Task(
            id="xrefs.json-handler-init-callers",
            category=XREFS,
            question="Which method constructs a JsonHandler?",
            sample=Sample.WIDE,
            probe=probes.callers(JSON_INIT),
            source=(
                "examples/wide-app/smali/com/example/wide/HandlerFactory.smali: the create "
                "method holds `invoke-direct {v0}, Lcom/example/wide/JsonHandler;-><init>()V`."
            ),
            must_contain=("com.example.wide.HandlerFactory.create",),
            note="The factory constructs both implementations.",
        ),
        Task(
            id="xrefs.xml-handler-init-callers",
            category=XREFS,
            question="Which method constructs an XmlHandler?",
            sample=Sample.WIDE,
            probe=probes.callers(XML_INIT),
            source=(
                "examples/wide-app/smali/com/example/wide/HandlerFactory.smali: the create "
                "method holds `invoke-direct {v0}, Lcom/example/wide/XmlHandler;-><init>()V`."
            ),
            must_contain=("com.example.wide.HandlerFactory.create",),
            note="The other branch of the same factory.",
        ),
        Task(
            id="xrefs.crypto-sign-call-site-count",
            category=XREFS,
            question="How many places in the demo application call Crypto.sign?",
            sample=Sample.DEMO,
            probe=probes.callers(SIGN),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali holds exactly one "
                "`invoke-static ... Crypto;->sign(...)` instruction."
            ),
            expect_count=1,
            note="A count of call sites, which is not the same as a count of callers.",
        ),
        Task(
            id="xrefs.crypto-sign-invocation-kind",
            category=XREFS,
            question="How does MainActivity call Crypto.sign — statically or on an instance?",
            sample=Sample.DEMO,
            probe=probes.callers(SIGN),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali: the instruction is "
                "`invoke-static`, and Crypto.sign is a static method."
            ),
            must_contain=("(static,",),
            note="The opcode is what tells a static call from a virtual one.",
        ),
        Task(
            id="xrefs.handler-handle-invocation-kind",
            category=XREFS,
            question="How does HandlerFactory call the Handler interface's handle method?",
            sample=Sample.WIDE,
            probe=probes.callers(HANDLE),
            source=(
                "examples/wide-app/smali/com/example/wide/HandlerFactory.smali: the instruction "
                "is `invoke-interface`."
            ),
            must_contain=("(interface,",),
            note="A call through an interface is its own kind of edge.",
        ),
        Task(
            id="xrefs.call-site-carries-its-dex",
            category=XREFS,
            question="Which DEX file holds the call to Crypto.sign?",
            sample=Sample.DEMO,
            probe=probes.callers(SIGN),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali is decoded from "
                "examples/demo-app/demo.apk's classes.dex — the APK holds one DEX file."
            ),
            must_contain=("classes.dex",),
            note="A call site knows which DEX file it is in.",
        ),
    ]


TASKS = _tasks()
