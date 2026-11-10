import { useEffect, useState, type JSX } from "react";
import {
  ApiError,
  getHealth,
  getProjectStatus,
  listProjects,
  type Health,
  type ProjectList,
  type ProjectStatus,
  type ProjectSummary,
} from "./api";

// The two screens this workbench serves so far: the workspace's project
// list, and one project's status. Both read the MCP contract's shapes
// unchanged; a screen that needs another tool calls another function.

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
        <a href="#/">← back to the project list</a>
      </p>
    </article>
  );
}

export default function App(): JSX.Element {
  const hash = useHashRoute();
  const statusMatch = hash.match(/^#\/projects\/(.+)$/);
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
        {statusMatch ? (
          <ProjectStatusScreen projectId={decodeURIComponent(statusMatch[1] ?? "")} />
        ) : (
          <ProjectListScreen />
        )}
      </main>
    </div>
  );
}
