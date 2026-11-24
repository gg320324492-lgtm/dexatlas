import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import HomePage from "./pages/HomePage";
import { Analysis } from "./pages/Analysis";
import { ProjectDetail } from "./pages/ProjectDetail";
import FindingsPage from "./pages/FindingsPage";
import EvidencePage from "./pages/EvidencePage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";

// 路由结构对应左侧栏五项：项目（首页）/ 分析 / 证据 / 报告 / 设置。
// Q2-M1 新增：analysis/:projectId 由本窗口的三区页面承接；projects/:projectId 为项目详情三栏页。
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="analysis" element={<Analysis />} />
        <Route path="analysis/:projectId" element={<Analysis />} />
        <Route path="projects/:projectId" element={<ProjectDetail />} />
        <Route path="findings" element={<FindingsPage />} />
        <Route path="evidence" element={<EvidencePage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
