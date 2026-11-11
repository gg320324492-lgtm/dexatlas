import { useEffect, useState, type FormEvent, type JSX } from "react";
import {
  ApiError,
  findCallers,
  findCallees,
  getClassSource,
  getEvidence,
  getHealth,
  getMethodSource,
  getProjectStatus,
  listEvidence,
  listProjects,
  resolveLocator,
  searchSymbols,
  type CalleeView,
  type CallerView,
  type CallSiteView,
  type EvidenceView,
  type Health,
  type LocatorResolution,
  type ProjectList,
  type ProjectStatus,
  type ProjectSummary,
  type SourceView,
  type SymbolList,
  type SymbolView,
} from "./api";

// The screens this workbench serves: the workspace's project list, one
// project's status, its symbols/source/evidence, and the calls into and out
// of one method. Every screen reads the MCP contract's shapes unchanged; a
// screen that needs another tool calls another function.

function useHashRoute(): string {
  const [hash, setHash] = useState(() => window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString();
}

// The MCP tools take a method's id, class name, name and descriptor as four
// separate arguments. The index's search hits carry them in one string, so
// one place in the UI decides how that string is taken apart. A hit that is
// not a class or method has no source to open.
interface SymbolTarget {
  kind: "class" | "method";
  className: string;
  methodName: string;
  descriptor?: string;
}

function sourceTarget(symbol: SymbolView): SymbolTarget | null {
  const name = symbol.name.text;
  if (symbol.kind === "class") return { kind: "class", className: name, methodName: "" };
  if (symbol.kind !== "method") return null;
  const open = name.indexOf("(");
  if (open < 0) return null;
  const classAndName = name.slice(0, open);
  const separator = classAndName.lastIndexOf(".");
  if (separator < 1) return null;
  return {
    kind: "method",
    className: classAndName.slice(0, separator),
    methodName: classAndName.slice(separator + 1),
    descriptor: name.slice(open),
  };
}

function errorText(err: unknown): string {
  return err instanceof ApiError ? `${err.code}: ${err.message}` : String(err);
}

function BackendsWarning({ missing }: { missing: string[] }): JSX.Element | null {
  if (missing.length === 0) return null;
  return (
    <span className="warn" title={`did not take part: ${missing.join(", ")}`}>
      no {missing.join(", no ")}
    </span>
  );
}

function ProjectRow({ project }: { project: ProjectSummary }): JSX.Element {
  return (
    <tr>
      <td>
        <a href={`#/projects/${project.id}`}>{project.apk_name}</a>
        <div className="row-links">
          <a href={`#/projects/${project.id}/search`}>search &amp; evidence</a> ·{" "}
          <a href={`#/projects/${project.id}/calls`}>call graph</a>
        </div>
      </td>
      <td>
        <span className={`status status-${project.status}`}>{project.status}</span>
      </td>
      <td className="num">{formatCount(project.class_count)}</td>
      <td className="num">{formatCount(project.method_count)}</td>
      <td className="num">{formatCount(project.call_site_count)}</td>
      <td className="num">{formatCount(project.call_edge_count)}</td>
      <td className="num">{formatCount(project.evidence_count)}</td>
      <td>{formatWhen(project.created_at)}</td>
      <td>
        <BackendsWarning missing={project.missing_backends} />
        {project.truncated && <span className="warn"> truncated</span>}
      </td>
    </tr>
  );
}

function ProjectListScreen(): JSX.Element {
  const [data, setData] = useState<ProjectList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  if (error) return <p className="error">the list could not be read: {error}</p>;
  if (!data) return <p className="loading">reading the workspace…</p>;
  if (data.projects.length === 0) {
    return (
      <p className="empty">
        this workspace holds no analysed APK yet. Analyse one with
        {" "}
        <code>dexatlas analyze &lt;apk&gt;</code> and it appears here.
      </p>
    );
  }
  return (
    <>
      <table className="projects">
        <thead>
          <tr>
            <th>APK</th>
            <th>status</th>
            <th className="num">classes</th>
            <th className="num">methods</th>
            <th className="num">call sites</th>
            <th className="num">call edges</th>
            <th className="num">evidence</th>
            <th>analysed</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {data.projects.map((project) => (
            <ProjectRow key={project.id} project={project} />
          ))}
        </tbody>
      </table>
      <p className="pager">
        {formatCount(data.total)} project{data.total === 1 ? "" : "s"}
      </p>
    </>
  );
}

function CountsGrid({ project }: { project: ProjectStatus["project"] }): JSX.Element {
  const entries: Array<[string, number]> = [
    ["classes", project.class_count],
    ["methods", project.method_count],
    ["call sites", project.call_site_count],
    ["call edges", project.call_edge_count],
    ["evidence", project.evidence_count],
  ];
  return (
    <div className="counts">
      {entries.map(([label, value]) => (
        <div className="count" key={label}>
          <span className="count-value">{formatCount(value)}</span>
          <span className="count-label">{label}</span>
        </div>
      ))}
    </div>
  );
}

function RunRow({ run }: { run: RunSummaryLike }): JSX.Element {
  return (
    <li>
      <code>{run.id}</code> — {run.status}, completeness: {run.completeness}
      {run.duration_seconds !== null && <span>, {run.duration_seconds.toFixed(1)}s</span>}
    </li>
  );
}

type RunSummaryLike = ProjectStatus["runs"][number];

function ProjectStatusScreen({ projectId }: { projectId: string }): JSX.Element {
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProjectStatus(projectId)
      .then(setStatus)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? `${err.code}: ${err.message}` : String(err));
      });
  }, [projectId]);

  if (error) {
    return (
      <p className="error">
        {error} — <a href="#/">back to the project list</a>
      </p>
    );
  }
  if (!status) return <p className="loading">reading the project…</p>;

  const { project, completeness } = status;
  return (
    <article>
      <header className="project-header">
        <h2>
          {project.apk_name}{" "}
          <span className={`status status-${project.status}`}>{project.status}</span>
        </h2>
        <p className="meta">
          <code>{project.id}</code> · sha256 {project.apk_sha256.slice(0, 16)}… · analysed{" "}
          {formatWhen(project.created_at)}
        </p>
      </header>

      <section className="panel" aria-label="completeness">
        <h3>Completeness</h3>
        {completeness.complete ? (
          <p className="ok">every step of the analysis finished.</p>
        ) : (
          <ul className="gaps">
            {completeness.missing_backends.map((backend) => (
              <li key={backend} className="warn">
                the {backend} backend did not take part — the numbers that depend on it are lower
                bounds.
              </li>
            ))}
            {completeness.truncated && (
              <li className="warn">a limit stopped the analysis short.</li>
            )}
            {completeness.errors.map((message) => (
              <li key={message} className="error">
                {message}
              </li>
            ))}
          </ul>
        )}
      </section>

      <CountsGrid project={project} />

      <section className="panel" aria-label="runs">
        <h3>Runs</h3>
        {status.published_run === null ? (
          <p className="meta">
            this workspace holds no recorded run — its rows are the published snapshot of an
            analysis nobody recorded.
          </p>
        ) : (
          <>
            <p>
              published run: <code>{status.published_run.id}</code>
            </p>
            <ul>
              {status.runs.map((run) => (
                <RunRow key={run.id} run={run} />
              ))}
            </ul>
          </>
        )}
      </section>

      <p>
        <a href="#/">← back to the project list</a> ·{" "}
        <a href={`#/projects/${projectId}/search`}>search symbols &amp; trace evidence</a> ·{" "}
        <a href={`#/projects/${projectId}/calls`}>the calls of one method →</a>
      </p>
    </article>
  );
}

