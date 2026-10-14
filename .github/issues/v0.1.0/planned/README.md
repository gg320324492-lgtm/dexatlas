# Phase 1 task archive

The eight tasks that planned Phase 1, and the design decisions recorded while
implementing them.

Seven of the eight are complete. Their issue files are kept here rather than on GitHub
as open issues, because reporting finished work as outstanding misrepresents the
project to anyone reading it — including future maintainers. The live Phase 1 tracker is
[`000-phase1-remaining.md`](../000-phase1-remaining.md).

Each file carries the decisions that are not obvious from the code: why a backend runs
as a subprocess rather than being linked, why the manifest parser uses `defusedxml`,
why cross-references are recovered by walking bytecode, and which defects the tests
caught that the implementation got wrong first.

| #    | Task                                                    | Status             |
| ---- | ------------------------------------------------------- | ------------------ |
| 001  | Project structure, CI and developer tooling             | Complete           |
| 002  | APK ingestion and metadata extraction                   | Complete           |
| 003  | JADX decompilation backend                              | Complete           |
| 004  | Apktool and Smali navigation                            | Complete           |
| 005  | Androguard symbol indexing                              | Complete           |
| 006  | Unified analysis API and CLI                            | Complete           |
| 007  | Evidence-based report generation                        | Complete           |
| 008  | Reproducible fixtures, tests and documentation          | Partly — see #000  |

These were also the issues that surfaced the defects worth remembering: a pipeline
that passed an `ApkMetadata` where a `Path` was expected, five unpaired Rich markup tags
that crashed ordinary CLI commands, a coverage gate that silently excluded the code it
was meant to measure, and three wrong assumptions about the Androguard 4.x API.
