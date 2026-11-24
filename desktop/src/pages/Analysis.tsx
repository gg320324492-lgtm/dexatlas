/**
 * 分析进行中页 — 左侧阶段进度 + 中间状态时间线 + 右侧后端状态（§2-3）。
 *
 * Q2-M2-C 真实后端接线（如实披露，无编造能力）：
 * - 数据源：workbench 后端 GET /api/projects/{id}（pending/running 时每 2s 轮询，
 *   completed/failed 停止）与 GET /api/health。
 * - 后端没有阶段级进度接口：左侧阶段推进由前端按时间模拟（每 2.4s 推进一格，
 *   最多推进到"报告"格），completed/failed 时与真实状态对齐；卡片角标常驻
 *   标注"阶段推进为前端模拟"。
 * - 后端没有实时日志流：中间日志区展示轮询得到的状态变化时间线（时间戳 + 事件），
 *   标题注明"后端未提供实时日志流，以下为状态轮询记录"，保留日志控制台样式。
 * - 8618 是只读 workbench API：没有 /api/backends 与 /api/projects/{id}/cancel
 *   路由。后端状态区以最近分析轮次的 tool_versions 推断各后端参与情况；
 *   取消按钮调用 POST /api/projects/{id}/cancel，对 404/失败如实提示。
 * - API 基址用相对 /api：依赖 vite dev 代理转发到 8618（M2-A 的 vite.config.ts
 *   代理合并后即生效；合并前可用临时代理配置验证）。后端未返回 CORS 头，
 *   浏览器直连绝对地址会被跨域拦截。
 * - M2-A 的统一 client（desktop/src/api/）合并后，本文件的 fetch 封装替换为该层。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/Button";
import { Card, CardBody, CardHeader } from "../components/Card";
import { StatusBadge, type StatusKind } from "../components/StatusBadge";
import { PartialBanner } from "../components/PartialBanner";
import { EmptyState } from "../components/states/EmptyState";
import { ErrorState } from "../components/states/ErrorState";
import { LoadingState } from "../components/states/LoadingState";
import { ApiError, dexatlas } from "../api";
import type { ProjectDetailEnvelope as WsProjectStatus, WorkbenchHealth as WsHealth } from "../api";
import type { BackendState, BackendStatus, LogLevel, LogEntry, StageInfo, StageState } from "../types";
import "./Analysis.css";

/** 相对基址：由 vite dev 代理（→ http://127.0.0.1:8618）转发，见文件头说明。 */
const API_BASE = "/api";

/** 轮询间隔：pending/running 时每 2s 读一次项目状态。 */
const POLL_INTERVAL_MS = 2000;
/** 阶段模拟推进间隔（前端模拟，非后端数据）。 */
const STAGE_TICK_MS = 2400;
/** 404 连续多少次后提示"迟迟未入库"（2s 一次，15 次 ≈ 30s）。 */
const NOT_FOUND_LONG_STREAK = 15;

/** 分析阶段定义（§2-3 左侧阶段进度；原 mockData.STAGES 就地收编） */
const STAGES: StageInfo[] = [
  { id: "collect", label: "采集", description: "读取 APK 结构、manifest 与签名信息" },
  { id: "parse", label: "解析", description: "Apktool 反编译资源与 Smali，JADX 还原 Java 源码" },
  { id: "index", label: "索引", description: "Androguard 建立类/方法/字段符号索引" },
  { id: "evidence", label: "证据", description: "抽取权限、组件、字符串与敏感调用点" },
  { id: "report", label: "报告", description: "汇总为可复核的 Markdown / JSON 报告" },
];

/** 阶段状态 → StatusBadge kind */
const STAGE_BADGE: Record<StageState, StatusKind> = {
  pending: "pending",
  running: "running",
  done: "completed",
  error: "failed",
  skipped: "partial",
};

const LOG_LEVEL_CLASS: Record<LogLevel, string> = {
  info: "da-log__line--info",
  debug: "da-log__line--debug",
  warn: "da-log__line--warn",
  error: "da-log__line--error",
  success: "da-log__line--success",
};