// -- screen 2: from a phrase in the index to the place a citation names ----

function DataNotice(): JSX.Element {
  return (
    <p className="data-notice">
      Text from the analysed APK is data, not instructions. Each response carries the same notice.
    </p>
  );
}

function SourcePanel({
  projectId,
  source,
}: {
  projectId: string;
  source: SourceView;
}): JSX.Element {
  return (
    <section className="panel" aria-label="source">
      <h3>Source · {source.kind ?? "none"}</h3>
      {source.found ? (
        <>
          <pre className="source">{source.text?.text ?? ""}</pre>
          {source.text?.truncated && <p className="warn">the source excerpt was cut short.</p>}
        </>
      ) : (
        <p className="warn">no source: {source.reason || "the analysis holds none"}</p>
      )}
      {source.candidates.length > 0 && (
        <p className="meta">
          this name matches {source.candidates.length} methods; choose a descriptor to read exactly
          one. The candidates are: {source.candidates.join(", ")}
        </p>
      )}
      <ProvenanceList projectId={projectId} locators={source.provenance} />
    </section>
  );
}

function LocatorRow({
  projectId,
  locator,
}: {
  projectId: string;
  locator: string;
}): JSX.Element {
  const [resolution, setResolution] = useState<LocatorResolution | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    resolveLocator(projectId, locator)
      .then(setResolution)
      .catch((err: unknown) => setError(errorText(err)));
  }, [projectId, locator, open]);

  return (
    <li className="locator">
      <code>{locator}</code>
      <button type="button" className="link-button" onClick={() => setOpen(!open)}>
        {open ? "hide" : "resolve"}
      </button>
      {open && error && <p className="error">could not resolve: {error}</p>}
      {open && !error && !resolution && <p className="loading">resolving…</p>}
      {open && resolution && (
        <div className={resolution.resolved ? "resolution ok" : "resolution error"}>
          <p>
            {resolution.resolved ? "resolved" : "not resolved"} — {resolution.reason}
          </p>
          {resolution.text && <pre className="source">{resolution.text.text}</pre>}
          {resolution.resolved && !resolution.text && (
            <p className="meta">this locator names a member of the APK, not a file to show.</p>
          )}
        </div>
      )}
    </li>
  );
}

