"""Tasks about what an APK says about itself: the manifest and its components.

Every expectation here is written against the sample's own manifest — the
checked-in ``AndroidManifest.xml`` beside the APK, and the binary manifest
inside the APK, which two independent readers agree on
(:mod:`benchmarks.axmlreader` reads the bytes, and Androguard's reader
agrees with it).

That agreement is worth a note, because it is not a given. The manifest
Apktool decodes carries no ``<uses-sdk>`` element: Apktool moves the SDK
levels into the ``apktool.yml`` it writes, and the values it writes there are
not the ones the APK's bytes say. For four of the five samples they differ —
the APK says 24, 21 and 26 where Apktool's file says 25, 23 and 27. The
expectations below are therefore written against the APK, which is the thing
being analysed; a task that quoted Apktool's file would be quoting a build
setting as if it were a property of the APK.
"""

from __future__ import annotations

from benchmarks import probes
from benchmarks.model import Category, Sample, Task

MANIFEST = Category.MANIFEST
COMPONENTS = Category.COMPONENTS


def _tasks() -> list[Task]:
    return [
        Task(
            id="manifest.package.demo",
            category=MANIFEST,
            question="Which package does the demo application declare?",
            sample=Sample.DEMO,
            probe=probes.manifest_value("package"),
            source=(
                'examples/demo-app/AndroidManifest.xml: <manifest package="com.example.demo">; '
                "the APK's binary manifest carries the same package attribute."
            ),
            must_contain=("com.example.demo",),
            must_not_contain=("com.example.multidex",),
            note="The package name is the first thing a manifest says about itself.",
        ),
        Task(
            id="manifest.version.multidex",
            category=MANIFEST,
            question="Which version does the multidex sample declare?",
            sample=Sample.MULTIDEX,
            probe=probes.manifest_value("version_name"),
            source=(
                "examples/multidex-app/AndroidManifest.xml: "
                'android:versionCode="2" android:versionName="2.0".'
            ),
            must_contain=("2.0",),
            note="The version name, not the version code.",
        ),
        Task(
            id="manifest.version-code.strings",
            category=MANIFEST,
            question="Which version code does the strings sample declare?",
            sample=Sample.STRINGS,
            probe=probes.manifest_value("version_code"),
            source=(
                'examples/strings-app/AndroidManifest.xml: android:versionCode="7"; '
                "examples/strings-app/apktool.yml: versionCode: 7."
            ),
            must_contain=("7",),
            note="The version code and the version name are two different numbers.",
        ),
        Task(
            id="manifest.min-sdk.wide",
            category=MANIFEST,
            question="Which minimum SDK version does the wide sample declare?",
            sample=Sample.WIDE,
            probe=probes.manifest_value("min_sdk"),
            source=(
                "examples/wide-app/AndroidManifest.xml: "
                '<uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />, and '
                "the APK's binary manifest, read with benchmarks/axmlreader.py, carries "
                "minSdkVersion=24."
            ),
            must_contain=("min_sdk=24",),
            must_not_contain=("min_sdk=25",),
            note=(
                "The APK says 24. Apktool's decoded apktool.yml says 25 for this sample, "
                "and the analysis follows the decoded file rather than the bytes."
            ),
        ),
        Task(
            id="manifest.min-sdk.multidex",
            category=MANIFEST,
            question="Which minimum SDK version does the multidex sample declare?",
            sample=Sample.MULTIDEX,
            probe=probes.manifest_value("min_sdk"),
            source=(
                "examples/multidex-app/AndroidManifest.xml: "
                '<uses-sdk android:minSdkVersion="24" ...>, and the APK\'s binary manifest, '
                "read with benchmarks/axmlreader.py, carries minSdkVersion=24."
            ),
            must_contain=("min_sdk=24",),
            must_not_contain=("min_sdk=25",),
            note="The same divergence as the wide sample, in a different APK.",
        ),
        Task(
            id="manifest.min-sdk.obfuscated",
            category=MANIFEST,
            question="Which minimum SDK version does the obfuscated sample declare?",
            sample=Sample.OBFUSCATED,
            probe=probes.manifest_value("min_sdk"),
            source=(
                "examples/obfuscated-app/AndroidManifest.xml: "
                '<uses-sdk android:minSdkVersion="21" android:targetSdkVersion="30" />, '
                "and the APK's binary manifest carries minSdkVersion=21."
            ),
            must_contain=("min_sdk=21",),
            must_not_contain=("min_sdk=23",),
            note="The largest divergence of the five: the APK says 21, the decoded file says 23.",
        ),
        Task(
            id="manifest.min-sdk.demo",
            category=MANIFEST,
            question="Which minimum SDK version does the demo application declare?",
            sample=Sample.DEMO,
            probe=probes.manifest_value("min_sdk"),
            source=(
                "examples/demo-app/AndroidManifest.xml: "
                '<uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />, and '
                "the APK's binary manifest carries minSdkVersion=24."
            ),
            must_contain=("min_sdk=24",),
            note=(
                "The control for the three tasks above: this sample's decoded build file "
                "happens to agree with the APK, so the answer is the same either way."
            ),
        ),
        Task(
            id="manifest.min-sdk.strings",
            category=MANIFEST,
            question="Which minimum SDK version does the strings sample declare?",
            sample=Sample.STRINGS,
            probe=probes.manifest_value("min_sdk"),
            source=(
                "examples/strings-app/AndroidManifest.xml: "
                '<uses-sdk android:minSdkVersion="26" android:targetSdkVersion="34" />, and '
                "the APK's binary manifest carries minSdkVersion=26."
            ),
            must_contain=("min_sdk=26",),
            must_not_contain=("min_sdk=27",),
            note="The fourth of the five samples, and the same divergence again.",
        ),
        Task(
            id="manifest.target-sdk.demo",
            category=MANIFEST,
            question="Which target SDK version does the demo application declare?",
            sample=Sample.DEMO,
            probe=probes.manifest_value("target_sdk"),
            source=('examples/demo-app/AndroidManifest.xml: android:targetSdkVersion="34".'),
            must_contain=("target_sdk=34",),
            note="The target SDK level, which is a different number from the minimum.",
        ),
        Task(
            id="manifest.permission.count-obfuscated",
            category=MANIFEST,
            question="How many permissions does the obfuscated sample declare?",
            sample=Sample.OBFUSCATED,
            probe=probes.manifest_permissions(),
            source=(
                "examples/obfuscated-app/AndroidManifest.xml declares three "
                "<uses-permission> elements: ACCESS_FINE_LOCATION, READ_PHONE_STATE, SEND_SMS."
            ),
            expect_count=3,
            note="A count is checked as a count, not as a substring.",
        ),
        Task(
            id="manifest.permission.name-strings",
            category=MANIFEST,
            question="Which permission does the strings sample declare?",
            sample=Sample.STRINGS,
            probe=probes.manifest_permissions(),
            source=(
                "examples/strings-app/AndroidManifest.xml: "
                '<uses-permission android:name="android.permission.INTERNET" />.'
            ),
            must_contain=("android.permission.INTERNET",),
            must_not_contain=("READ_EXTERNAL_STORAGE", "SEND_SMS"),
            note="Only one permission — the other samples' permissions are not this one's.",
        ),
        Task(
            id="manifest.permission.multidex-has-two",
            category=MANIFEST,
            question="Which permissions does the multidex sample declare?",
            sample=Sample.MULTIDEX,
            probe=probes.manifest_permissions(),
            source=(
                "examples/multidex-app/AndroidManifest.xml declares "
                "android.permission.INTERNET and android.permission.READ_EXTERNAL_STORAGE."
            ),
            must_contain=(
                "android.permission.INTERNET",
                "android.permission.READ_EXTERNAL_STORAGE",
            ),
            note="Two permissions, and the answer has to name both of them.",
        ),
        Task(
            id="components.count.obfuscated",
            category=COMPONENTS,
            question="How many components does the obfuscated sample declare?",
            sample=Sample.OBFUSCATED,
            probe=probes.manifest_components(),
            source=(
                "examples/obfuscated-app/AndroidManifest.xml: an <application> with an "
                "<activity>, a <receiver> and a <service> inside it — four components."
            ),
            expect_count=4,
            note="The application element counts as a component.",
        ),
        Task(
            id="components.count.strings",
            category=COMPONENTS,
            question="How many components does the strings sample declare?",
            sample=Sample.STRINGS,
            probe=probes.manifest_components(),
            source=(
                'examples/strings-app/AndroidManifest.xml: <application android:label="Strings '
                'Sample" /> and nothing else — one component.'
            ),
            expect_count=1,
            note="One: a sample with no activity, no service and no receiver.",
        ),
        Task(
            id="components.exported.demo",
            category=COMPONENTS,
            question="Which components does the demo application export?",
            sample=Sample.DEMO,
            probe=probes.manifest_exported_components(),
            source=(
                "examples/demo-app/AndroidManifest.xml: <activity android:name="
                '"com.example.demo.MainActivity" android:exported="true"> and '
                '<service android:name="com.example.demo.SyncService" android:exported="true" />.'
            ),
            must_contain=("com.example.demo.MainActivity", "com.example.demo.SyncService"),
            must_not_contain=("receiver",),
            note="Two exported components, and the demo declares no receiver at all.",
        ),
        Task(
            id="components.exported.obfuscated",
            category=COMPONENTS,
            question="Which components does the obfuscated sample export?",
            sample=Sample.OBFUSCATED,
            probe=probes.manifest_exported_components(),
            source=(
                "examples/obfuscated-app/AndroidManifest.xml: the activity a.a.a.a and the "
                'receiver a.a.b.a are exported="true"; the service a.b.a is exported="false".'
            ),
            must_contain=("a.a.a.a", "a.a.b.a"),
            must_not_contain=("service a.b.a",),
            note="An exported receiver in an obfuscated app is the finding worth making.",
        ),
        Task(
            id="components.exported.multidex-single",
            category=COMPONENTS,
            question="Which component does the multidex sample export?",
            sample=Sample.MULTIDEX,
            probe=probes.manifest_exported_components(),
            source=(
                "examples/multidex-app/AndroidManifest.xml: the activity PrimaryHelper is "
                'exported="true" and the service SecondaryHelper is exported="false".'
            ),
            must_contain=("com.example.multidex.PrimaryHelper",),
            must_not_contain=("SecondaryHelper",),
            note="Exactly one exported component; the service is not exported.",
        ),
        Task(
            id="components.kind.receiver-obfuscated",
            category=COMPONENTS,
            question="Does the obfuscated sample declare a broadcast receiver?",
            sample=Sample.OBFUSCATED,
            probe=probes.manifest_components(kind="receiver"),
            source=(
                "examples/obfuscated-app/AndroidManifest.xml: "
                '<receiver android:name="a.a.b.a" android:exported="true" />.'
            ),
            must_contain=("a.a.b.a",),
            note="A receiver, named after a package segment — the kind of collision a "
            "name-based lookup gets wrong.",
        ),
    ]


TASKS = _tasks()
