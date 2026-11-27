/**
 * 分析进行中页 — 左侧阶段进度 + 中间状态时间线 + 右侧后端状态（§2-3）。
 *
 * Q2-M2-C 真实后端接线（如实披露，无编造能力）：
 * - 数据源：workbench 后端 GET /api/projects/{id}（每 2s 轮询一次，进了
 *   终态就停）与 GET /api/health。
 * - Q2 批次二 X3：阶段进度优先读取真实 run 数据。在项目状态轮询之外并行轮询
 *   GET /api/projects/{id}/runs（workbench PR #5 起），用最新一轮 run 的
 *   status/completeness/tool_versions/duration_seconds 映射到五阶段视图。
 * - Phase 5 W2：run.stages（后端 pipeline 的阶段事件，runs.py RunStage）
 *   存在时，时间线直接按阶段事件渲染。Phase 5 收尾删除了前端时间模拟：
 *   拿不到后端事实时如实显示拿不到，不再按时间推进五格。
 *
 * 【后端事实 vs 前端映射——两件事，别混成一件】
 * - 后端给的**事实**：阶段事件（GET /api/projects/{id}/runs/{run_id}/stages）、
 *   run 的 status、项目的 status；
 * - 前端做的**映射**：哪一格算「推进到位」（映射规则在 ../stages 的
 *   STAGE_TO_SLOT）。五个格子与后端的五个推进点**一一对应**：inspect →
 *   采集、parse-apktool → 解析、index-androguard → 索引、decompile-jadx →
 *   反编译、publish → 报告。所以格上的状态就是后端报的事实，没有推断。
 * 页面上的角标与注释都按这条线措辞：事件是后端给的，对应关系是前端定的。
 *
 * 阶段映射规则（优先级从高到低）写在 ../stages 里（纯函数、可被
 * desktop/src/stages.test.ts 直接执行）：
 * - 有 stages（后端 pipeline 的阶段事件，runs.py RunStage）→ 按事件推进置
 *   done/running；run 已终止却停在某阶段的格子标 error；completeness =
 *   "partial" 时按 errors 点名的工具在已完成格子上标注"部分"（skipped 态）；
 * - 否则按 run.status 粗粒度映射（旧后端写入的 run 无阶段事件），角标只
 *   标注数据来源（stages / run-status），并说明格子是前端的映射；
 * - 无 run 数据时五格全部"待处理"（状态未知），角标不标来源；runs 请求
 *   失败（404 / 网络）时阶段卡片显示可读错误与重试入口——不画一个看起来
 *   在推进的时间线。
 *
 * 【轮询什么时候停】
 * 三处轮询（项目状态、runs 列表、阶段事件）都走 ../stages 的
 * pollUntilTerminal：终态判据是后端返回的状态字段（project.status /
 * run.status），口径只有一份（../stages 的 isTerminalStatus：completed /
 * failed / cancelled；项目的状态域里没有 cancelled——被取消的分析把项目
 * 留在 failed）。进了终态就清掉定时器：项目跑完之后不该再每两秒问一次后端。
 *
 * - 后端没有实时日志流：中间日志区展示轮询得到的状态变化时间线（时间戳 + 事件），
 *   标题注明"后端未提供实时日志流，以下为状态轮询记录"，保留日志控制台样式。
 * - workbench 提供 GET /api/backends（列出本机已安装/缺失的分析后端），它说明
 *   "装没装"；最近分析轮次的 tool_versions 说明"这次分析记下了哪个版本"。本页的
 *   后端状态区把两份事实合起来判——run 的记录分不开「版本还没探测出来」与「压根
 *   没装」，机器那份名单才分得开（映射在 ../stages 的 deriveBackends）；取消按钮
 *   调用 POST /api/projects/{id}/cancel，对 404/失败如实提示。
 * - API 基址用相对 /api：依赖 vite dev 代理转发到 8618（M2-A 的 vite.config.ts
 *   代理合并后即生效；合并前可用临时代理配置验证）。后端未返回 CORS 头，
 *   浏览器直连绝对地址会被跨域拦截。
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
import type {
  BackendInfo,
  ProjectDetailEnvelope as WsProjectStatus,
  RunInfo,
  RunStageEvent,
  RunsEnvelope,
  WorkbenchHealth as WsHealth,
} from "../api";
import type { BackendState, LogLevel, LogEntry, StageState } from "../types";
import {
  STAGES,
  deriveBackends,
  deriveStageBadge,
  deriveStagesFromRun,
  isTerminalStatus,
  pollUntilTerminal,
} from "../stages";
import "./Analysis.css";

/** 相对基址：由 vite dev 代理（→ http://127.0.0.1:8618）转发，见文件头说明。 */
const API_BASE = "/api";

