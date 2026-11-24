/**
 * 项目详情页 — 三栏布局：左列证据列表 / 中间源码或调用图主体 / 右侧证据抽屉（§2-4）。
 * 证据抽屉内提供 locator 与 resolve 动作位（跳回来源）。
 * 当前为受控 mock；真实数据接入由后续窗口完成。
 */

import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "../components/Button";
import { Card, CardBody, CardHeader } from "../components/Card";
import { SearchInput } from "../components/SearchInput";
import { Drawer } from "../components/Drawer";
import { PartialBanner } from "../components/PartialBanner";
import { EmptyState } from "../components/states/EmptyState";
import { EVIDENCE_DETAILS, EVIDENCE_ITEMS, SOURCE_LINES } from "../mockData";
import type { DetailViewMode, EvidenceDetail, EvidenceKind } from "../types";
import "./ProjectDetail.css";

const KIND_LABEL: Record<EvidenceKind, string> = {
  symbol: "符号",
  string: "字符串",
  permission: "权限",
  component: "组件",
  sink: "汇聚点",
};

const KIND_CLASS: Record<EvidenceKind, string> = {
  symbol: "da-ev-tag--symbol",
  string: "da-ev-tag--string",
  permission: "da-ev-tag--permission",
  component: "da-ev-tag--component",
  sink: "da-ev-tag--sink",
};

const ORIGIN_LABEL = { jadx: "JADX", apktool: "Apktool", androguard: "Androguard" } as const;