const BACKEND_BADGE: Record<BackendState, StatusKind> = {
  queued: "pending",
  running: "running",
  done: "completed",
  error: "failed",
  skipped: "partial",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "排队中",
  running: "分析中",
  completed: "已完成",
  failed: "失败",
};

/** workbench /api/health 不含后端清单；各后端版本从最近分析轮次的 tool_versions 读取。 */
const BACKEND_KEYS: Array<{ name: string; key: string }> = [
  { name: "JADX", key: "jadx" },
  { name: "Apktool", key: "apktool" },
  { name: "Androguard", key: "androguard" },
];

function nowLabel(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function statusLogLevel(status: string): LogLevel {
  if (status === "completed") return "success";
  if (status === "failed") return "error";
  return "info";
}

interface PollingResult {
  project: WsProjectStatus | null;
  health: WsHealth | null;
  pollError: string | null;
  notFound: boolean;
  notFoundLong: boolean;
  logs: LogEntry[];
  pushLog: (level: LogLevel, source: string, message: string) => void;
}

/** 轮询项目状态，把状态变化写成时间线日志；终态停止，错误去重后如实记录。 */
function useProjectPolling(projectId: string | undefined, retryNonce: number): PollingResult {
  const [project, setProject] = useState<WsProjectStatus | null>(null);
  const [health, setHealth] = useState<WsHealth | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [notFoundLong, setNotFoundLong] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logIdRef = useRef(0);
  const prevStatusRef = useRef<string | null>(null);
  const prevRunCountRef = useRef(0);
  const notFoundStreakRef = useRef(0);
  const lastErrorRef = useRef<string | null>(null);

  const pushLog = useCallback((level: LogLevel, source: string, message: string) => {
    logIdRef.current += 1;
    const entry: LogEntry = { id: logIdRef.current, timeLabel: nowLabel(), level, source, message };
    setLogs((prev) => [...prev.slice(-499), entry]);
  }, []);

  useEffect(() => {
    if (!projectId) return;
    // 项目切换 / 重试时重置观察状态，避免把上一个项目的状态当成变化
    setProject(null);
    setNotFound(false);
    setNotFoundLong(false);
    setPollError(null);
    setLogs([]);
    prevStatusRef.current = null;
    prevRunCountRef.current = 0;
    notFoundStreakRef.current = 0;
    lastErrorRef.current = null;

    let stopped = false;
    let busy = false;
    let timer: number | undefined;
    const stop = () => {
      if (timer !== undefined) {
        window.clearInterval(timer);
        timer = undefined;
      }
    };

    const poll = async () => {
      if (busy || stopped) return;
      busy = true;
      try {
        const data = await dexatlas.getProject(projectId);
        if (stopped) return;
        notFoundStreakRef.current = 0;
        setNotFound(false);
        setNotFoundLong(false);
        setPollError(null);
        lastErrorRef.current = null;

        const status = data.project.status;
        const prev = prevStatusRef.current;
        if (prev === null) {
          pushLog(statusLogLevel(status), "状态", `首次读取：${data.project.apk_name} · 状态 ${status}`);
        } else if (prev !== status) {
          const extra =
            status === "completed" && data.published_run?.duration_seconds != null
              ? `，用时 ${data.published_run.duration_seconds.toFixed(1)}s`
              : "";
          pushLog(statusLogLevel(status), "状态", `状态变化：${prev} → ${status}${extra}`);
        }
        prevStatusRef.current = status;

        if (data.runs.length !== prevRunCountRef.current) {
          const latest = data.runs[0];
          pushLog(
            "info",
            "轮次",
            `检测到 ${data.runs.length} 个分析轮次${latest ? `，最新 ${latest.id}（${latest.status}）` : ""}`,
          );
          prevRunCountRef.current = data.runs.length;
        }

        setProject(data);
        if (status === "completed" || status === "failed") stop();
      } catch (err) {
        if (stopped) return;
        const code = err instanceof ApiError ? err.status : 0;
        const msg = err instanceof Error ? err.message : String(err);
        if (code === 404) {
          // 刚上传的项目要等后台任务把项目行写入 store，短时间内 404 属正常
          notFoundStreakRef.current += 1;
          setNotFound(true);
          if (notFoundStreakRef.current === 1) {
            pushLog("warn", "轮询", "项目尚未入库（404），继续等待后台任务写入…");
          }
          if (notFoundStreakRef.current === NOT_FOUND_LONG_STREAK) {
            setNotFoundLong(true);
            pushLog("warn", "轮询", "项目已约 30 秒未入库，请检查后端日志或重新上传");
          }
        } else {
          setPollError(msg);
          if (lastErrorRef.current !== msg) {
            lastErrorRef.current = msg;
            pushLog("warn", "轮询", `轮询失败：${msg}`);
          }
        }
      } finally {
        busy = false;
      }
    };

    pushLog("info", "轮询", `开始轮询 GET ${API_BASE}/projects/${projectId}（每 ${POLL_INTERVAL_MS / 1000}s）`);
    void poll();
    timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS);
    void dexatlas
      .getHealth()
      .then((h) => {
        if (!stopped) setHealth(h);
      })
      .catch(() => {
        // health 读取失败不阻塞状态轮询，页面如实显示"读取中"
      });

    return () => {
      stopped = true;
      stop();
    };
  }, [projectId, retryNonce, pushLog]);

  return { project, health, pollError, notFound, notFoundLong, logs, pushLog };
}

