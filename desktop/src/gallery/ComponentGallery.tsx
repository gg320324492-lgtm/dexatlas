/**
 * 组件画廊 — Q2-M1 验收展示页（补充单 §4.1 / §2.3）。
 * 全部组件在同一处定义、同页预览各状态，便于截图验收。
 * 本页只做展示；交互演示的状态都保存在本组件的受控 state 中。
 */

import { useState } from "react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Panel,
  Table,
  StatusBadge,
  Sidebar,
  Breadcrumbs,
  Dialog,
  Drawer,
  Tabs,
  Input,
  SearchInput,
  EmptyState,
  ErrorState,
  LoadingState,
  PartialBanner,
  Timeline,
  SourcePreview,
  DragDropUploader,
  MetricCard,
} from "../components";
import { SAMPLE_CODE, SAMPLE_NAV, SAMPLE_ROWS, SAMPLE_TIMELINE } from "./galleryData";
import "./gallery.css";

const TOKEN_SWATCHES: Array<{ name: string; value: string }> = [
  { name: "--color-navy-800", value: "#16243d" },
  { name: "--color-navy-600", value: "#2c4370" },
  { name: "--color-lavender", value: "#b8a7f5" },
  { name: "--color-lavender-soft", value: "#d8cefc" },
  { name: "--color-apricot", value: "#f7c59f" },
  { name: "--color-apricot-soft", value: "#fbe3cf" },
  { name: "--color-bg", value: "#fbf7f2" },
  { name: "--color-surface", value: "#ffffff" },
  { name: "--color-success", value: "#2e9e6b" },
  { name: "--color-warning", value: "#d98a2b" },
  { name: "--color-danger", value: "#d64550" },
  { name: "--color-info", value: "#4a7fd6" },
];

function Section({ title, desc, children }: { title: string; desc?: string; children: React.ReactNode }) {
  return (
    <section className="gallery__section">
      <h2 className="gallery__section-title">{title}</h2>
      {desc ? <p className="gallery__section-desc">{desc}</p> : null}
      {children}
    </section>
  );
}

function Demo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="gallery__demo">
      <div className="gallery__demo-label">{label}</div>
      {children}
    </div>
  );
}

