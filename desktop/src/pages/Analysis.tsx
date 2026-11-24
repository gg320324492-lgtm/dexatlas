/**
 * 分析进行中页 — 左侧阶段进度 + 中间实时日志 + 右侧后端状态（§2-3）。
 * 本窗口用受控 mock 定时推进状态演示完整生命周期；
 * 后续窗口接入真实后端时，替换 useAnalysisSimulation 的数据源即可，页面结构不变。
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/Button";
import { Card, CardBody, CardHeader } from "../components/Card";
import { StatusBadge, type StatusKind } from "../components/StatusBadge";
import { PartialBanner } from "../components/PartialBanner";
import { EmptyState } from "../components/states/EmptyState";
import { INITIAL_BACKENDS, INITIAL_LOGS, STAGES } from "../mockData";
import type { BackendState, BackendStatus, LogLevel, LogEntry, StageState } from "../types";
import "./Analysis.css";

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

/** 日志推进脚本：每一步在指定 tick 追加日志并推进阶段/后端状态。 */
interface TickScript {
  logs: Array<Omit<LogEntry, "id" | "timeLabel">>;
  /** 本 tick 结束时的阶段状态覆盖 */
  stageState?: Partial<Record<string, StageState>>;
  backendState?: Partial<Record<string, BackendState>>;
  /** 阶段推进：当前运行阶段 id */
  activeStage?: string;
}

const TICK_SCRIPT: TickScript[] = [
  {
    logs: [{ level: "info", source: "索引", message: "Androguard：构建类/方法/字段符号索引 …" }],
    activeStage: "index",
    backendState: { Androguard: "running" },
  },
  {
    logs: [{ level: "debug", source: "索引", message: "已索引 38,214 个类、212,048 个方法" }],
    activeStage: "index",
  },
  {
    logs: [{ level: "success", source: "索引", message: "符号索引完成，耗时 4.1s" }],
    stageState: { index: "done" },
    activeStage: "evidence",
    backendState: { Androguard: "done" },
  },
  {
    logs: [
      { level: "info", source: "证据", message: "抽取权限声明：28 项" },
      { level: "warn", source: "证据", message: "发现 2 个导出组件未受权限保护" },
    ],
    activeStage: "evidence",
  },
  {
    logs: [{ level: "success", source: "证据", message: "证据抽取完成：47 条，已关联 locator" }],
    stageState: { evidence: "done" },
    activeStage: "report",
  },
  {
    logs: [{ level: "info", source: "报告", message: "生成 Markdown / JSON 报告 …" }],
    activeStage: "report",
  },
  {
    logs: [{ level: "success", source: "报告", message: "报告已生成：reports/demo-app.md" }],
    stageState: { report: "done" },
  },
];

function nowLabel(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/** 受控 mock：按 tick 推进日志/阶段/后端状态。真实接入时替换为 Tauri 事件订阅。 */
function useAnalysisSimulation(running: boolean) {
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS);
  const [stageStates, setStageStates] = useState<Record<string, StageState>>(() => ({
    collect: "done",
    parse: "done",
    index: "running",
    evidence: "pending",
    report: "pending",
  }));
  const [backends, setBackends] = useState<BackendStatus[]>(INITIAL_BACKENDS);
  const tickRef = useRef(0);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      const tick = TICK_SCRIPT[tickRef.current];
      tickRef.current += 1;
      if (!tick) {
        window.clearInterval(timer);
        return;
      }
      const timeLabel = nowLabel();
      setLogs((prev) => [...prev, ...tick.logs.map((l, i) => ({ ...l, id: prev.length + 1 + i, timeLabel }))]);
      if (tick.activeStage) setStageStates((prev) => ({ ...prev, [tick.activeStage as string]: "running" }));
      if (tick.stageState) {
        const patch = tick.stageState as Record<string, StageState>;
        setStageStates((prev) => ({ ...prev, ...patch }));
      }
      if (tick.backendState) {
        const patch = tick.backendState as Record<string, BackendState>;
        setBackends((prev) =>
          prev.map((b) => {
            const next = patch[b.name];
            return next ? { ...b, state: next } : b;
          }),
        );
      }
    }, 2200);
    return () => window.clearInterval(timer);
  }, [running]);

  const finished = tickRef.current >= TICK_SCRIPT.length;
  return { logs, stageStates, backends, finished };
}