/**
 * 阶段推进模拟：后端无阶段级进度接口，按时间近似推进（每 STAGE_TICK_MS 一格），
 * 最多推进到最后一格；completed 时全部置完成，failed 时停在当前格标失败。
 * 返回已完成格数（0..STAGES.length）。
 */
function useStageSimulation(status: string | null): number {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    if (status === "completed") {
      setProgress(STAGES.length);
      return;
    }
    if (status === "failed" || status === null) return;
    const timer = window.setInterval(() => {
      setProgress((p) => Math.min(p + 1, STAGES.length - 1));
    }, STAGE_TICK_MS);
    return () => window.clearInterval(timer);
  }, [status]);
  return progress;
}

function deriveStageStates(progress: number, status: string | null): Record<string, StageState> {
  const states: Record<string, StageState> = {};
  STAGES.forEach((stage, i) => {
    if (status === "completed") {
      states[stage.id] = "done";
    } else if (status === "failed") {
      states[stage.id] = i < progress ? "done" : i === progress ? "error" : "pending";
    } else {
      states[stage.id] = i < progress ? "done" : i === progress ? "running" : "pending";
    }
  });
  return states;
}

/** 后端状态：workbench 无 /api/backends，用最近轮次的 tool_versions 如实推断。 */
function deriveBackends(project: WsProjectStatus | null): BackendStatus[] {
  const latest = project?.runs[0];
  const versions = latest?.tool_versions ?? {};
  const hasRun = Boolean(latest);
  return BACKEND_KEYS.map(({ name, key }) => {
    const version = versions[key] ?? null;
    if (!hasRun) {
      return { name, state: "queued" as BackendState, detail: "等待分析轮次数据…" };
    }
    if (version) {
      return { name, state: "done" as BackendState, detail: `v${version} · 参与本次分析` };
    }
    return { name, state: "error" as BackendState, detail: "未安装或未配置，未参与本次分析" };
  });
}

