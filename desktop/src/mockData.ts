/**
 * 受控 mock 数据 — Q2-M1 页面联调用。
 * 数据形状与 src/types.ts 一致；后续窗口接真实后端时只替换数据源，不改页面结构。
 * 注意：这里的数字是原型演示数据，不代表任何真实测量结果。
 */

import type {
  BackendStatus,
  EvidenceDetail,
  EvidenceItem,
  LogEntry,
  ProjectSummary,
  SourceLine,
  StageInfo,
} from "./types";

/** 分析阶段定义（§2-3 左侧阶段进度） */
export const STAGES: StageInfo[] = [
  { id: "collect", label: "采集", description: "读取 APK 结构、manifest 与签名信息" },
  { id: "parse", label: "解析", description: "Apktool 反编译资源与 Smali，JADX 还原 Java 源码" },
  { id: "index", label: "索引", description: "Androguard 建立类/方法/字段符号索引" },
  { id: "evidence", label: "证据", description: "抽取权限、组件、字符串与敏感调用点" },
  { id: "report", label: "报告", description: "汇总为可复核的 Markdown / JSON 报告" },
];

/** 首页最近项目 mock 列表 */
export const RECENT_PROJECTS: ProjectSummary[] = [
  {
    id: "demo-app",
    name: "demo-app",
    packageName: "com.example.demo",
    sizeLabel: "12.4 MB",
    updatedLabel: "10 分钟前",
    status: "running",
  },
  {
    id: "bench-marker",
    name: "bench-marker",
    packageName: "org.bench.marker",
    sizeLabel: "8.1 MB",
    updatedLabel: "2 小时前",
    status: "done",
    evidenceCount: 47,
  },
  {
    id: "legacy-pay",
    name: "legacy-pay",
    packageName: "com.legacy.pay",
    sizeLabel: "21.7 MB",
    updatedLabel: "昨天",
    status: "partial",
    evidenceCount: 12,
  },
  {
    id: "broken-ota",
    name: "broken-ota",
    packageName: "com.broken.ota",
    sizeLabel: "5.3 MB",
    updatedLabel: "3 天前",
    status: "error",
  },
  {
    id: "sample-empty",
    name: "sample-empty",
    packageName: "io.sample.empty",
    sizeLabel: "1.2 MB",
    updatedLabel: "上周",
    status: "idle",
  },
];

/** 分析页初始日志 */
export const INITIAL_LOGS: LogEntry[] = [
  { id: 1, timeLabel: "10:02:11", level: "info", source: "采集", message: "已读取 APK：demo-app.apk（12.4 MB，minSdk 24）" },
  { id: 2, timeLabel: "10:02:12", level: "info", source: "采集", message: "manifest 解析完成：18 个组件，28 项权限声明" },
  { id: 3, timeLabel: "10:02:13", level: "info", source: "解析", message: "Apktool 解码资源与 Smali …" },
  { id: 4, timeLabel: "10:02:19", level: "debug", source: "解析", message: "JADX 反编译 classes.dex（1 个 dex，38,214 个类）" },
  { id: 5, timeLabel: "10:02:26", level: "success", source: "解析", message: "JADX 完成：还原 37,905 个类，482 个类降级为 Smali 视图" },
  { id: 6, timeLabel: "10:02:27", level: "info", source: "索引", message: "Androguard 建立符号索引 …" },
];

/** 后端状态面板初始值 */
export const INITIAL_BACKENDS: BackendStatus[] = [
  { name: "Apktool", state: "done", detail: "资源与 Smali 解码完成", progress: 100 },
  { name: "JADX", state: "done", detail: "37,905 类还原完成", progress: 100 },
  { name: "Androguard", state: "running", detail: "符号索引构建中 …", progress: 46 },
];

/** 详情页左列证据列表 mock */
export const EVIDENCE_ITEMS: EvidenceItem[] = [
  { id: "ev-1", kind: "permission", title: "android.permission.READ_SMS", subtitle: "manifest 声明 · AndroidManifest.xml", origin: "apktool" },
  { id: "ev-2", kind: "symbol", title: "MainActivity.onCreate", subtitle: "com.example.demo", origin: "jadx" },
  { id: "ev-3", kind: "sink", title: "TelephonyManager.getDeviceId", subtitle: "SmsLeakWorker.collect()", origin: "jadx" },
  { id: "ev-4", kind: "string", title: "\"https://api.example-test.com/v1/upload\"", subtitle: "strings.xml · app_name 旁", origin: "apktool" },
  { id: "ev-5", kind: "component", title: "SmsReceiver", subtitle: "exported=true · receivers", origin: "androguard" },
  { id: "ev-6", kind: "symbol", title: "CryptoBox.decrypt", subtitle: "com.example.demo.util", origin: "jadx" },
  { id: "ev-7", kind: "sink", title: "Runtime.exec", subtitle: "ShellHelper.runCommand()", origin: "jadx" },
  { id: "ev-8", kind: "permission", title: "android.permission.SEND_SMS", subtitle: "manifest 声明 · uses-permission", origin: "apktool" },
];