/** 轮询间隔：pending/running 时每 2s 读一次项目状态。 */
const POLL_INTERVAL_MS = 2000;
/** 404 连续多少次后提示"迟迟未入库"（2s 一次，15 次 ≈ 30s）。 */
const NOT_FOUND_LONG_STREAK = 15;

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
  // 最近一次读到的项目状态：终态判定读它（判据是后端字段，不是时间）。
  const latestStatusRef = useRef<string | null>(null);

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
    latestStatusRef.current = null;

    let stopped = false;
    let busy = false;

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
        // 终态判定交给 pollUntilTerminal：判据是后端返回的 project.status，
        // 与 runs 轮询共用同一份口径（../stages 的 isTerminalStatus）。
        latestStatusRef.current = status;
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
    // 轮询规则在 ../stages 的 pollUntilTerminal：进了终态（completed /
    // failed / cancelled）就清掉定时器，不再空转地问后端。
    const poller = pollUntilTerminal({
      poll,
      isTerminal: () => isTerminalStatus(latestStatusRef.current),
      intervalMs: POLL_INTERVAL_MS,
    });
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
      poller.stop();
    };
  }, [projectId, retryNonce, pushLog]);

  return { project, health, pollError, notFound, notFoundLong, logs, pushLog };
}

/**
 * 并行轮询 runs 列表：与项目状态轮询独立，runs 拉取失败不阻塞状态展示。
 *
 * 【什么时候停】最新一轮 run 进了终态就停：判据是后端返回的 run.status
 * （completed / failed / cancelled，见 ../stages 的 isTerminalStatus），和
 * 项目状态轮询共用同一份口径。跑完了还每两秒问一次后端，问的是一个不会
 * 变的答案——那不是「还在跑」，只是空转。
 */
function useRunsPolling(
  projectId: string | undefined,
  active: boolean,
  retryNonce: number,
): {
  runs: RunInfo[];
  runsError: string | null;
} {
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [runsError, setRunsError] = useState<string | null>(null);
  const observedProjectRef = useRef<string | undefined>(undefined);
  // 最近一次读到的最新一轮 run 的状态：终态判定读它（判据是后端字段）。
  const latestRunStatusRef = useRef<string | null>(null);

  useEffect(() => {
    if (!projectId || !active) return;
    // 换项目时先清掉上一个项目的 run：留着它会让新页面短暂显示旧项目的
    // 阶段事实（甚至把旧项目的阶段事件当成新项目的来源）。
    if (observedProjectRef.current !== projectId) {
      observedProjectRef.current = projectId;
      setRuns([]);
      setRunsError(null);
      latestRunStatusRef.current = null;
    }
    let stopped = false;
    let busy = false;

    const poll = async () => {
      if (busy) return;
      busy = true;
      try {
        const envelope: RunsEnvelope = await dexatlas.getRuns(projectId);
        if (!stopped) {
          setRuns(envelope.runs);
          setRunsError(null);
          // runs[0] 是最新一轮；它进终态，这轮轮询就到此为止。
          latestRunStatusRef.current = envelope.runs[0]?.status ?? null;
        }
      } catch (err) {
        if (!stopped) {
          const msg = err instanceof Error ? err.message : String(err);
          // 404 = 后端（PR #5 之前）无该端点：如实记录一次，不反复刷屏
          setRunsError((prev) => (prev === msg ? prev : msg));
        }
      } finally {
        busy = false;
      }
    };

    const poller = pollUntilTerminal({
      poll,
      isTerminal: () => isTerminalStatus(latestRunStatusRef.current),
      intervalMs: POLL_INTERVAL_MS,
    });
    return () => {
      stopped = true;
      poller.stop();
    };
  }, [projectId, active, retryNonce]);

  return { runs, runsError };
}

