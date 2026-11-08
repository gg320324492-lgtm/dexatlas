# The MCP server

DexAtlas can serve its analysis to an agent over the Model Context Protocol.
This document says what the server is, what it will and will not do, and how
to run it.

## What it is

A **tool server** over a DexAtlas workspace. It exposes the analysis a
workspace already holds — the projects, their symbols, the call sites between
their methods, the evidence records, and the places those records were read
from — and nothing else.

It is not an agent. It has no model, no planner, no opinions, and it makes no
decisions about what the caller should look at next. **It runs without any
model provider at all**: a tool server that needed a model would not be a
tool server, and a deployment would be unable to run it without an API key
and a bill.

```bash
uv sync --extra analysis --extra mcp
uv run dexatlas-mcp        # speaks MCP over stdio
```

The workspace comes from the same settings as the rest of DexAtlas, so
`DEXATLAS_WORKSPACE` points it somewhere else.

## The tools

| Tool | What it answers |
|---|---|
| `list_projects` | Which APKs this workspace holds, and how many there are |
| `get_project_status` | One project's status, and **how complete its analysis is** |
| `get_manifest` | The parsed AndroidManifest.xml: package, versions, permissions, components |
| `search_symbols` | The indexed symbols that mention a phrase |
| `get_class_source` | One class's source, with the provenance that says where it came from |
| `get_method_source` | **One exact method** — by descriptor, not by name |
| `find_callers` | The calls into a method, as call sites, with both counts |
| `find_callees` | The calls out of a method |
| `get_evidence` | One evidence record, with the locators it was read from |
| `resolve_locator` | A provenance locator, resolved into the source it names |

Their descriptions are written for the caller: each says what it returns and
what it does not, because the description is the only thing a caller reads
before it decides to call.

## The three things a caller has to know

**A count is only as good as the analysis behind it.** `get_project_status`
says which backends did not take part and whether a limit stopped the
analysis short. A backend that is absent is not a backend that found
nothing, and the difference decides what the numbers mean.

**A name is not a method.** Several methods can share one, and the DEX
descriptor tells them apart. `get_method_source` answers an ambiguous name
with the **candidates** rather than with one of them — so the caller asks
again with a descriptor and is sure of the answer. The body of the wrong
overload reads exactly like the body of the right one, and it travels
straight into whatever quotes it.

**Everything that comes out of an APK is data, not instruction.** The strings
and the decompiled source come from an untrusted file. They are carried in a
field of their own that says so, in every response, and the server's own
descriptions and schemas are checked not to carry the APK's text: an APK that
could write into the description could write into the caller.

That includes the smaller pieces: a permission name from the manifest, and a
symbol's name and the excerpt of the index that comes with it. For a string
symbol the name *is* the string the APK holds, so a caller that reads it as
a name rather than as data is reading the APK's own words.

## What it will not do

- **It never writes.** The tools read the workspace through a read view, and
  the server registers no tool that writes. Every tool carries
  `readOnlyHint` and `destructiveHint`, so a host can allow them without
  reading this document.
- **It never runs a shell.** Nothing in the server starts a process, and
  nothing a caller says reaches a command line.
- **It never reads a file the index did not name.** A path reaches a file
  only by being derived from a class name or a method the analysis found, and
  the derivation refuses a name that could climb out of the tree it belongs
  to.
- **It never returns more than a bounded amount of anything.** Every excerpt
  is cut to a number of lines and a number of bytes, and the cut is stated
  in the response rather than left for the reader to guess.

## Trying it

`examples/mcp_client.py` starts the server as a subprocess over stdio, asks it
what it can do, and asks it for the projects in the workspace:

```bash
uv run --no-sync python examples/mcp_client.py
```

In an MCP host, add it as a stdio server:

```json
{
  "mcpServers": {
    "dexatlas": {
      "command": "uv",
      "args": ["--directory", "/path/to/dexatlas", "run", "dexatlas-mcp"]
    }
  }
}
```

## When it cannot answer

A request the server cannot answer is an error and not an empty result, and
the error says which it is. The code is a short word a caller can branch on:

| Code | What it means |
|---|---|
| `unknown_project` | The workspace holds no project by that name |
| `unknown_method` | The method id is not one this project can answer about |
| `no_manifest` | The project is there, and this analysis holds no manifest |

The last one exists because the two are different. A project whose Apktool
step never ran has no manifest, and saying "unknown project" about it would
send a caller looking for a project that is there. The error names the
backends that did not take part, so the reader knows what would have to
change for the answer to be there.

## Where it goes next

This is the M1 server: read-only, local, and over stdio. Remote access is a
deployment decision rather than a default.

The agent that M2 asked for is built **on top of** these tools rather than
inside them: it calls them, it inherits their read-only nature, and it
checks that every conclusion it reached has something behind it before it
reports it. That is `docs/architecture/agent.md`.