export function Analysis() {
  const { projectId } = useParams();
  const { logs, stageStates, backends, finished } = useAnalysisSimulation(true);
  const logBodyRef = useRef<HTMLDivElement>(null);

  // 新日志到达时滚动到底部
  useEffect(() => {
    const el = logBodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs]);

  const activeStageId = useMemo(() => STAGES.find((s) => stageStates[s.id] === "running")?.id, [stageStates]);

  if (!projectId) {
    return (
      <div className="page">
        <EmptyState
          title="尚未开始分析"
          description="从首页拖入一个 APK 后，这里会显示阶段进度、实时日志与后端状态。"
          actions={
            <Link to="/" className="da-link">
              返回首页上传
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="page analysis">
      <header className="page-header analysis__header">
        <div>
          <h1 className="page-title">分析进行中</h1>
          <p className="page-subtitle">
            项目 <code className="da-code">{projectId}</code>
            {finished ? " · 全部阶段完成" : ` · 当前阶段：${STAGES.find((s) => s.id === activeStageId)?.label ?? "—"}`}
          </p>
        </div>
        <div className="analysis__actions">
          <Button variant="secondary" size="sm">
            暂停
          </Button>
          <Button variant="danger" size="sm" confirm="确认取消本次分析？已生成的中间结果将被丢弃。">
            取消
          </Button>
        </div>
      </header>

      {!finished && (
        <PartialBanner tone="info" message="原型演示：进度由受控 mock 驱动，接入真实后端后由分析进程推送。">
          <Button variant="ghost" size="sm" onClick={() => window.location.reload()}>
            重置演示
          </Button>
        </PartialBanner>
      )}

      <div className="analysis__grid">
        {/* 左：阶段进度 */}
        <Card className="analysis__stages" aria-label="阶段进度">
          <CardHeader title="阶段进度" subtitle="采集 → 解析 → 索引 → 证据 → 报告" />
          <CardBody>
            <ol className="da-stage-list">
              {STAGES.map((stage) => {
                const state = stageStates[stage.id] ?? "pending";
                return (
                  <li key={stage.id} className={`da-stage da-stage--${state}`} aria-current={state === "running" ? "step" : undefined}>
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

        {/* 中：实时日志 */}
        <Card className="analysis__logs" aria-label="实时日志">
          <CardHeader
            title="实时日志"
            subtitle="按时间正序，自动滚动"
            actions={<StatusBadge kind={finished ? "completed" : "running"} label={finished ? "已结束" : "滚动更新"} pulse={!finished} />}
          />
          <CardBody>
            <div className="da-log" ref={logBodyRef} role="log" aria-live="polite" aria-label="分析日志输出" tabIndex={0}>
              {logs.map((log) => (
                <div key={log.id} className={`da-log__line ${LOG_LEVEL_CLASS[log.level]}`}>
                  <span className="da-log__time">{log.timeLabel}</span>
                  <span className="da-log__source">[{log.source}]</span>
                  <span className="da-log__msg">{log.message}</span>
                </div>
              ))}
              {!finished && <div className="da-log__cursor" aria-hidden="true">▌</div>}
            </div>
          </CardBody>
        </Card>

        {/* 右：后端状态 */}
        <Card className="analysis__backends" aria-label="后端状态">
          <CardHeader title="后端状态" subtitle="JADX / Apktool / Androguard" />
          <CardBody>
            <ul className="da-backend-list">
              {backends.map((backend) => (
                <li key={backend.name} className="da-backend">
                  <div className="da-backend__head">
                    <span className="da-backend__name">{backend.name}</span>
                    <StatusBadge kind={BACKEND_BADGE[backend.state]} pulse={backend.state === "running"} />
                  </div>
                  <div className="da-backend__detail">{backend.detail}</div>
                  {typeof backend.progress === "number" && (
                    <div
                      className="da-backend__bar"
                      role="progressbar"
                      aria-valuenow={backend.progress}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${backend.name} 进度`}
                    >
                      <div className="da-backend__bar-fill" style={{ width: `${backend.progress}%` }} />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