export function ProjectDetail() {
  const { projectId = "demo-app" } = useParams();
  const [keyword, setKeyword] = useState("");
  const [kindFilter, setKindFilter] = useState<EvidenceKind | "all">("all");
  const [viewMode, setViewMode] = useState<DetailViewMode>("source");
  const [selectedId, setSelectedId] = useState<string | null>("ev-3");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const filtered = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return EVIDENCE_ITEMS.filter((item) => {
      const matchKind = kindFilter === "all" || item.kind === kindFilter;
      const matchKw = kw === "" || item.title.toLowerCase().includes(kw) || (item.subtitle ?? "").toLowerCase().includes(kw);
      return matchKind && matchKw;
    });
  }, [keyword, kindFilter]);

  const selected: EvidenceDetail | null = selectedId ? EVIDENCE_DETAILS[selectedId] ?? null : null;

  const openEvidence = (id: string) => {
    setSelectedId(id);
    setDrawerOpen(true);
  };

  return (
    <div className="page detail">
      <header className="page-header detail__header">
        <div>
          <h1 className="page-title">项目详情</h1>
          <p className="page-subtitle">
            <code className="da-code">{projectId}</code> · 47 条证据 · 报告已生成
          </p>
        </div>
        <div className="detail__actions">
          <Button variant="secondary" size="sm" iconEnd={<span aria-hidden="true">↧</span>}>
            导出 Markdown
          </Button>
          <Button variant="primary" size="sm" iconEnd={<span aria-hidden="true">↧</span>}>
            导出 JSON
          </Button>
        </div>
      </header>

      <PartialBanner
        tone="warning"
        message="部分状态：JADX 对 482 个类反编译降级，这些类的证据来自 Smali 视图，locator 指向 .smali 文件。"
      />

      <div className="detail__grid">
        {/* 左列：证据列表 */}
        <Card className="detail__list" aria-label="证据列表">
          <CardHeader
            title="证据"
            subtitle={`${filtered.length} / ${EVIDENCE_ITEMS.length} 条`}
            actions={
              <SearchInput
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onClear={() => setKeyword("")}
                placeholder="搜索类名 / 权限 / 字符串"
                aria-label="搜索证据"
              />
            }
          />
          <CardBody>
            <div className="detail__filters" role="group" aria-label="按证据类型筛选">
              {(["all", "permission", "symbol", "sink", "component", "string"] as const).map((kind) => (
                <button
                  key={kind}
                  type="button"
                  className={`da-filter-chip${kindFilter === kind ? " is-active" : ""}`}
                  onClick={() => setKindFilter(kind)}
                  aria-pressed={kindFilter === kind}
                >
                  {kind === "all" ? "全部" : KIND_LABEL[kind]}
                </button>
              ))}
            </div>

            {filtered.length === 0 ? (
              <EmptyState title="没有匹配的证据" description="换个关键词，或清除筛选条件。" />
            ) : (
              <ul className="da-ev-list">
                {filtered.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={`da-ev-item${selectedId === item.id ? " is-selected" : ""}`}
                      onClick={() => openEvidence(item.id)}
                      aria-expanded={selectedId === item.id && drawerOpen}
                    >
                      <div className="da-ev-item__top">
                        <span className={`da-ev-tag ${KIND_CLASS[item.kind]}`}>{KIND_LABEL[item.kind]}</span>
                        <span className="da-ev-item__origin">{ORIGIN_LABEL[item.origin]}</span>
                      </div>
                      <div className="da-ev-item__title">{item.title}</div>
                      {item.subtitle && <div className="da-ev-item__subtitle">{item.subtitle}</div>}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        {/* 中间：源码 / 调用图主体 */}
        <Card className="detail__main" aria-label="源码预览">
          <CardHeader
            title={viewMode === "source" ? "SmsLeakWorker.java" : "调用图（局部）"}
            subtitle={viewMode === "source" ? "JADX 还原 · 片段 82–96 行" : "以 ev-3 为中心的调用关系"}
            actions={
              <div className="detail__view-toggle" role="tablist" aria-label="主体视图切换">
                <button
                  type="button"
                  role="tab"
                  aria-selected={viewMode === "source"}
                  className={`da-view-btn${viewMode === "source" ? " is-active" : ""}`}
                  onClick={() => setViewMode("source")}
                >
                  源码
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={viewMode === "callgraph"}
                  className={`da-view-btn${viewMode === "callgraph" ? " is-active" : ""}`}
                  onClick={() => setViewMode("callgraph")}
                >
                  调用图
                </button>
              </div>
            }
          />
          <CardBody>
            {viewMode === "source" ? (
              <pre className="da-source" tabIndex={0} aria-label="源码预览片段">
                {SOURCE_LINES.map((line) => (
                  <div key={line.line} className={`da-source__line${line.highlighted ? " is-highlighted" : ""}${selected?.locator.line === line.line ? " is-referenced" : ""}`}>
                    <span className="da-source__num">{line.line}</span>
                    <code>{line.text}</code>
                  </div>
                ))}
              </pre>
            ) : (
              <div className="da-callgraph" aria-label="调用图预览">
                <div className="da-callgraph__node da-callgraph__node--entry">MainActivity.onCreate</div>
                <div className="da-callgraph__edge" aria-hidden="true">↓</div>
                <div className="da-callgraph__node">SmsLeakWorker.schedule(context)</div>
                <div className="da-callgraph__edge" aria-hidden="true">↓</div>
                <div className="da-callgraph__node da-callgraph__node--hot">SmsLeakWorker.collect() ← 证据 ev-3</div>
                <div className="da-callgraph__edge" aria-hidden="true">↓</div>
                <div className="da-callgraph__node">TelephonyManager.getDeviceId()</div>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* 右侧：证据抽屉 */}
      <Drawer
        open={drawerOpen && selected !== null}
        title="证据详情"
        onClose={() => setDrawerOpen(false)}
        width={460}
        footer={
          selected && (
            <div className="da-ev-drawer__footer">
              <span className="da-ev-drawer__locator" title={selected.locator.path}>
                locator：{selected.locator.path}
                {selected.locator.line ? `:${selected.locator.line}` : ""}
              </span>
              <div className="da-ev-drawer__actions">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => window.alert(`原型阶段：跳转定位到 ${selected.locator.path}:${selected.locator.line ?? 1}`)}
                >
                  打开来源
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => window.alert(`原型阶段：在分析工作区内解析 locator ${selected.locator.path}`)}
                >
                  resolve
                </Button>
              </div>
            </div>
          )
        }
      >
        {selected && (
          <div className="da-ev-drawer">
            <div className="da-ev-drawer__tags">
              <span className={`da-ev-tag ${KIND_CLASS[selected.kind]}`}>{KIND_LABEL[selected.kind]}</span>
              <span className="da-ev-tag da-ev-tag--origin">{ORIGIN_LABEL[selected.origin]}</span>
            </div>
            <h3 className="da-ev-drawer__title">{selected.title}</h3>
            {selected.subtitle && <p className="da-ev-drawer__subtitle">{selected.subtitle}</p>}
            <p className="da-ev-drawer__summary">{selected.summary}</p>
            <pre className="da-ev-drawer__snippet" tabIndex={0}>
              <code>{selected.snippet}</code>
            </pre>
            {selected.relatedIds.length > 0 && (
              <div className="da-ev-drawer__related">
                <div className="da-ev-drawer__related-label">关联证据</div>
                <ul>
                  {selected.relatedIds.map((rid) => {
                    const rel = EVIDENCE_DETAILS[rid];
                    if (!rel) return null;
                    return (
                      <li key={rid}>
                        <button type="button" className="da-ev-drawer__related-item" onClick={() => setSelectedId(rid)}>
                          {rel.title}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}
