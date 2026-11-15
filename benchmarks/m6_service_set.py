"""The frozen service-regression set: the 20 task ids M6 drills against.

The list is copied verbatim from the frozen document
``docs/benchmarks/service-regression-set.md`` (baseline commit ``100b191``)
and kept in code so that a run can select exactly these tasks with
``benchmarks/comparison/run.py --task <prefix>``. The document is the
authority: if the two ever disagree, the document wins and this file must be
corrected in the same commit.

Freeze discipline (document §5): the set is chosen before any agent tuning,
may not be trimmed to raise a pass rate, and any change to it must be
versioned in a new commit that says why. This file is a pointer, not a
second definition — it adds no task, drops none, and reorders none.
"""

from __future__ import annotations

SERVICE_REGRESSION_PREFIXES: tuple[str, ...] = (
    # §3.1 permissions / components (5)
    "manifest.package.demo",
    "manifest.permission.name-strings",
    "manifest.permission.count-obfuscated",
    "components.exported.demo",
    "components.exported.obfuscated",
    # §3.2 method identity / source (3)
    "overloads.method-identity.crypto-sign",
    "overloads.method-identity.descriptor-distinguishes",
    "ambiguity.declared-type-contradicts-body",
    # §3.3 call relations (3)
    "xrefs.crypto-sign-callers",
    "xrefs.handler-handle-callers",
    "xrefs.crypto-sign-call-site-count",
    # §3.4 resource provenance (4)
    "strings.api-key.demo",
    "strings.telemetry-url.obfuscated",
    "resources.app-name.demo",
    "wheresource.app-name-resource-file.demo",
    # §3.5 unanswerable / missing backend (4)
    "unanswerable.crypto-digestof-has-no-callers",
    "unanswerable.demo-declares-no-receiver",
    "partial.no-apktool-there-is-no-manifest",
    "partial.no-jadx-the-failure-is-recorded",
    # §3.6 structural addition (1)
    "multidex.dex-file-count",
)

__all__ = ["SERVICE_REGRESSION_PREFIXES"]