export function ComponentGallery() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dangerOpen, setDangerOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [galleryUploadMsg, setGalleryUploadMsg] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [name, setName] = useState("");
  const [bannerVisible, setBannerVisible] = useState(true);

  return (
    <div className="page gallery">
      <header className="page-header">
        <h1 className="page-title">组件画廊</h1>
        <p className="page-subtitle">DexAtlas Desktop 组件库总览 — 设计 token 与全部组件的各状态（Q2-M1 验收页）。</p>
      </header>

      <p className="gallery__intro">
        设计 token：暖白底 #fbf7f2 · 深海军蓝 #16243d · 淡紫 #b8a7f5 · 淡橙 #f7c59f · 圆角 16px · 两级阴影 ·
        焦点环 2px 淡紫。所有组件只做展示与受控行为，不直接发起请求。
      </p>

      {/* ---------- 设计 token ---------- */}
      <Section title="设计 token" desc="颜色 token 样卡（完整 token 清单见 src/styles/tokens.css，唯一来源）。">
        <div className="gallery__swatches">
          {TOKEN_SWATCHES.map((s) => (
            <div key={s.name} className="gallery__swatch">
              <div className="gallery__swatch-color" style={{ background: s.value }} />
              <div className="gallery__swatch-name">{s.name}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ---------- Button ---------- */}
      <Section title="Button 按钮" desc="primary 实心 / secondary 描边 / danger 危险 / ghost 弱操作；loading 与 disabled 禁点；confirm 弹确认。">
        <Demo label="variant × 状态">
          <div className="gallery__row">
            <Button variant="primary">主要操作</Button>
            <Button variant="secondary">次要操作</Button>
            <Button variant="danger" confirm="确认删除该项目？">
              危险操作
            </Button>
            <Button variant="ghost">弱操作</Button>
            <Button variant="primary" loading>
              加载中
            </Button>
            <Button variant="primary" disabled>
              禁用
            </Button>
          </div>
        </Demo>
        <Demo label="尺寸">
          <div className="gallery__row">
            <Button variant="primary" size="sm">小按钮</Button>
            <Button variant="primary" size="md">中按钮</Button>
            <Button variant="primary" size="lg">大按钮</Button>
          </div>
        </Demo>
      </Section>

      {/* ---------- Card / Panel / MetricCard ---------- */}
      <Section title="Card · Panel · MetricCard" desc="大圆角卡片语言；Panel 可折叠；MetricCard 展示关键指标。">
        <div className="gallery__split">
          <div className="gallery__stack">
            <Card>
              <CardHeader title="基础卡片" subtitle="CardHeader + CardBody + CardFooter" />
              <CardBody>卡片正文：大圆角 16px、一级阴影、暖白表面。</CardBody>
            </Card>
            <Card accent>
              <CardHeader title="渐变描边卡片" subtitle="accent：淡紫→淡橙描边，用于首屏强调" />
              <CardBody>渐变仅用于首屏与品牌强调（补充单 3-5）。</CardBody>
            </Card>
          </div>
          <div className="gallery__stack">
            <Panel title="可折叠面板" subtitle="点击标题切换" defaultCollapsed={false}>
              面板内容：折叠按钮键盘可达，aria-expanded 表达状态。
            </Panel>
            <Panel title="默认折叠面板" defaultCollapsed>
              这段内容初始不可见。
            </Panel>
            <div className="gallery__metric-grid">
              <MetricCard label="证据条数" value="47" delta="+12%" trend="up" hint="较上次分析" />
              <MetricCard label="类总数" value="38,214" hint="Androguard 索引" />
              <MetricCard label="失败步骤" value="1" delta="-1" trend="down" hint="JADX 超时" />
            </div>
          </div>
        </div>
      </Section>

      {/* ---------- StatusBadge ---------- */}
      <Section title="StatusBadge 状态徽章" desc="五态：completed / running / failed / partial / pending；running 可带呼吸动画。">
        <Demo label="五种状态">
          <div className="gallery__row">
            <StatusBadge kind="completed" />
            <StatusBadge kind="running" pulse />
            <StatusBadge kind="failed" />
            <StatusBadge kind="partial" />
            <StatusBadge kind="pending" />
          </div>
        </Demo>
        <Demo label="自定义文案">
          <div className="gallery__row">
            <StatusBadge kind="completed" label="JADX 完成" />
            <StatusBadge kind="failed" label="Apktool 超时" />
            <StatusBadge kind="partial" label="仅 Manifest 视图" />
          </div>
        </Demo>
      </Section>

      {/* ---------- Table ---------- */}
      <Section title="Table 数据表" desc="客户端排序、可点击行、紧凑密度、空数据替换展示。">
        <Table
          caption="证据示例"
          columns={[
            { key: "name", header: "名称", sortValue: (r) => r.name },
            { key: "kind", header: "种类", sortValue: (r) => r.kind },
            { key: "origin", header: "来源", sortValue: (r) => r.origin },
            { key: "status", header: "状态", render: (r) => <StatusBadge kind={r.status} /> },
          ]}
          rows={SAMPLE_ROWS}
          rowKey={(r) => r.id}
          density="default"
        />
        <div style={{ height: "var(--space-3)" }} />
        <Table
          caption="紧凑密度"
          density="compact"
          columns={[
            { key: "name", header: "名称" },
            { key: "origin", header: "来源" },
          ]}
          rows={SAMPLE_ROWS.slice(0, 3)}
          rowKey={(r) => r.id}
        />
        <div style={{ height: "var(--space-3)" }} />
        <Table
          columns={[{ key: "name", header: "名称" }]}
          rows={SAMPLE_ROWS.slice(0, 0)}
          rowKey={(r) => r.id}
          empty={<EmptyState title="没有证据" description="该分析尚未产生任何证据条目。" />}
        />
      </Section>

      {/* ---------- Sidebar / Breadcrumbs ---------- */}
      <Section title="Sidebar 侧栏 · Breadcrumbs 面包屑" desc="主导航五项；侧栏支持受控折叠；面包屑末项为当前页。">
        <div className="gallery__sidebar-demo">
          <Sidebar items={SAMPLE_NAV} activeKey="analysis" collapsed={sidebarCollapsed} onCollapsedChange={setSidebarCollapsed} />
          <div className="gallery__stack" style={{ flex: 1 }}>
            <Breadcrumbs
              items={[
                { key: "projects", label: "项目", onClick: () => {} },
                { key: "demo", label: "com.example.demo", onClick: () => {} },
                { key: "evidence", label: "证据详情" },
              ]}
            />
            <Demo label="说明">
              左侧为 Sidebar（当前折叠：{sidebarCollapsed ? "是" : "否"}），右上有 Breadcrumbs。
              侧栏激活项使用 navy-600 底 + 淡紫内嵌指示条。
            </Demo>
          </div>
        </div>
      </Section>

      {/* ---------- Dialog / Drawer ---------- */}
      <Section title="Dialog 对话框 · Drawer 抽屉" desc="Escape 关闭、遮罩点击关闭、焦点陷阱、关闭后焦点返回触发元素。">
        <div className="gallery__row">
          <Button variant="primary" onClick={() => setDialogOpen(true)}>
            打开对话框
          </Button>
          <Button variant="secondary" onClick={() => setDangerOpen(true)}>
            危险确认弹窗
          </Button>
          <Button variant="secondary" onClick={() => setDrawerOpen(true)}>
            打开抽屉
          </Button>
        </div>
        <Dialog
          open={dialogOpen}
          title="导出报告"
          description="将生成 Markdown 与 JSON 两种格式的分析报告。"
          confirmLabel="导出"
          onClose={() => setDialogOpen(false)}
          onConfirm={() => setDialogOpen(false)}
        >
          <Input label="报告标题" value={name} onChange={(e) => setName(e.target.value)} placeholder="demo-app 分析报告" hint="将写入报告文件名" />
        </Dialog>
        <Dialog
          open={dangerOpen}
          title="删除项目"
          description="将删除该项目全部分析记录与报告，操作不可恢复。"
          danger
          confirmLabel="确认删除"
          onClose={() => setDangerOpen(false)}
          onConfirm={() => setDangerOpen(false)}
        >
          项目：com.example.demo
        </Dialog>
        <Drawer open={drawerOpen} title="证据：getDeviceId" onClose={() => setDrawerOpen(false)}>
          <div className="gallery__stack">
            <StatusBadge kind="completed" label="JADX · 已复核" />
            <p style={{ margin: 0, color: "var(--color-text-secondary)" }}>
              locator：<code>sources/com/example/demo/SmsLeakWorker.java:88</code>
            </p>
            <SourcePreview language="java" path="SmsLeakWorker.java" code={SAMPLE_CODE} highlightLines={[7]} maxLines={20} />
          </div>
        </Drawer>
      </Section>

      {/* ---------- Tabs / Input / SearchInput ---------- */}
      <Section title="Tabs 页签 · Input 输入框 · SearchInput 搜索框" desc="Tabs 支持左右方向键切换；Input 带 label/hint/error 关联；SearchInput 可清除。">
        <Tabs
          items={[
            { key: "source", label: "源码" },
            { key: "callgraph", label: "调用图", badge: "12" },
            { key: "perms", label: "权限", disabled: true },
          ]}
        >
          {(key) => (
            <div className="gallery__demo">
              当前页签：<strong>{key}</strong>（方向键 ←/→ 可切换，roving tabindex）
            </div>
          )}
        </Tabs>
        <div style={{ height: "var(--space-4)" }} />
        <div className="gallery__split">
          <div className="gallery__stack">
            <Input label="项目名称" placeholder="例如 demo-app" value={name} onChange={(e) => setName(e.target.value)} hint="仅用于展示命名" />
            <Input label="后端路径" defaultValue="/usr/local/bin/jadx" prefix="PATH" />
            <Input label="APK 路径" defaultValue="G:\bad\path" error="路径不存在，请检查盘符" />
          </div>
          <div className="gallery__stack">
            <SearchInput placeholder="搜索证据、类名、权限…" value={search} onChange={(e) => setSearch(e.target.value)} onClear={() => setSearch("")} />
            <SearchInput placeholder="禁用态" disabled value="" />
            <Demo label="受控值">{search === "" ? "（空）" : search}</Demo>
          </div>
        </div>
      </Section>

      {/* ---------- 状态组件：loading/empty/error/partial ---------- */}
      <Section title="状态组件" desc="LoadingState（骨架屏）/ EmptyState / ErrorState / PartialBanner，四态覆盖（补充单 4-4）。">
        <div className="gallery__split">
          <div className="gallery__stack">
            <Demo label="LoadingState · 行骨架">
              <LoadingState lines={3} />
            </Demo>
            <Demo label="LoadingState · 卡片骨架">
              <LoadingState variant="card" />
            </Demo>
            <Demo label="EmptyState">
              <EmptyState title="暂无分析项目" description="从首页拖入 APK 开始第一次分析。" />
            </Demo>
          </div>
          <div className="gallery__stack">
            <Demo label="ErrorState">
              <ErrorState
                title="JADX 反编译失败"
                description="后端进程退出码 1，已降级为仅 Manifest 视图。"
                detail={"Exit code 1\njava.lang.OutOfMemoryError: Java heap space\n\tat jadx.core.dex.nodes.ClassNode.load(ClassNode.java:121)"}
                onRetry={() => {}}
              />
            </Demo>
            {bannerVisible ? (
              <PartialBanner
                tone="warning"
                message="部分后端未完成：报告基于 2/3 个后端的输出。"
                details={["JADX：进程超时（120s）", "Apktool：正常", "Androguard：正常"]}
                onRetry={() => {}}
                onDismiss={() => setBannerVisible(false)}
              />
            ) : (
              <Button variant="secondary" size="sm" onClick={() => setBannerVisible(true)}>
                恢复 PartialBanner
              </Button>
            )}
            <PartialBanner tone="info" message="原型演示：进度由受控 mock 驱动。" />
          </div>
        </div>
      </Section>

      {/* ---------- Timeline ---------- */}
      <Section title="Timeline 阶段时间线" desc="分析流水线阶段进度；running 带呼吸动画。">
        <div className="gallery__timeline-box">
          <Timeline items={SAMPLE_TIMELINE} />
        </div>
      </Section>

      {/* ---------- SourcePreview ---------- */}
      <Section title="SourcePreview 源码预览" desc="行号 + 目标行高亮（证据回跳来源的展示端）；长文件可展开。">
        <div className="gallery__code-box">
          <SourcePreview
            language="java"
            path="sources/com/example/demo/SmsLeakWorker.java"
            code={SAMPLE_CODE}
            highlightLines={[7]}
            startLine={82}
          />
        </div>
      </Section>

      {/* ---------- DragDropUploader ---------- */}
      <Section title="DragDropUploader 拖拽上传" desc="扩展名与大小前端校验；拖入高亮；键盘可达（Enter/空格打开文件选择）；校验失败行内提示，不弹原生 alert。">
        <DragDropUploader
          accept={[".apk"]}
          maxSizeMB={512}
          title="拖入 APK 文件"
          description="支持 .apk，单个文件不超过 512 MB"
          onFileSelected={(file) => setGalleryUploadMsg(`已选择：${file.name}`)}
          onRejected={(reason) => setGalleryUploadMsg(reason)}
        />
        {galleryUploadMsg ? (
          <p className="gallery-upload-msg" role="status">
            {galleryUploadMsg}
          </p>
        ) : null}
      </Section>

      <footer className="gallery__section" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
        DexAtlas Desktop · Q2-M1 组件画廊 · 组件定义于 src/components/，token 于 src/styles/tokens.css。
      </footer>
    </div>
  );
}