function ProvenanceList({
  projectId,
  locators,
}: {
  projectId: string;
  locators: string[];
}): JSX.Element {
  if (locators.length === 0) return <p className="meta">this response names no provenance locator.</p>;
  return (
    <div className="provenance">
      <h4>Provenance · resolve a locator</h4>
      <ul className="locators">
        {locators.map((locator) => (
          <LocatorRow key={locator} projectId={projectId} locator={locator} />
        ))}
      </ul>
    </div>
  );
}

function EvidenceRow({
  record,
  selected,
  onSelect,
}: {
  record: EvidenceView;
  selected: boolean;
  onSelect: () => void;
}): JSX.Element {
  return (
    <li>
      <button type="button" className={`evidence-button ${selected ? "selected" : ""}`} onClick={onSelect}>
        <code>{record.id}</code> · {record.kind} · {record.level}
        <span className="evidence-summary">{record.summary}</span>
      </button>
    </li>
  );
}

function SearchEvidenceScreen({ projectId }: { projectId: string }): JSX.Element {
  const [query, setQuery] = useState("Crypto");
  const [submitted, setSubmitted] = useState("Crypto");
  const [symbols, setSymbols] = useState<SymbolList | null>(null);
  const [symbolsError, setSymbolsError] = useState<string | null>(null);

  const [source, setSource] = useState<SourceView | null>(null);
  const [sourceLabel, setSourceLabel] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);

  const [records, setRecords] = useState<EvidenceView[] | null>(null);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [record, setRecord] = useState<EvidenceView | null>(null);
  const [recordError, setRecordError] = useState<string | null>(null);

  useEffect(() => {
    setSymbols(null);
    setSymbolsError(null);
    searchSymbols(projectId, submitted)
      .then(setSymbols)
      .catch((err: unknown) => setSymbolsError(errorText(err)));
  }, [projectId, submitted]);

  useEffect(() => {
    setRecords(null);
    setRecordsError(null);
    listEvidence(projectId)
      .then(setRecords)
      .catch((err: unknown) => setRecordsError(errorText(err)));
  }, [projectId]);

  useEffect(() => {
    if (selectedId === null) {
      setRecord(null);
      return;
    }
    setRecord(null);
    setRecordError(null);
    getEvidence(projectId, selectedId)
      .then(setRecord)
      .catch((err: unknown) => setRecordError(errorText(err)));
  }, [projectId, selectedId]);

  function openSource(symbol: SymbolView): void {
    const target = sourceTarget(symbol);
    if (target === null) return;
    setSource(null);
    setSourceError(null);
    setSourceLabel(symbol.name.text);
    const request =
      target.kind === "class"
        ? getClassSource(projectId, target.className)
        : getMethodSource(projectId, target.className, target.methodName, target.descriptor);
    request
      .then(setSource)
      .catch((err: unknown) => setSourceError(errorText(err)));
  }

  return (
    <article>
      <header className="project-header">
        <h2>Symbol search &amp; evidence</h2>
        <p className="meta">
          project <code>{projectId}</code> · every answer comes from the workspace through the MCP
          tools
        </p>
      </header>

      <DataNotice />

      <section className="panel" aria-label="symbol search">
        <h3>1 · Search the index</h3>
        <form
          className="search-form"
          onSubmit={(event) => {
            event.preventDefault();
            setSubmitted(query);
          }}
        >
          <input
            aria-label="symbol query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="a class, method, field or string"
          />
          <button type="submit">search</button>
        </form>
        {symbolsError && <p className="error">the index could not be read: {symbolsError}</p>}
        {!symbolsError && !symbols && <p className="loading">searching…</p>}
        {symbols && symbols.symbols.length === 0 && (
          <p className="empty">nothing in the index matches “{submitted}”.</p>
        )}
        {symbols && symbols.symbols.length > 0 && (
          <>
            <ul className="symbols">
              {symbols.symbols.map((symbol, index) => {
                const target = sourceTarget(symbol);
                return (
                  <li key={`${symbol.kind}:${symbol.name.text}:${index}`}>
                    <span className="kind">{symbol.kind}</span>{" "}
                    {target ? (
                      <button type="button" className="link-button" onClick={() => openSource(symbol)}>
                        <code>{symbol.name.text}</code>
                      </button>
                    ) : (
                      <code>{symbol.name.text}</code>
                    )}
                    {symbol.detail.text && <span className="detail"> {symbol.detail.text}</span>}
                    {symbol.kind === "method" && (
                      <>
                        {" · "}
                        <a className="row-links" href={callUrl(projectId, symbol.name.text)}>
                          call graph
                        </a>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
            <p className="pager">
              {symbols.symbols.length} shown · {formatCount(symbols.total)} indexed matches
            </p>
          </>
        )}
      </section>

      <section className="panel" aria-label="source view">
        <h3>2 · Read the class or method source</h3>
        {sourceLabel === null && <p className="empty">open a class or method above to read its source.</p>}
        {sourceLabel !== null && (
          <p className="meta">
            <code>{sourceLabel}</code>
          </p>
        )}
        {sourceError && <p className="error">the source could not be read: {sourceError}</p>}
        {!sourceError && sourceLabel !== null && !source && <p className="loading">reading…</p>}
        {source && <SourcePanel projectId={projectId} source={source} />}
      </section>

      <section className="panel" aria-label="evidence records">
        <h3>3 · Evidence records</h3>
        {recordsError && <p className="error">the evidence could not be listed: {recordsError}</p>}
        {!recordsError && !records && <p className="loading">listing evidence…</p>}
        {records && records.length === 0 && <p className="empty">this analysis holds no evidence records.</p>}
        {records && records.length > 0 && (
          <>
            <ul className="evidence-list">
              {records.map((item) => (
                <EvidenceRow
                  key={item.id}
                  record={item}
                  selected={selectedId === item.id}
                  onSelect={() => setSelectedId(item.id)}
                />
              ))}
            </ul>
            {selectedId === null && <p className="empty">open a record to see its provenance.</p>}
            {recordError && <p className="error">the record could not be read: {recordError}</p>}
            {!recordError && selectedId !== null && !record && <p className="loading">reading the record…</p>}
            {record && (
              <div className="record">
                <h4>
                  <code>{record.id}</code> · {record.kind} · {record.level}
                </h4>
                <p>{record.summary}</p>
                <pre className="source">{JSON.stringify(record.detail, null, 2)}</pre>
                <ProvenanceList projectId={projectId} locators={record.provenance} />
              </div>
            )}
          </>
        )}
      </section>

      <p>
        <a href={`#/projects/${projectId}`}>← project status</a> · <a href="#/">project list</a>
      </p>
    </article>
  );
}

// -- the third screen: who calls a method, and what it calls --------------
//
// The screen is built on the two tools that answer that question, one call per
// direction. It starts from a method id, which the index search supplies: a
// method hit's name is the method's canonical id, and that is what the two
// endpoints take. Picking a caller or a callee moves the screen to that method,
// so following a chain is the same two calls over again — a cross-reference
// walk, not a new contract.

/** One method in the graph, as the tool that produced it answered it.
 *
 * `sites` is how many call sites the method contributes, or `null` where the
 * tool does not answer per node — which is what `find_callees` does: its
 * callees are deduplicated, and its two counts are totals. A node that drew a
 * number the tool did not answer would put on the screen a number no query can
 * re-derive. */
interface CallTarget {
  id: string;
  kind: string;
  sites: number | null;
}

function callersOf(sites: CallSiteView[]): CallTarget[] {
  const byId = new Map<string, CallTarget>();
  for (const site of sites) {
    const seen = byId.get(site.caller);
    if (seen) seen.sites = (seen.sites ?? 0) + 1;
    // One caller can call by more than one opcode, so the node shows how many
    // sites it contributes and leaves the opcode to the table of sites below.
    else byId.set(site.caller, { id: site.caller, kind: "", sites: 1 });
  }
  return [...byId.values()];
}

function calleesOf(callees: SymbolView[]): CallTarget[] {
  return callees.map((symbol) => ({ id: symbol.name.text, kind: symbol.detail.text, sites: null }));
}

function callUrl(projectId: string, methodId: string): string {
  return `#/projects/${encodeURIComponent(projectId)}/calls?method=${encodeURIComponent(methodId)}`;
}

function MethodPicker({ projectId }: { projectId: string }): JSX.Element {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SymbolView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function look(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;
    setError(null);
    try {
      const page = await searchSymbols(projectId, query.trim(), 0, 50);
      setHits(page.symbols.filter((symbol) => symbol.kind === "method"));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <section className="panel" aria-label="pick a method">
      <h3>Pick a method</h3>
      <form className="search-form" onSubmit={look}>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="a name in the index, e.g. sign"
          aria-label="method name"
        />
        <button type="submit">search the index</button>
      </form>
      {error && <p className="error">{error}</p>}
      {hits === null ? (
        <p className="meta">
          the search runs over the index, so it finds a method by the text the analysis read. A
          method&apos;s name is its id — <code>com.example.Crypto.sign()V</code> — and that is what
          the callers and the callees are asked for.
        </p>
      ) : hits.length === 0 ? (
        <p className="empty">
          the index holds no method that matches {query.trim() || "that"}. That is what the index
          says, not that the APK has no such method — a backend that did not run indexed less.
        </p>
      ) : (
        <ul className="targets">
          {hits.map((hit) => (
            <li key={hit.name.text}>
              <a href={callUrl(projectId, hit.name.text)}>
                <code>{hit.name.text}</code>
              </a>
              <span className="meta"> {hit.detail.text}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CountPair({ view }: { view: CallerView | CalleeView }): JSX.Element {
  return (
    <span className="meta">
      {formatCount(view.call_site_count)} call site{view.call_site_count === 1 ? "" : "s"} ·{" "}
      {formatCount(view.call_edge_count)} call edge{view.call_edge_count === 1 ? "" : "s"}
      {view.truncated && <span className="warn"> · page cut short, more exist</span>}
    </span>
  );
}

const NODE_WIDTH = 280;
const NODE_HEIGHT = 30;
const ROW_HEIGHT = 48;
// Three columns: the callers, the method asked about, the callees. The gaps
// between them are where the edges are drawn, so they are wide enough to read
// as a direction rather than as a line that could point either way.
const CALLERS_X = 16;
const FOCAL_X = CALLERS_X + NODE_WIDTH + 76;
const CALLEES_X = FOCAL_X + NODE_WIDTH + 76;
const GRAPH_WIDTH = CALLEES_X + NODE_WIDTH + 16;

/** One method in the graph.
 *
 * The nodes are HTML links laid over an SVG that draws only the edges. That
 * split is not decoration: an `<a>` in the SVG namespace is a different
 * element from an `<a>` in HTML, and browsers differ on whether clicking one
 * navigates. A node the reader cannot click is a graph they cannot walk, so
 * the clickable part is the part every browser treats as a link, and the part
 * that has to follow coordinates is the part that draws them. */
function CallNode({
  projectId,
  methodId,
  x,
  y,
  sites,
  kind,
  focal,
}: {
  projectId: string;
  methodId: string;
  x: number;
  y: number;
  sites: number | null;
  kind?: string;
  focal?: boolean;
}): JSX.Element {
  const style = { left: x, top: y, width: NODE_WIDTH, height: NODE_HEIGHT };
  const title = sites === null ? methodId : `${methodId} — ${sites} call site${sites === 1 ? "" : "s"}`;
  /* A number is drawn only where the tool answered it. `find_callers` returns
     the call sites, so a caller's number counts them; `find_callees` returns
     its callees deduplicated and answers no count per callee, so a callee node
     carries the opcode instead — the counts it does answer are the totals
     above the graph. The method in the middle is asked about, not counted. */
  const tail = kind ? (
    <span className="node-kind">{kind}</span>
  ) : sites !== null ? (
    <span className="node-count">{sites}</span>
  ) : null;

  if (focal) {
    return (
      <div className="gnode focal" style={style} title={methodId}>
        <span className="node-label">{shorten(methodId, 36)}</span>
      </div>
    );
  }
  const target = callUrl(projectId, methodId);
  return (
    <a
      className="gnode"
      style={style}
      href={target}
      title={title}
      onClick={(event) => {
        // The `href` is what makes a node a link — right-clickable, copyable,
        // reachable by keyboard, and correct in any browser. The handler moves
        // the hash as well so the walk does not depend on the click being
        // handled as a default-allowed navigation.
        event.preventDefault();
        window.location.hash = target;
      }}
    >
      <span className="node-label">{shorten(methodId, 36)}</span>
      {tail}
    </a>
  );
}

function CallGraph({
  projectId,
  methodId,
  callers,
  callees,
}: {
  projectId: string;
  methodId: string;
  callers: CallTarget[];
  callees: CallTarget[];
}): JSX.Element {
  const rows = Math.max(callers.length, callees.length, 1);
  const height = rows * ROW_HEIGHT + 24;
  const focusY = 12 + (rows * ROW_HEIGHT - NODE_HEIGHT) / 2;
  const focusMid = focusY + NODE_HEIGHT / 2;

  function edge(id: string, side: "in" | "out", y: number): JSX.Element {
    const mid = y + NODE_HEIGHT / 2;
    const from = side === "in" ? CALLERS_X + NODE_WIDTH : FOCAL_X + NODE_WIDTH;
    const to = side === "in" ? FOCAL_X : CALLEES_X;
    // An incoming edge leaves the caller and arrives at the method asked
    // about; an outgoing one leaves that method and arrives at the callee.
    const fromY = side === "in" ? mid : focusMid;
    const toY = side === "in" ? focusMid : mid;
    return (
      <path
        key={`${side}-${id}`}
        className={`edge ${side}`}
        markerEnd={`url(#arrow-${side})`}
        d={`M ${from} ${fromY} C ${from + 34} ${fromY}, ${to - 34} ${toY}, ${to} ${toY}`}
      />
    );
  }

  return (
    <div className="graph-scroll">
      <div className="graph-wrap" style={{ width: GRAPH_WIDTH, height }}>
        <svg
          className="graph-edges"
          viewBox={`0 0 ${GRAPH_WIDTH} ${height}`}
          width={GRAPH_WIDTH}
          height={height}
          aria-hidden="true"
        >
          <defs>
            <marker
              id="arrow-in"
              viewBox="0 0 8 8"
              refX={7}
              refY={4}
              markerWidth={6}
              markerHeight={6}
              orient="auto"
            >
              <path className="arrow in" d="M 0 0 L 8 4 L 0 8 z" />
            </marker>
            <marker
              id="arrow-out"
              viewBox="0 0 8 8"
              refX={7}
              refY={4}
              markerWidth={6}
              markerHeight={6}
              orient="auto"
            >
              <path className="arrow out" d="M 0 0 L 8 4 L 0 8 z" />
            </marker>
          </defs>
          {callers.map((node, index) => edge(node.id, "in", 12 + index * ROW_HEIGHT))}
          {callees.map((node, index) => edge(node.id, "out", 12 + index * ROW_HEIGHT))}
        </svg>
        <p className="sr-only">
          {callers.length} caller{callers.length === 1 ? "" : "s"} and {callees.length} callee
          {callees.length === 1 ? "" : "s"} of {methodId}. The edges carry no meaning a reader needs
          that the lists below do not carry: each one is a call site.
        </p>
        {callers.map((node, index) => (
          <CallNode
            key={`in-${node.id}`}
            projectId={projectId}
            methodId={node.id}
            x={CALLERS_X}
            y={12 + index * ROW_HEIGHT}
            sites={node.sites}
          />
        ))}
        {callees.map((node, index) => (
          <CallNode
            key={`out-${node.id}`}
            projectId={projectId}
            methodId={node.id}
            x={CALLEES_X}
            y={12 + index * ROW_HEIGHT}
            sites={null}
            kind={node.kind}
          />
        ))}
        <CallNode
          projectId={projectId}
          methodId={methodId}
          x={FOCAL_X}
          y={focusY}
          sites={null}
          focal
        />
      </div>
    </div>
  );
}

function shorten(value: string, max: number): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function SiteRow({ site, projectId }: { site: CallSiteView; projectId: string }): JSX.Element {
  return (
    <tr>
      <td>
        <a href={callUrl(projectId, site.caller)}>
          <code>{site.caller}</code>
        </a>
      </td>
      <td>
        <span className="kind">{site.kind}</span>
      </td>
      <td>
        <code>{site.dex_name || "—"}</code>
      </td>
      <td className="num">
        {site.instruction_offset >= 0 ? site.instruction_offset : "—"}
      </td>
      <td className="meta">{shorten(site.provenance[0] ?? "", 64)}</td>
    </tr>
  );
}

function CallScreen({ projectId, methodId }: { projectId: string; methodId: string }): JSX.Element {
  const [callers, setCallers] = useState<CallerView | null>(null);
  const [callees, setCallees] = useState<CalleeView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCallers(null);
    setCallees(null);
    setError(null);
    Promise.all([findCallers(projectId, methodId), findCallees(projectId, methodId)])
      .then(([inbound, outbound]) => {
        setCallers(inbound);
        setCallees(outbound);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [projectId, methodId]);

  if (error) return <p className="error">{error}</p>;
  if (!callers || !callees) return <p className="loading">reading the calls…</p>;

  return (
    <>
      <div className="counts">
        <div className="count">
          <span className="count-value">{formatCount(callers.call_site_count)}</span>
          <span className="count-label">call sites in</span>
        </div>
        <div className="count">
          <span className="count-value">{formatCount(callers.call_edge_count)}</span>
          <span className="count-label">call edges in</span>
        </div>
        <div className="count">
          <span className="count-value">{formatCount(callees.call_site_count)}</span>
          <span className="count-label">call sites out</span>
        </div>
        <div className="count">
          <span className="count-value">{formatCount(callees.call_edge_count)}</span>
          <span className="count-label">call edges out</span>
        </div>
      </div>

      <section className="panel" aria-label="call graph">
        <h3>The shape of one method</h3>
        <CallGraph
          projectId={projectId}
          methodId={methodId}
          callers={callersOf(callers.call_sites)}
          callees={calleesOf(callees.callees)}
        />
        <p className="meta">
          Left is who calls it, right is what it calls, and the middle is the method asked about. A
          node is a method, an edge is a caller, a callee and the way the call is made, and the
          arrow points the way the call goes. A number on a caller is how many call sites it
          contributes; the callees <code>find_callees</code> answers are deduplicated, so a callee
          node shows the opcode instead of a count. Click a node to move the screen there.
        </p>
      </section>

      <section className="panel" aria-label="callers">
        <h3>Callers — one row per place in the bytecode</h3>
        <CountPair view={callers} />
        {callers.call_sites.length === 0 ? (
          <p className="empty">
            no call site into this method was read. That is not the same as nobody calling it: an
            absent call is what the analysis saw, and a backend that did not run reads none.
          </p>
        ) : (
          <table className="sites">
            <thead>
              <tr>
                <th>caller</th>
                <th>opcode</th>
                <th>DEX</th>
                <th className="num">offset</th>
                <th>locator</th>
              </tr>
            </thead>
            <tbody>
              {callers.call_sites.map((site, index) => (
                <SiteRow key={`${site.caller}-${index}`} site={site} projectId={projectId} />
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel" aria-label="callees">
        <h3>Callees — what the method calls</h3>
        <CountPair view={callees} />
        {callees.callees.length === 0 ? (
          <p className="empty">
            no call out of this method was read — no body, a body that calls nothing, or no backend
            that could read bytecode.
          </p>
        ) : (
          <ul className="targets">
            {callees.callees.map((symbol) => (
              <li key={symbol.name.text}>
                <a href={callUrl(projectId, symbol.name.text)}>
                  <code>{symbol.name.text}</code>
                </a>
                <span className="kind">{symbol.detail.text}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

function readMethodParam(query: string | undefined): string | null {
  if (!query) return null;
  return new URLSearchParams(query).get("method");
}

function CallGraphScreen({
  projectId,
  methodId,
}: {
  projectId: string;
  methodId: string | null;
}): JSX.Element {
  return (
    <article>
      <header className="project-header">
        <h2>
          {methodId ? (
            <>
              Calls of <code>{methodId}</code>
            </>
          ) : (
            "Calls"
          )}
        </h2>
        <p className="meta">
          who calls this method, and what it calls — each answer is one call to the tool that
          answers that direction, and each row is a place in the bytecode.
        </p>
      </header>

      <MethodPicker projectId={projectId} />
      {methodId !== null && <CallScreen projectId={projectId} methodId={methodId} />}

      <p>
        <a href={`#/projects/${encodeURIComponent(projectId)}`}>← back to the project</a> ·{" "}
        <a href={`#/projects/${encodeURIComponent(projectId)}/search`}>search &amp; evidence</a> ·{" "}
        <a href="#/">project list</a>
      </p>
    </article>
  );
}

export default function App(): JSX.Element {
  const hash = useHashRoute();
  const callsMatch = hash.match(/^#\/projects\/([^/?#]+)\/calls(?:\?([^#]*))?$/);
  const searchMatch = hash.match(/^#\/projects\/([^/?#]+)\/search$/);
  const statusMatch = hash.match(/^#\/projects\/([^/?#]+)$/);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <div className="workbench">
      <header className="topbar">
        <h1>
          <a href="#/">DexAtlas Workbench</a>
        </h1>
        <span className="meta">
          {health ? `v${health.version} · ${health.workspace}` : "…"}
        </span>
      </header>
      <main>
        {callsMatch ? (
          <CallGraphScreen
            projectId={decodeURIComponent(callsMatch[1] ?? "")}
            methodId={readMethodParam(callsMatch[2])}
          />
        ) : searchMatch ? (
          <SearchEvidenceScreen projectId={decodeURIComponent(searchMatch[1] ?? "")} />
        ) : statusMatch ? (
          <ProjectStatusScreen projectId={decodeURIComponent(statusMatch[1] ?? "")} />
        ) : (
          <ProjectListScreen />
        )}
      </main>
    </div>
  );
}
