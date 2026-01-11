/**
 * 應用程式路由器
 *
 * 提供懶載入與路由保護功能
 *
 * @version 1.1.0
 * @date 2026-01-06
 */

import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ROUTES } from './types';
import { ProtectedRoute, AdminRoute } from './ProtectedRoute';
import { PageLoading } from '../components/common';
import Layout from '../components/Layout';

// --- 整合說明 ---
// ContractCasePage 是功能和 UI 完整的主體。
// 所有與 /projects 相關的路徑都將重定向到功能更完整的 /contract-cases 相關路徑。

// 懶加載頁面組件
const DocumentPage = lazy(() => import('../pages/DocumentPage').then(module => ({ default: module.DocumentPage })));
const DocumentDetailPage = lazy(() => import('../pages/DocumentDetailPage').then(module => ({ default: module.DocumentDetailPage })));
const DocumentCreatePage = lazy(() => import('../pages/DocumentCreatePage').then(module => ({ default: module.DocumentCreatePage })));
const DocumentEditPage = lazy(() => import('../pages/DocumentEditPage').then(module => ({ default: module.DocumentEditPage })));
const DashboardPage = lazy(() => import('../pages/DashboardPage').then(module => ({ default: module.DashboardPage })));
const SettingsPage = lazy(() => import('../pages/SettingsPage').then(module => ({ default: module.SettingsPage })));
const ProfilePage = lazy(() => import('../pages/ProfilePage').then(module => ({ default: module.ProfilePage })));
const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then(module => ({ default: module.NotFoundPage })));
const DatabaseManagementPage = lazy(() => import('../pages/DatabaseManagementPage').then(module => ({ default: module.DatabaseManagementPage })));
const EntryPage = lazy(() => import('../pages/EntryPage'));
const LoginPage = lazy(() => import('../pages/LoginPage'));
const RegisterPage = lazy(() => import('../pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('../pages/ForgotPasswordPage'));
const UserManagementPage = lazy(() => import('../pages/UserManagementPage'));

// --- 承攬案件管理 ---
// 列表頁面
const ContractCasePage = lazy(() => import('../pages/ContractCasePage').then(module => ({ default: module.ContractCasePage })));
// 詳情頁面 - 採用 TAB 分頁模式（案件資訊、承辦同仁、協力廠商）
const ContractCaseDetailPage = lazy(() => import('../pages/ContractCaseDetailPage').then(module => ({ default: module.ContractCaseDetailPage })));
// 表單頁面 - 新增/編輯
const ContractCaseFormPage = lazy(() => import('../pages/ContractCaseFormPage').then(module => ({ default: module.ContractCaseFormPage })));

const DocumentNumbersPage = lazy(() => import('../pages/DocumentNumbersPage').then(module => ({ default: module.DocumentNumbersPage })));
const SendDocumentCreatePage = lazy(() => import('../pages/SendDocumentCreatePage').then(module => ({ default: module.SendDocumentCreatePage })));
const ReceiveDocumentCreatePage = lazy(() => import('../pages/ReceiveDocumentCreatePage').then(module => ({ default: module.ReceiveDocumentCreatePage })));
const AgenciesPage = lazy(() => import('../pages/AgenciesPage').then(module => ({ default: module.AgenciesPage })));
const ApiMappingDisplayPage = lazy(() => import('../pages/ApiMappingDisplayPage').then(module => ({ default: module.ApiMappingDisplayPage })));
const ApiDocumentationPage = lazy(() => import('../pages/ApiDocumentationPage'));
const VendorPage = lazy(() => import('../pages/VendorPage'));
const StaffPage = lazy(() => import('../pages/StaffPage'));
const SiteManagementPage = lazy(() => import('../pages/SiteManagementPage').then(module => ({ default: module.default })));
const CalendarPage = lazy(() => import('../pages/CalendarPage'));
const ReportsPage = lazy(() => import('../pages/ReportsPage'));
const GoogleAuthDiagnosticPage = lazy(() => import('../pages/GoogleAuthDiagnosticPage'));
const SystemPage = lazy(() => import('../pages/SystemPage'));
const PermissionManagementPage = lazy(() => import('../pages/PermissionManagementPage'));
// PureCalendarPage 已整合至 CalendarPage，保留重導向以維持相容性
// const PureCalendarPage = lazy(() => import('../pages/PureCalendarPage'));
const UnifiedFormDemoPage = lazy(() => import('../pages/UnifiedFormDemoPage'));
const AdminDashboardPage = lazy(() => import('../pages/AdminDashboardPage'));

// ProtectedRoute 已移至獨立模組：./ProtectedRoute.tsx

// 主路由器組件
export const AppRouter: React.FC = () => {
  return (
    <Layout>
      <Suspense fallback={<PageLoading message="載入頁面中..." />}>
        <Routes>
          {/* 系統入口與登入相關頁面 */}
          <Route path={ROUTES.ENTRY} element={<EntryPage />} />
          <Route path={ROUTES.LOGIN} element={<LoginPage />} />
          <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
          <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPasswordPage />} />

          {/* 首頁重定向到入口頁面 */}
          <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.ENTRY} replace />} />
          
          {/* 公文相關路由 */}
          <Route path={ROUTES.DOCUMENTS} element={<DocumentPage />} />
          <Route path={ROUTES.DOCUMENT_DETAIL} element={<DocumentDetailPage />} />
          <Route path={ROUTES.DOCUMENT_CREATE} element={<ReceiveDocumentCreatePage />} />
          <Route path={ROUTES.DOCUMENT_EDIT} element={<DocumentEditPage />} />
          
          {/* 儀表板 */}
          <Route path={ROUTES.DASHBOARD} element={<DashboardPage />} />
          
          {/* --- 承攬案件路由 (以 /contract-cases 為主) --- */}
          {/* 列表頁面 */}
          <Route path={ROUTES.CONTRACT_CASES} element={<ContractCasePage />} />

          {/* 詳情頁面 - TAB 分頁（案件資訊、承辦同仁、協力廠商） */}
          <Route path={ROUTES.CONTRACT_CASE_DETAIL} element={<ContractCaseDetailPage />} />

          {/* 新增/編輯頁面 */}
          <Route path={ROUTES.CONTRACT_CASE_CREATE} element={<ContractCaseFormPage />} />
          <Route path={ROUTES.CONTRACT_CASE_EDIT} element={<ContractCaseFormPage />} />

          {/* 舊路由重定向 */}
          <Route path={ROUTES.CASES} element={<Navigate to={ROUTES.CONTRACT_CASES} replace />} />
          <Route path={ROUTES.PROJECTS} element={<Navigate to={ROUTES.CONTRACT_CASES} replace />} />
          <Route path={ROUTES.CASE_DETAIL} element={<Navigate to={ROUTES.CONTRACT_CASES} replace />} />
          <Route path={ROUTES.CASE_CREATE} element={<Navigate to={ROUTES.CONTRACT_CASES} replace />} />
          <Route path={ROUTES.CASE_EDIT} element={<Navigate to={ROUTES.CONTRACT_CASES} replace />} />

          {/* 發文字號管理 */}
          <Route path={ROUTES.DOCUMENT_NUMBERS} element={<DocumentNumbersPage />} />
          <Route path={ROUTES.SEND_DOCUMENT_CREATE} element={<SendDocumentCreatePage />} />
          
          {/* 機關單位管理 */}
          <Route path={ROUTES.AGENCIES} element={<AgenciesPage />} />
          
          {/* API 對應頁面 */}
          <Route path={ROUTES.API_MAPPING} element={<ApiMappingDisplayPage />} />
          
          {/* API 文件頁面 */}
          <Route path={ROUTES.API_DOCS} element={<ApiDocumentationPage />} />
          
          {/* 廠商管理 */}
          <Route path={ROUTES.VENDORS} element={<VendorPage />} />

          {/* 承辦同仁管理 */}
          <Route path={ROUTES.STAFF} element={<StaffPage />} />

          {/* 行事曆 */}
          <Route path={ROUTES.CALENDAR} element={<CalendarPage />} />

          {/* 純粹行事曆 - 重導向至整合行事曆 */}
          <Route path={ROUTES.PURE_CALENDAR} element={<Navigate to={ROUTES.CALENDAR} replace />} />

          {/* 統計報表 */}
          <Route path={ROUTES.REPORTS} element={<ReportsPage />} />

          {/* 統一表單示例 */}
          <Route path={ROUTES.UNIFIED_FORM_DEMO} element={<UnifiedFormDemoPage />} />

          {/* Google認證診斷 */}
          <Route path={ROUTES.GOOGLE_AUTH_DIAGNOSTIC} element={<GoogleAuthDiagnosticPage />} />

          {/* 系統管理 */}
          <Route path={ROUTES.SYSTEM} element={<SystemPage />} />

          {/* 管理員面板 */}
          <Route path="/admin/dashboard" element={<ProtectedRoute requireAuth={true} roles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />

          {/* 權限管理 */}
          <Route path={ROUTES.PERMISSION_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><PermissionManagementPage /></ProtectedRoute>} />

          {/* 網站管理 */}
          <Route path={ROUTES.SITE_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><SiteManagementPage /></ProtectedRoute>} />

          {/* 需要認證的路由 */}
          <Route path={ROUTES.SETTINGS} element={<ProtectedRoute requireAuth={true} roles={['admin']}><SettingsPage /></ProtectedRoute>} />
          <Route path={ROUTES.USER_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><UserManagementPage /></ProtectedRoute>} />
          <Route path={ROUTES.PROFILE} element={<ProtectedRoute requireAuth={true}><ProfilePage /></ProtectedRoute>} />
          <Route path={ROUTES.DATABASE} element={<ProtectedRoute requireAuth={true} roles={['admin']}><DatabaseManagementPage /></ProtectedRoute>} />

          {/* 404 頁面 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </Layout>
  );
};