/** duration_seconds → 展示字符串 */
function durationLabel(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return null;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m${String(s).padStart(2, "0")}s`;
}

/**
 * 轮询最新 run 的阶段事件（Phase 5 W2 独立端点）。runs 拉取成功且有
 * run id 后开始轮询；端点不可用（404 = 旧后端）时如实记录一次。
 *
 * 【什么时候停】该 run 进了终态就停：判据是 stages 端点返回的 run_status
 * （后端字段），口径与另两处轮询相同（../stages 的 isTerminalStatus）。
 * run 结束之后阶段事件不会再变，继续问只是白问。
 */
function useRunStagesPolling(
  projectId: string | undefined,
  runId: string | null | undefined,
  active: boolean,
): { stages: RunStageEvent[] | null; stagesError: string | null } {
  const [stages, setStages] = useState<RunStageEvent[] | null>(null);
  const [stagesError, setStagesError] = useState<string | null>(null);
  const polledRunRef = useRef<string | null>(null);
  // 最近一次读到的该 run 的状态：终态判定读它（判据是后端字段）。
  const latestRunStatusRef = useRef<string | null>(null);

  useEffect(() => {
    if (!projectId || !runId || !active) {
      // 没有 run（或还没拿到 run）：清掉上一个项目/轮次留下的阶段事件。
      // 否则角标会把旧项目的阶段事件标到当前页上——来源不真实，
      // 比没有来源更糟。
      polledRunRef.current = null;
      setStages(null);
      setStagesError(null);
      return;
    }
    const key = `${projectId}:${runId}`;
    if (polledRunRef.current !== key) {
      polledRunRef.current = key;
      latestRunStatusRef.current = null;
      setStages(null);
      setStagesError(null);
    }
    let stopped = false;
    let busy = false;

    const poll = async () => {
      if (busy) return;
      busy = true;
      try {
        const envelope = await dexatlas.getRunStages(projectId, runId);
        if (!stopped) {
          setStages(envelope.stages);
          setStagesError(null);
          // 端点同时返回这一轮 run 的状态：它进终态，阶段事件就定型了。
          latestRunStatusRef.current = envelope.run_status ?? null;
        }
      } catch (err) {
        if (!stopped) {
          const msg = err instanceof Error ? err.message : String(err);
          setStagesError((prev) => (prev === msg ? prev : msg));
        }
      } finally {
        busy = false;
      }
    };

    const poller = pollUntilTerminal({
      poll,
      isTerminal: () => isTerminalStatus(latestRunStatusRef.current),
      intervalMs: POLL_INTERVAL_MS,
    });
    return () => {
      stopped = true;
      poller.stop();
    };
  }, [projectId, runId, active]);

  return { stages, stagesError };
}

export function Analysis() {
  const { projectId } = useParams();
  const [retryNonce, setRetryNonce] = useState(0);
  const [runsRetryNonce, setRunsRetryNonce] = useState(0);
  const { project, health, pollError, notFound, notFoundLong, logs, pushLog } = useProjectPolling(projectId, retryNonce);
  const status = project?.project.status ?? null;
  const active = status === "pending" || status === "running";
  const { runs, runsError } = useRunsPolling(projectId, Boolean(project), runsRetryNonce);
  // 优先取最新一轮真实 run；runs 为空时回退项目信封里的 runs
  const latestRun = runs[0] ?? project?.runs[0] ?? null;
  const hasRealRun = Boolean(runs.length) || Boolean(project?.runs.length);
  const { stages: runStageEvents, stagesError } = useRunStagesPolling(
    projectId,
    latestRun?.id ?? null,
    Boolean(project),
  );
  const runDerived = useMemo(
    () => deriveStagesFromRun(latestRun, runStageEvents),
    [latestRun, runStageEvents],
  );
  // 没有 run 数据时 deriveStagesFromRun(null, null) 把五格全部置为待处理；
  // 页面如实说明「状态未知」，不按时间推进（模拟路径已删除）。
  const stageStates = runDerived.states;
  const partialLabels = runDerived.partialLabels;
  // 机器那份「装没装」的名单：run 的记录分不开「版本还没探测出来」与「压根
  // 没装」，得靠它。没有它，后端状态卡就只能在这两种说法里挑一个，挑错
  // 就是对用户说假话（实测两头都发生过）。拿不到就 null——卡片退回只看 run
  // 的记录，并在说明里如实写出来。
  const [machineBackends, setMachineBackends] = useState<BackendInfo | null>(null);
  useEffect(() => {
    let alive = true;
    void dexatlas
      .getBackends()
      .then((info) => {
        if (alive) setMachineBackends(info);
      })
      .catch(() => {
        // 后端没提供该端点（或网络不通）：机器那份名单读不到，如实当作没有。
      });
    return () => {
      alive = false;
    };
  }, [projectId]);
  const backends = useMemo(() => deriveBackends(latestRun, machineBackends), [latestRun, machineBackends]);
  const [cancelNotice, setCancelNotice] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const logBodyRef = useRef<HTMLDivElement>(null);

  // 新时间线条目到达时滚动到底部
  useEffect(() => {
    const el = logBodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs]);

  const completed = status === "completed";
  const failed = status === "failed";
  const ended = completed || failed;
  const activeStageLabel = STAGES.find((s) => stageStates[s.id] === "running")?.label;
  const duration = durationLabel(latestRun?.duration_seconds);
  const hasStageFacts = Boolean(runStageEvents?.length);
  // 角标只标注数据来源（阶段事件 / run 状态），并写明哪一部分是后端给的
  // 事实、哪一部分是前端做的映射；没有 run 数据时不标来源，
  // 卡片正文如实说明「状态未知」。
  const stageBadge = hasStageFacts
    ? deriveStageBadge("stages")
    : hasRealRun
      ? deriveStageBadge("run-status", Boolean(runsError || stagesError))
      : null;

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
            {active && activeStageLabel
              ? ` · ${hasStageFacts ? "当前阶段" : "推断阶段"}：${activeStageLabel}`
              : ""}
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
        {project && runsError && hasRealRun ? (
          <PartialBanner
            tone="warning"
            message={`runs 端点不可用，阶段进度改按项目详情里的 run 数据映射：${runsError}`}
          />
        ) : null}
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
          {/* 左：阶段进度（后端阶段事件 → 前端映射；无数据时如实显示未知） */}
          <Card className="analysis__stages" aria-label="阶段进度">
            <CardHeader
              title="阶段进度"
              subtitle="采集 → 解析 → 索引 → 反编译 → 报告"
              actions={
                stageBadge ? (
                  <span className="da-mock-badge" title={stageBadge.title}>
                    {stageBadge.text}
                  </span>
                ) : undefined
              }
            />
            <CardBody>
              {!hasRealRun && runsError ? (
                <ErrorState
                  title="阶段进度无法取得"
                  description={`后端不可用，阶段进度无法取得：${runsError}`}
                  onRetry={() => setRunsRetryNonce((n) => n + 1)}
                />
              ) : (
                <>
                  <ol className="da-stage-list">
                    {STAGES.map((stage) => {
                      const state = stageStates[stage.id] ?? "pending";
                      const partial = partialLabels[stage.id];
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
                            <div className="da-stage__label">
                              {stage.label}
                              {partial ? <span className="da-stage__partial">{partial}</span> : null}
                            </div>
                            <div className="da-stage__desc">{stage.description}</div>
                          </div>
                          <StatusBadge
                            kind={STAGE_BADGE[state]}
                            label={partial ? "部分" : undefined}
                            pulse={state === "running"}
                          />
                        </li>
                      );
                    })}
                  </ol>
                  {!hasRealRun ? (
                    <p className="da-stage-unknown">
                      后端尚未返回任何 run 数据：五个阶段的状态未知，这里不推测进度。
                    </p>
                  ) : null}
                  {hasRealRun && latestRun ? (
                    <div className="da-stage-meta">
                      <span>
                        run <code className="da-code">{latestRun.id.slice(0, 8)}</code> · {latestRun.status}
                        {latestRun.completeness === "partial" ? " · partial" : ""}
                        {duration ? ` · ${duration}` : ""}
                      </span>
                      {Object.keys(latestRun.tool_versions ?? {}).length > 0 ? (
                        <span className="da-stage-meta__tools">
                          {Object.entries(latestRun.tool_versions)
                            .filter(([, v]) => v)
                            .map(([k, v]) => `${k} v${v}`)
                            .join(" · ")}
                        </span>
                      ) : null}
                    </div>
                  ) : null}
                </>
              )}
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

          {/* 右：后端状态（机器的「装没装」+ 最近分析轮次的 tool_versions） */}
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
                两份后端事实分开说：GET /api/backends 回答本机「装没装」
                （{machineBackends ? `本机缺失：${machineBackends.missing.join("、") || "无"}` : "这份名单读不到"}）；
                最近一轮 run 的 tool_versions 回答「这次分析记下了哪个版本」。
                两件事必须合起来看——run 的记录分不开「版本还没探测出来」与「压根没装」，机器那份名单才分得开。
              </p>
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  );
}