/** 证据详情 mock（抽屉内容） */
export const EVIDENCE_DETAILS: Record<string, EvidenceDetail> = {
  "ev-1": {
    ...EVIDENCE_ITEMS[0]!,
    summary: "应用声明读取短信权限。该权限在分析样本中通常用于验证码读取或短信备份，需结合调用点判断是否越界。",
    locator: { path: "AndroidManifest.xml", line: 12 },
    snippet: "<uses-permission android:name=\"android.permission.READ_SMS\" />",
    relatedIds: ["ev-3", "ev-8"],
  },
  "ev-2": {
    ...EVIDENCE_ITEMS[1]!,
    summary: "入口 Activity 的 onCreate 方法，包含初始化与权限请求流程。",
    locator: { path: "sources/com/example/demo/MainActivity.java", line: 24 },
    snippet: "@Override\nprotected void onCreate(Bundle savedInstanceState) {\n    super.onCreate(savedInstanceState);\n    SmsLeakWorker.schedule(this);\n}",
    relatedIds: ["ev-3"],
  },
  "ev-3": {
    ...EVIDENCE_ITEMS[2]!,
    summary: "敏感数据汇聚点：设备 ID 读取。与 READ_SMS 权限共同出现时，符合短信隐私类风险模式。",
    locator: { path: "sources/com/example/demo/work/SmsLeakWorker.java", line: 88 },
    snippet: "final String deviceId = telephonyManager.getDeviceId();\nuploadQueue.offer(new Payload(deviceId, smsBody));",
    relatedIds: ["ev-1", "ev-4"],
  },
  "ev-4": {
    ...EVIDENCE_ITEMS[3]!,
    summary: "硬编码上传地址。域名不在样本签名证书的已知域名集合中，建议人工复核。",
    locator: { path: "res/values/strings.xml", line: 31 },
    snippet: "<string name=\"upload_endpoint\">https://api.example-test.com/v1/upload</string>",
    relatedIds: ["ev-3"],
  },
  "ev-5": {
    ...EVIDENCE_ITEMS[4]!,
    summary: "导出的广播接收器。exported=true 且未声明自定义权限保护，外部应用可直接触发。",
    locator: { path: "AndroidManifest.xml", line: 47 },
    snippet: "<receiver android:name=\".SmsReceiver\" android:exported=\"true\">\n    <intent-filter>…</intent-filter>\n</receiver>",
    relatedIds: ["ev-1"],
  },
  "ev-6": {
    ...EVIDENCE_ITEMS[5]!,
    summary: "自实现解密工具类，使用静态密钥。密钥硬编码在常量池中。",
    locator: { path: "sources/com/example/demo/util/CryptoBox.java", line: 15 },
    snippet: "private static final byte[] KEY = \"dexatlas-demo-key\".getBytes();",
    relatedIds: [],
  },
  "ev-7": {
    ...EVIDENCE_ITEMS[6]!,
    summary: "动态命令执行点。参数来自外部输入时构成命令注入风险面。",
    locator: { path: "sources/com/example/demo/shell/ShellHelper.java", line: 52 },
    snippet: "Process p = Runtime.getRuntime().exec(cmd);",
    relatedIds: [],
  },
  "ev-8": {
    ...EVIDENCE_ITEMS[7]!,
    summary: "应用声明发送短信权限，与 READ_SMS 组合后具备完整短信读写能力。",
    locator: { path: "AndroidManifest.xml", line: 13 },
    snippet: "<uses-permission android:name=\"android.permission.SEND_SMS\" />",
    relatedIds: ["ev-1"],
  },
};

/** 详情页源码预览 mock（SmsLeakWorker 片段，证据 ev-3 引用第 88 行） */
export const SOURCE_LINES: SourceLine[] = [
  { line: 82, text: "private void collect() {" },
  { line: 83, text: "    TelephonyManager tm =" },
  { line: 84, text: "        (TelephonyManager) context.getSystemService(TELEPHONY_SERVICE);" },
  { line: 85, text: "    if (tm == null) {" },
  { line: 86, text: "        Log.w(TAG, \"telephony service unavailable\");" },
  { line: 87, text: "        return;" },
  { line: 88, text: "    final String deviceId = tm.getDeviceId();  // 敏感：设备标识" },
  { line: 89, text: "    uploadQueue.offer(new Payload(deviceId, latestSmsBody()));" },
  { line: 90, text: "}" },
  { line: 91, text: "" },
  { line: 92, text: "private String latestSmsBody() {" },
  { line: 93, text: "    Cursor c = context.getContentResolver().query(" },
  { line: 94, text: "        Telephony.Sms.Inbox.CONTENT_URI, null, null, null, null);" },
  { line: 95, text: "    return c != null && c.moveToFirst() ? c.getString(2) : \"\";" },
  { line: 96, text: "}" },
];
