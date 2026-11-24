import "./EvidencePage.css";

interface EvidenceItem {
  id: string;
  kind: "manifest" | "smali" | "java" | "symbol";
  label: string;
  backend: string;
  locator: string;
}

// 占位数据：证据检索与抽屉交互由后续窗口完成。
const EVIDENCE: EvidenceItem[] = [
  {
    id: "E-101",
    kind: "manifest",
    label: "usesCleartextTraffic=\"true\"",
    backend: "Apktool",
    locator: "AndroidManifest.xml:42",
  },
  {
    id: "E-102",
    kind: "smali",
    label: "loadUrl(file://…) 调用点",
    backend: "Apktool",
    locator: "MainActivity.smali:188",
  },
  {
    id: "E-103",
    kind: "java",
    label: "onCreate() 反编译片段",
    backend: "JADX",
    locator: "com/acme/payment/MainActivity.java:61",
  },
  {
    id: "E-104",
    kind: "symbol",
    label: "Lcom/acme/payment/MainActivity; → Landroid/webkit/WebView;",
    backend: "Androguard",
    locator: "classes.dex",
  },
];

const KIND_LABEL: Record<EvidenceItem["kind"], string> = {
  manifest: "清单",
  smali: "Smali",
  java: "Java",
  symbol: "符号图",
};

/** 证据页：证据条目总览（供报告与详情页引用）。 */
export default function EvidencePage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">证据</h1>
        <p className="page-subtitle">按后端归档的分析记录，locator 指向可复核的原始位置。</p>
      </header>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>编号</th>
              <th>类型</th>
              <th>内容</th>
              <th>后端</th>
              <th>Locator</th>
            </tr>
          </thead>
          <tbody>
            {EVIDENCE.map((e) => (
              <tr key={e.id}>
                <td className="evidence-id">{e.id}</td>
                <td>
                  <span className="badge badge-muted">{KIND_LABEL[e.kind]}</span>
                </td>
                <td className="evidence-label">{e.label}</td>
                <td>{e.backend}</td>
                <td className="evidence-locator">{e.locator}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
