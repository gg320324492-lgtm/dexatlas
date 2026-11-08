"""Tasks about finding a string or a resource, and where it was declared.

The search index holds the DEX string pool and the symbol names; the resource
index holds the strings the APK's resource table declares. The two are
different things, and the tasks keep them apart: a hard-coded key that lives
in ``strings.xml`` is in neither the pool nor the code.

Every expectation is a literal that can be read out of the sample's own files —
a ``const-string`` line in a Smali file, or a ``<string>`` element in the
checked-in ``res/values/strings.xml``.
"""

from __future__ import annotations

from benchmarks import probes
from benchmarks.model import Category, Sample, Task

STRINGS = Category.STRINGS


def _tasks() -> list[Task]:
    return [
        Task(
            id="strings.api-key.demo",
            category=STRINGS,
            question="Does the demo application contain a live-looking API key?",
            sample=Sample.DEMO,
            probe=probes.search_results("sk_live"),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali: the onCreate "
                'method holds `const-string v1, "sk_live_2f8a91c4e7b3"`.'
            ),
            must_contain=("sk_live_2f8a91c4e7b3",),
            note="The whole constant, not a prefix of it.",
        ),
        Task(
            id="strings.api-key-label.demo",
            category=STRINGS,
            question="Under what name does the demo application use its key?",
            sample=Sample.DEMO,
            probe=probes.search_results("api_key"),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali: the onCreate "
                'method holds `const-string v0, "api_key"`.'
            ),
            must_contain=("api_key",),
            note="The name of the header, which is a string in its own right.",
        ),
        Task(
            id="strings.endpoint.demo",
            category=STRINGS,
            question="Which endpoint does the demo application talk to?",
            sample=Sample.DEMO,
            probe=probes.search_results("https://api.example.com/v1"),
            source=(
                "examples/demo-app/smali/com/example/demo/MainActivity.smali: the constructor "
                'holds `const-string p0, "https://api.example.com/v1"`.'
            ),
            must_contain=("https://api.example.com/v1",),
            note="The URL, whole.",
        ),
        Task(
            id="strings.imei.obfuscated",
            category=STRINGS,
            question="Does the obfuscated sample contain a device identifier?",
            sample=Sample.OBFUSCATED,
            probe=probes.search_results("IMEI"),
            source=(
                "examples/obfuscated-app/smali/a/b/a.smali: the method named a holds "
                '`const-string v0, "IMEI:000000000000000"`.'
            ),
            must_contain=("IMEI:000000000000000",),
            note="A placeholder value, but a string a reader would want to see.",
        ),
        Task(
            id="strings.cipher.obfuscated",
            category=STRINGS,
            question="Which cipher does the obfuscated sample name?",
            sample=Sample.OBFUSCATED,
            probe=probes.search_results("AES/ECB"),
            source=(
                "examples/obfuscated-app/smali/a/b/a.smali: the method named b holds "
                '`const-string v0, "AES/ECB/PKCS5Padding"`.'
            ),
            must_contain=("AES/ECB/PKCS5Padding",),
            note="The full cipher name, mode and padding.",
        ),
        Task(
            id="strings.telemetry-url.obfuscated",
            category=STRINGS,
            question="Which URL does the obfuscated sample collect to?",
            sample=Sample.OBFUSCATED,
            probe=probes.search_results("telemetry.example.net"),
            source=(
                "examples/obfuscated-app/smali/a/a/a.smali: the method named a holds "
                '`const-string v1, "https://telemetry.example.net/collect?d="`.'
            ),
            must_contain=("https://telemetry.example.net/collect?d=",),
            note="The URL, whole, including the query prefix.",
        ),
        Task(
            id="strings.staging-url.strings",
            category=STRINGS,
            question="Does the strings sample name a staging endpoint?",
            sample=Sample.STRINGS,
            probe=probes.search_results("staging.api.example.com"),
            source=(
                "examples/strings-app/smali/com/example/strings/Constants.smali: the stagingUrl "
                'method holds `const-string v0, "https://staging.api.example.com/v2"`.'
            ),
            must_contain=("https://staging.api.example.com/v2",),
            note="Two endpoints in one sample; the answer has to pick the staging one.",
        ),
        Task(
            id="strings.user-agent.strings",
            category=STRINGS,
            question="What user agent does the strings sample report?",
            sample=Sample.STRINGS,
            probe=probes.search_results("ExampleApp/7.1.3"),
            source=(
                "examples/strings-app/smali/com/example/strings/Constants.smali: the userAgent "
                'method holds `const-string v0, "ExampleApp/7.1.3 (Android 14; Pixel 8)"`.'
            ),
            must_contain=("ExampleApp/7.1.3 (Android 14; Pixel 8)",),
            note="A user agent that names the app version and the device.",
        ),
        Task(
            id="resources.app-name.demo",
            category=STRINGS,
            question="What is the demo application's label resource?",
            sample=Sample.DEMO,
            probe=probes.resource_rows(name="app_name"),
            source=(
                "examples/demo-app/res/values/strings.xml: "
                '<string name="app_name">DexAtlas Demo</string>.'
            ),
            must_contain=("app_name", "DexAtlas Demo"),
            note="A resource declaration, read out of the file that declares it.",
        ),
        Task(
            id="resources.count.demo",
            category=STRINGS,
            question="How many resource strings does the demo application declare?",
            sample=Sample.DEMO,
            probe=probes.resource_rows(),
            source=(
                "examples/demo-app/res/values/strings.xml holds exactly one <string> element, "
                "app_name."
            ),
            expect_count=1,
            note="A count, and the resource table is not the DEX string pool.",
        ),
    ]


TASKS = _tasks()
