/**
 * 组件画廊的示例数据与公共片段。
 * 只做静态展示数据，不发请求。
 */

export const SAMPLE_ROWS = [
  { id: "ev-1", name: "READ_SMS", kind: "权限", origin: "Apktool", status: "completed" as const },
  { id: "ev-2", name: "MainActivity.onCreate", kind: "符号", origin: "JADX", status: "completed" as const },
  { id: "ev-3", name: "getDeviceId", kind: "汇聚点", origin: "JADX", status: "running" as const },
  { id: "ev-5", name: "SmsReceiver", kind: "组件", origin: "Androguard", status: "partial" as const },
  { id: "ev-8", name: "SEND_SMS", kind: "权限", origin: "Apktool", status: "pending" as const },
];

export const SAMPLE_CODE = `package com.example.demo;

public class SmsLeakWorker {
    private void collect() {
        TelephonyManager tm = (TelephonyManager)
            context.getSystemService(TELEPHONY_SERVICE);
        final String deviceId = tm.getDeviceId();  // 敏感：设备标识
        uploadQueue.offer(new Payload(deviceId, latestSmsBody()));
    }
}`;

export const SAMPLE_TIMELINE = [
  { key: "collect", title: "采集与校验", meta: "Apktool · 1.2s", status: "completed" as const },
  { key: "parse", title: "资源与 Smali 解析", meta: "Apktool · 3.4s", status: "completed" as const },
  { key: "index", title: "符号索引", meta: "Androguard · 4.1s", status: "running" as const },
  { key: "evidence", title: "证据抽取", meta: "待运行", status: "pending" as const },
  { key: "report", title: "报告生成", meta: "待运行", status: "pending" as const },
];

export const SAMPLE_NAV = [
  { key: "projects", label: "项目", icon: "▦" },
  { key: "analysis", label: "分析", icon: "◈" },
  { key: "evidence", label: "证据", icon: "◆" },
  { key: "reports", label: "报告", icon: "▤" },
  { key: "settings", label: "设置", icon: "⚙" },
];
