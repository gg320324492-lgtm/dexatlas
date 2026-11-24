/**
 * 首页 — 拖拽上传 + 最近项目（§2-1 首屏）。
 * 上传区支持点击选择与 drag&drop，做 APK 类型校验与错误反馈；
 * 最近项目列表带状态徽章与进入详情入口。
 * 上传成功后由 App 路由切换到分析进行中页（受控 mock 流程）。
 */

import { useCallback, useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { Button } from "../components/Button";
import { RECENT_PROJECTS } from "../mockData";
import type { ProjectStatus, ProjectSummary } from "../types";
import "./Home.css";

/** 状态徽章文案与语义色 class */
const STATUS_META: Record<ProjectStatus, { label: string; cls: string }> = {
  idle: { label: "未开始", cls: "da-status--idle" },
  running: { label: "分析中", cls: "da-status--running" },
  done: { label: "已完成", cls: "da-status--done" },
  partial: { label: "部分完成", cls: "da-status--partial" },
  error: { label: "失败", cls: "da-status--error" },
};

function StatusBadge({ status }: { status: ProjectStatus }) {
  const meta = STATUS_META[status];
  return <span className={`da-status-badge ${meta.cls}`}>{meta.label}</span>;
}

function isApkFile(file: File): boolean {
  // 按扩展名校验；真实字节校验（ZIP magic + AndroidManifest）留给后端接入窗口
  return file.name.toLowerCase().endsWith(".apk");
}

export function Home({ onStartAnalysis }: { onStartAnalysis: (apkName: string) => void }) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragDepth = useRef(0);

  const acceptFile = useCallback(
    (file: File | undefined | null) => {
      if (!file) return;
      if (!isApkFile(file)) {
        setError(`不支持的文件类型：${file.name}。请拖入 .apk 安装包。`);
        setSelectedName(null);
        return;
      }
      if (file.size > 2 * 1024 * 1024 * 1024) {
        setError("文件超过 2 GB 上限，桌面原型暂不处理超大型包。");
        setSelectedName(null);
        return;
      }
      setError(null);
      setSelectedName(file.name);
    },
    [],
  );

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      dragDepth.current = 0;
      setDragOver(false);
      acceptFile(event.dataTransfer.files?.[0]);
    },
    [acceptFile],
  );

  const onDragEnter = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepth.current += 1;
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setDragOver(false);
  }, []);

  const onFileInput = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      acceptFile(event.target.files?.[0]);
      // 允许重复选择同一文件
      event.target.value = "";
    },
    [acceptFile],
  );

  const startAnalysis = useCallback(() => {
    if (selectedName) onStartAnalysis(selectedName);
  }, [selectedName, onStartAnalysis]);

  return (
    <div className="da-home">
      <section className="da-home__hero">
        <h1 className="da-home__title">把一个 APK 变成可复核的证据链</h1>
        <p className="da-home__subtitle">拖入安装包，DexAtlas 依次完成采集、解析、索引与证据抽取，每条结论都能跳回来源。</p>
      </section>

      <section
        className={`da-dropzone${dragOver ? " da-dropzone--over" : ""}${selectedName ? " da-dropzone--filled" : ""}`}
        role="button"
        tabIndex={0}
        aria-label="上传 APK：拖拽文件到此处，或点击选择文件"
        aria-invalid={error ? true : undefined}
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        onDragEnter={onDragEnter}
        onDragLeave={onDragLeave}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".apk,application/vnd.android.package-archive"
          className="da-dropzone__input"
          onChange={onFileInput}
          tabIndex={-1}
          aria-hidden="true"
        />
        <div className="da-dropzone__icon" aria-hidden="true">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 16V4" />
            <path d="m7 9 5-5 5 5" />
            <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
          </svg>
        </div>
        {selectedName ? (
          <>
            <p className="da-dropzone__title">已选择：{selectedName}</p>
            <p className="da-dropzone__hint">点击「开始分析」进入分析进行中页面</p>
          </>
        ) : (
          <>
            <p className="da-dropzone__title">拖拽 APK 到此处，或点击选择文件</p>
            <p className="da-dropzone__hint">支持 .apk 安装包，最大 2 GB</p>
          </>
        )}
        {error && (
          <p className="da-dropzone__error" role="alert">
            {error}
          </p>
        )}
      </section>

      <div className="da-home__actions">
        <Button variant="primary" size="lg" disabled={!selectedName} onClick={startAnalysis}>
          开始分析
        </Button>
        {selectedName && (
          <Button variant="ghost" size="lg" onClick={() => { setSelectedName(null); setError(null); }}>
            重新选择
          </Button>
        )}
      </div>

      <section className="da-home__recent" aria-labelledby="recent-heading">
        <div className="da-home__recent-head">
          <h2 id="recent-heading">最近项目</h2>
          <span className="da-home__recent-count">{RECENT_PROJECTS.length} 个项目</span>
        </div>
        <ul className="da-project-list">
          {RECENT_PROJECTS.map((project) => (
            <ProjectRow key={project.id} project={project} />
          ))}
        </ul>
      </section>
    </div>
  );
}

function ProjectRow({ project }: { project: ProjectSummary }) {
  return (
    <li className="da-project-row">
      <div className="da-project-row__main">
        <span className="da-project-row__name">{project.name}</span>
        <span className="da-project-row__pkg">{project.packageName}</span>
      </div>
      <div className="da-project-row__meta">
        <span>{project.sizeLabel}</span>
        <span aria-hidden="true">·</span>
        <span>{project.updatedLabel}</span>
        {typeof project.evidenceCount === "number" && (
          <>
            <span aria-hidden="true">·</span>
            <span>{project.evidenceCount} 条证据</span>
          </>
        )}
      </div>
      <StatusBadge status={project.status} />
      <Button
        variant="secondary"
        size="sm"
        onClick={() => window.alert(`原型阶段：项目 ${project.name} 的详情页入口。`)}
      >
        进入详情
      </Button>
    </li>
  );
}
