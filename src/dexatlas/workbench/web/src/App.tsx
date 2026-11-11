import { useEffect, useState, type JSX } from "react";
import {
  ApiError,
  getClassSource,
  getEvidence,
  getHealth,
  getMethodSource,
  getProjectStatus,
  listEvidence,
  listProjects,
  resolveLocator,
  searchSymbols,
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
// project's status, and its symbols/source/evidence. Every screen reads the
// MCP contract's shapes unchanged; a screen that needs another tool calls
// another function.

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
          <a href={`#/projects/${project.id}/search`}>search &amp; evidence</a>
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
        <a href={`#/projects/${projectId}/search`}>search symbols &amp; trace evidence</a>
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

export default function App(): JSX.Element {
  const hash = useHashRoute();
  const searchMatch = hash.match(/^#\/projects\/([^/]+)\/search$/);
  const statusMatch = hash.match(/^#\/projects\/([^/]+)$/);
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
        {searchMatch ? (
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