export function Analysis() {
  const { projectId } = useParams();
  const [retryNonce, setRetryNonce] = useState(0);
  const { project, health, pollError, notFound, notFoundLong, logs, pushLog } = useProjectPolling(projectId, retryNonce);
  const status = project?.project.status ?? null;
  const progress = useStageSimulation(status);
  const stageStates = useMemo(() => deriveStageStates(progress, status), [progress, status]);
  const backends = useMemo(() => deriveBackends(project), [project]);
  const [cancelNotice, setCancelNotice] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const logBodyRef = useRef<HTMLDivElement>(null);

  // 新时间线条目到达时滚动到底部
  useEffect(() => {
    const el = logBodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs]);

  const active = status === "pending" || status === "running";
  const completed = status === "completed";
  const failed = status === "failed";
  const ended = completed || failed;
  const activeStageLabel = STAGES.find((s) => stageStates[s.id] === "running")?.label;

  const handleCancel = async () => {
    if (!projectId) return;
    setCancelling(true);
    setCancelNotice(null);
    try {
      await dexatlas.cancelProject(projectId);
      pushLog("info", "取消", "已向后端发送取消请求（202），等待状态确认");
    } catch (err) {
      const code = err instanceof ApiError ? err.status : 0;
      const msg = err instanceof Error ? err.message : String(err);
      const notice =
        code === 404 || code === 405
          ? "取消失败：当前 workbench 后端未提供 /api/projects/{id}/cancel 接口，无法取消。"
          : `取消失败：${msg}`;
      setCancelNotice(notice);
      pushLog("warn", "取消", notice);
    } finally {
      setCancelling(false);
    }
  };

  if (!projectId) {
    return (
      <div className="page">
        <EmptyState
          title="尚未开始分析"
          description="从首页拖入一个 APK 后，这里会显示阶段进度、状态轮询记录与后端状态。"
          actions={
            <Link to="/" className="da-link">
              返回首页上传
            </Link>
          }
        />
      </div>
    );
  }

  const projectLabel = project ? `${project.project.apk_name} · ${projectId}` : projectId;
  // workbench 的 completeness.errors 是字符串数组；兼容历史对象形状，统一转字符串展示
  const errors = (project?.completeness.errors ?? []).map((e) =>
    typeof e === "string" ? e : `${e.tool}${e.code ? ` [${e.code}]` : ""} ${e.message}`,
  );

  return (
    <div className="page analysis">
      <header className="page-header analysis__header">
        <div>
          <h1 className="page-title">分析进行中</h1>
          <p className="page-subtitle">
            项目 <code className="da-code">{projectLabel}</code>
            {status
              ? ` · ${STATUS_LABEL[status] ?? status}`
              : notFound
                ? " · 等待入库"
                : " · 读取中…"}
            {active && activeStageLabel ? ` · 模拟阶段：${activeStageLabel}` : ""}
          </p>
        </div>
        <div className="analysis__actions">
          {completed ? (
            <Link to={`/projects/${projectId}`} className="da-btn da-btn--primary da-btn--sm">
              查看分析结果
            </Link>
          ) : null}
          {active ? (
            <Button
              variant="danger"
              size="sm"
              loading={cancelling}
              confirm="确认取消本次分析？已生成的中间结果将被丢弃。"
              onClick={() => void handleCancel()}
            >
              取消
            </Button>
          ) : null}
        </div>
      </header>

      <div className="analysis__banners">
        {notFoundLong && !project ? (
          <PartialBanner
            tone="warning"
            message="项目迟迟未入库：后端持续返回 404。可能上传失败、后端异常或项目 id 有误；仍在继续轮询。"
          />
        ) : null}
        {pollError && project ? <PartialBanner tone="warning" message={`轮询失败，正在重试：${pollError}`} /> : null}
        {cancelNotice ? (
          <PartialBanner tone="danger" message={cancelNotice} onDismiss={() => setCancelNotice(null)} />
        ) : null}
        {completed && project ? (
          <PartialBanner
            tone="info"
            message={`分析完成：${project.project.class_count} 类 · ${project.project.method_count} 方法 · ${project.project.call_site_count} 调用点 · ${project.project.evidence_count} 条证据。`}
          >
            <Link to={`/projects/${projectId}`} className="da-btn da-btn--primary da-btn--sm">
              打开项目详情
            </Link>
          </PartialBanner>
        ) : null}
        {project && errors.length > 0 && !failed ? (
          <PartialBanner
            tone="warning"
            message="本轮分析存在未完成的步骤，结果不完整："
            details={errors.slice(0, 5).map((e, i) => <span key={i}>{e}</span>)}
          />
        ) : null}
        {failed && project ? (
          <PartialBanner
            tone="danger"
            message="分析失败：本轮未产出可发布的结果。"
            details={errors.slice(0, 5).map((e, i) => <span key={i}>{e}</span>)}
          />
        ) : null}
      </div>

      {failed && project ? (
        <ErrorState
          title="分析失败"
          description="后端在本轮分析中遇到错误，未发布任何结果。可返回首页重新上传该 APK 再试。"
          detail={errors.length > 0 ? errors.join("\n") : undefined}
          actions={
            <Link to="/" className="da-btn da-btn--secondary da-btn--sm">
              返回首页
            </Link>
          }
        />
      ) : !project && notFound ? (
        <LoadingState label="等待项目入库" lines={3} />
      ) : !project && pollError ? (
        <ErrorState
          title="无法连接后端"
          description={`正在尝试访问 ${API_BASE}，失败原因：${pollError}`}
          onRetry={() => setRetryNonce((n) => n + 1)}
        />
      ) : (
        <div className="analysis__grid">
          {/* 左：阶段进度（模拟推进，见角标） */}
          <Card className="analysis__stages" aria-label="阶段进度">
            <CardHeader
              title="阶段进度"
              subtitle="采集 → 解析 → 索引 → 证据 → 报告"
              actions={
                <span className="da-mock-badge" title="后端没有阶段级进度接口，阶段推进由前端按时间模拟，完成/失败时与真实状态对齐">
                  阶段推进为前端模拟
                </span>
              }
            />
            <CardBody>
              <ol className="da-stage-list">
                {STAGES.map((stage) => {
                  const state = stageStates[stage.id] ?? "pending";
                  return (
                    <li
                      key={stage.id}
                      className={`da-stage da-stage--${state}`}
                      aria-current={state === "running" ? "step" : undefined}
                    >
                      <span className="da-stage__dot" aria-hidden="true">
                        {state === "done" ? "✓" : state === "running" ? "◌" : state === "error" ? "✕" : "•"}
                      </span>
                      <div className="da-stage__text">
                        <div className="da-stage__label">{stage.label}</div>
                        <div className="da-stage__desc">{stage.description}</div>
                      </div>
                      <StatusBadge kind={STAGE_BADGE[state]} pulse={state === "running"} />
                    </li>
                  );
                })}
              </ol>
            </CardBody>
          </Card>

          {/* 中：状态时间线（后端无实时日志流，如实标注） */}
          <Card className="analysis__logs" aria-label="状态轮询时间线">
            <CardHeader
              title="实时日志"
              subtitle="后端未提供实时日志流，以下为状态轮询记录"
              actions={
                <StatusBadge
                  kind={ended ? "completed" : "running"}
                  label={ended ? "已结束" : "滚动更新"}
                  pulse={!ended}
                />
              }
            />
            <CardBody>
              <div className="da-log" ref={logBodyRef} role="log" aria-live="polite" aria-label="分析状态轮询记录" tabIndex={0}>
                {logs.length === 0 ? (
                  <div className="da-log__line da-log__line--debug">
                    <span className="da-log__time">{nowLabel()}</span>
                    <span className="da-log__source">[轮询]</span>
                    <span className="da-log__msg">等待第一次轮询返回…</span>
                  </div>
                ) : (
                  logs.map((log) => (
                    <div key={log.id} className={`da-log__line ${LOG_LEVEL_CLASS[log.level]}`}>
                      <span className="da-log__time">{log.timeLabel}</span>
                      <span className="da-log__source">[{log.source}]</span>
                      <span className="da-log__msg">{log.message}</span>
                    </div>
                  ))
                )}
                {!ended && <div className="da-log__cursor" aria-hidden="true">▌</div>}
              </div>
            </CardBody>
          </Card>

          {/* 右：后端状态（版本来自最近分析轮次的 tool_versions） */}
          <Card className="analysis__backends" aria-label="后端状态">
            <CardHeader
              title="后端状态"
              subtitle={health ? `workbench v${health.version} · workspace ${health.workspace}` : "读取 /api/health …"}
            />
            <CardBody>
              <ul className="da-backend-list">
                {backends.map((backend) => (
                  <li key={backend.name} className="da-backend">
                    <div className="da-backend__head">
                      <span className="da-backend__name">{backend.name}</span>
                      <StatusBadge kind={BACKEND_BADGE[backend.state]} pulse={backend.state === "running"} />
                    </div>
                    <div className="da-backend__detail">{backend.detail}</div>
                  </li>
                ))}
              </ul>
              <p className="da-backend__note">
                8618 为只读 workbench API，无 /api/backends 端点；以上由最近分析轮次的 tool_versions 推断。
              </p>
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  );
}
