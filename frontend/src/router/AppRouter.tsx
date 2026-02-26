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
import { ProtectedRoute } from './ProtectedRoute';
import { PageLoading } from '../components/common';
import Layout from '../components/Layout';

// --- 整合說明 ---
// ContractCasePage 是功能和 UI 完整的主體。
// 所有與 /projects 相關的路徑都將重定向到功能更完整的 /contract-cases 相關路徑。

// 懶加載頁面組件
const DocumentPage = lazy(() => import('../pages/DocumentPage').then(module => ({ default: module.DocumentPage })));
const DocumentDetailPage = lazy(() => import('../pages/DocumentDetailPage').then(module => ({ default: module.DocumentDetailPage })));
const DocumentEditPage = lazy(() => import('../pages/DocumentEditPage').then(module => ({ default: module.DocumentEditPage })));
const DashboardPage = lazy(() => import('../pages/DashboardPage').then(module => ({ default: module.DashboardPage })));
const ProfilePage = lazy(() => import('../pages/ProfilePage').then(module => ({ default: module.ProfilePage })));
const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then(module => ({ default: module.NotFoundPage })));
const DatabaseManagementPage = lazy(() => import('../pages/DatabaseManagementPage').then(module => ({ default: module.DatabaseManagementPage })));
// EntryPage 已整合至 LoginPage，保留重導向
const LoginPage = lazy(() => import('../pages/LoginPage'));
const RegisterPage = lazy(() => import('../pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('../pages/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('../pages/ResetPasswordPage'));
const MFAVerifyPage = lazy(() => import('../pages/MFAVerifyPage'));
const VerifyEmailPage = lazy(() => import('../pages/VerifyEmailPage'));
const UserManagementPage = lazy(() => import('../pages/UserManagementPage'));
const UserFormPage = lazy(() => import('../pages/UserFormPage').then(module => ({ default: module.UserFormPage })));

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
const AgencyFormPage = lazy(() => import('../pages/AgencyFormPage').then(module => ({ default: module.AgencyFormPage })));
const ApiMappingDisplayPage = lazy(() => import('../pages/ApiMappingDisplayPage').then(module => ({ default: module.ApiMappingDisplayPage })));
const ApiDocumentationPage = lazy(() => import('../pages/ApiDocumentationPage'));
const VendorPage = lazy(() => import('../pages/VendorPage'));
const VendorFormPage = lazy(() => import('../pages/VendorFormPage').then(module => ({ default: module.VendorFormPage })));
const StaffPage = lazy(() => import('../pages/StaffPage'));
const StaffCreatePage = lazy(() => import('../pages/StaffCreatePage').then(module => ({ default: module.StaffCreatePage })));
const StaffDetailPage = lazy(() => import('../pages/StaffDetailPage').then(module => ({ default: module.StaffDetailPage })));
const CertificationFormPage = lazy(() => import('../pages/CertificationFormPage').then(module => ({ default: module.CertificationFormPage })));
const SiteManagementPage = lazy(() => import('../pages/SiteManagementPage').then(module => ({ default: module.default })));
const BackupManagementPage = lazy(() => import('../pages/BackupManagementPage').then(module => ({ default: module.BackupManagementPage })));
const CalendarPage = lazy(() => import('../pages/CalendarPage'));
const CalendarEventFormPage = lazy(() => import('../pages/CalendarEventFormPage'));
const ReportsPage = lazy(() => import('../pages/ReportsPage'));
const GoogleAuthDiagnosticPage = lazy(() => import('../pages/GoogleAuthDiagnosticPage'));
// SystemPage 已移除，功能整合至其他管理頁面
const PermissionManagementPage = lazy(() => import('../pages/PermissionManagementPage'));
const RolePermissionDetailPage = lazy(() => import('../pages/RolePermissionDetailPage'));
// PureCalendarPage 已整合至 CalendarPage，保留重導向以維持相容性
// const PureCalendarPage = lazy(() => import('../pages/PureCalendarPage'));
const UnifiedFormDemoPage = lazy(() => import('../pages/UnifiedFormDemoPage'));
const AdminDashboardPage = lazy(() => import('../pages/AdminDashboardPage'));
const DeploymentManagementPage = lazy(() => import('../pages/DeploymentManagementPage'));
const AIAssistantManagementPage = lazy(() => import('../pages/AIAssistantManagementPage'));
const KnowledgeGraphPage = lazy(() => import('../pages/KnowledgeGraphPage'));

// 桃園查估專區
const TaoyuanDispatchPage = lazy(() => import('../pages/TaoyuanDispatchPage'));
const TaoyuanDispatchCreatePage = lazy(() => import('../pages/TaoyuanDispatchCreatePage'));
const TaoyuanDispatchDetailPage = lazy(() => import('../pages/TaoyuanDispatchDetailPage'));
const TaoyuanProjectCreatePage = lazy(() => import('../pages/TaoyuanProjectCreatePage'));
const TaoyuanProjectDetailPage = lazy(() => import('../pages/TaoyuanProjectDetailPage'));
const WorkRecordFormPage = lazy(() => import('../pages/WorkRecordFormPage'));

// ProtectedRoute 已移至獨立模組：./ProtectedRoute.tsx

// 主路由器組件
export const AppRouter: React.FC = () => {
  return (
    <Layout>
      <Suspense fallback={<PageLoading message="載入頁面中..." />}>
        <Routes>
          {/* 首頁重導向至儀表板 */}
          <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.DASHBOARD} replace />} />

          {/* 統一登入入口 */}
          <Route path={ROUTES.LOGIN} element={<LoginPage />} />
          <Route path={ROUTES.ENTRY} element={<LoginPage />} />  {/* /entry 使用 LoginPage */}
          <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
          <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPasswordPage />} />
          <Route path={ROUTES.RESET_PASSWORD} element={<ResetPasswordPage />} />
          <Route path={ROUTES.MFA_VERIFY} element={<MFAVerifyPage />} />
          <Route path={ROUTES.VERIFY_EMAIL} element={<VerifyEmailPage />} />

          {/* 公文相關路由（需要認證） */}
          <Route path={ROUTES.DOCUMENTS} element={<ProtectedRoute><DocumentPage /></ProtectedRoute>} />
          <Route path={ROUTES.DOCUMENT_DETAIL} element={<ProtectedRoute><DocumentDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.DOCUMENT_CREATE} element={<ProtectedRoute><ReceiveDocumentCreatePage /></ProtectedRoute>} />
          <Route path={ROUTES.DOCUMENT_EDIT} element={<ProtectedRoute><DocumentEditPage /></ProtectedRoute>} />

          {/* 儀表板（需要認證） */}
          <Route path={ROUTES.DASHBOARD} element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />

          {/* --- 承攬案件路由（需要認證） --- */}
          <Route path={ROUTES.CONTRACT_CASES} element={<ProtectedRoute><ContractCasePage /></ProtectedRoute>} />
          <Route path={ROUTES.CONTRACT_CASE_DETAIL} element={<ProtectedRoute><ContractCaseDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.CONTRACT_CASE_CREATE} element={<ProtectedRoute><ContractCaseFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.CONTRACT_CASE_EDIT} element={<ProtectedRoute><ContractCaseFormPage /></ProtectedRoute>} />

          {/* 發文字號管理（需要認證） */}
          <Route path={ROUTES.DOCUMENT_NUMBERS} element={<ProtectedRoute><DocumentNumbersPage /></ProtectedRoute>} />
          <Route path={ROUTES.SEND_DOCUMENT_CREATE} element={<ProtectedRoute><SendDocumentCreatePage /></ProtectedRoute>} />

          {/* 機關單位管理（需要認證） */}
          <Route path={ROUTES.AGENCIES} element={<ProtectedRoute><AgenciesPage /></ProtectedRoute>} />
          <Route path={ROUTES.AGENCY_CREATE} element={<ProtectedRoute><AgencyFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.AGENCY_EDIT} element={<ProtectedRoute><AgencyFormPage /></ProtectedRoute>} />

          {/* API 對應頁面（需管理員） */}
          <Route path={ROUTES.API_MAPPING} element={<ProtectedRoute requireAuth={true} roles={['admin']}><ApiMappingDisplayPage /></ProtectedRoute>} />

          {/* API 文件頁面（需管理員） */}
          <Route path={ROUTES.API_DOCS} element={<ProtectedRoute requireAuth={true} roles={['admin']}><ApiDocumentationPage /></ProtectedRoute>} />

          {/* 廠商管理（需要認證） */}
          <Route path={ROUTES.VENDORS} element={<ProtectedRoute><VendorPage /></ProtectedRoute>} />
          <Route path={ROUTES.VENDOR_CREATE} element={<ProtectedRoute><VendorFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.VENDOR_EDIT} element={<ProtectedRoute><VendorFormPage /></ProtectedRoute>} />

          {/* 承辦同仁管理（需要認證） */}
          <Route path={ROUTES.STAFF} element={<ProtectedRoute><StaffPage /></ProtectedRoute>} />
          <Route path={ROUTES.STAFF_CREATE} element={<ProtectedRoute><StaffCreatePage /></ProtectedRoute>} />
          <Route path={ROUTES.STAFF_DETAIL} element={<ProtectedRoute><StaffDetailPage /></ProtectedRoute>} />
          {/* 證照管理（導航模式） */}
          <Route path={ROUTES.CERTIFICATION_CREATE} element={<ProtectedRoute><CertificationFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.CERTIFICATION_EDIT} element={<ProtectedRoute><CertificationFormPage /></ProtectedRoute>} />

          {/* 行事曆（需要認證） */}
          <Route path={ROUTES.CALENDAR} element={<ProtectedRoute><CalendarPage /></ProtectedRoute>} />
          <Route path={ROUTES.CALENDAR_EVENT_CREATE} element={<ProtectedRoute><CalendarEventFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.CALENDAR_EVENT_EDIT} element={<ProtectedRoute><CalendarEventFormPage /></ProtectedRoute>} />

          {/* 純粹行事曆 - 重導向至 /calendar */}
          <Route path={ROUTES.PURE_CALENDAR} element={<Navigate to={ROUTES.CALENDAR} replace />} />

          {/* 專案路由 - 重導向至承攬案件 */}
          <Route path={ROUTES.PROJECTS} element={<Navigate to={ROUTES.CONTRACT_CASES} replace />} />

          {/* 統計報表（需要認證） */}
          <Route path={ROUTES.REPORTS} element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />

          {/* 桃園查估專區（需要認證） */}
          <Route path={ROUTES.TAOYUAN_DISPATCH} element={<ProtectedRoute><TaoyuanDispatchPage /></ProtectedRoute>} />
          <Route path={ROUTES.TAOYUAN_DISPATCH_CREATE} element={<ProtectedRoute><TaoyuanDispatchCreatePage /></ProtectedRoute>} />
          <Route path={ROUTES.TAOYUAN_DISPATCH_DETAIL} element={<ProtectedRoute><TaoyuanDispatchDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.TAOYUAN_PROJECT_CREATE} element={<ProtectedRoute><TaoyuanProjectCreatePage /></ProtectedRoute>} />
          <Route path={ROUTES.TAOYUAN_PROJECT_DETAIL} element={<ProtectedRoute><TaoyuanProjectDetailPage /></ProtectedRoute>} />
          {/* 作業歷程（導航模式） */}
          <Route path={ROUTES.TAOYUAN_WORKFLOW_CREATE} element={<ProtectedRoute><WorkRecordFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.TAOYUAN_WORKFLOW_EDIT} element={<ProtectedRoute><WorkRecordFormPage /></ProtectedRoute>} />

          {/* 統一表單示例（需管理員） */}
          <Route path={ROUTES.UNIFIED_FORM_DEMO} element={<ProtectedRoute requireAuth={true} roles={['admin']}><UnifiedFormDemoPage /></ProtectedRoute>} />

          {/* Google認證診斷（需管理員） */}
          <Route path={ROUTES.GOOGLE_AUTH_DIAGNOSTIC} element={<ProtectedRoute requireAuth={true} roles={['admin']}><GoogleAuthDiagnosticPage /></ProtectedRoute>} />

          {/* 系統管理 */}
          {/* /system 已移除，重定向至管理後台 */}
          <Route path={ROUTES.SYSTEM} element={<Navigate to={ROUTES.ADMIN_DASHBOARD} replace />} />

          {/* 管理員面板 */}
          <Route path={ROUTES.ADMIN_DASHBOARD} element={<ProtectedRoute requireAuth={true} roles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />

          {/* 權限管理 - 獨立頁面：管理系統權限定義與角色 */}
          <Route path={ROUTES.PERMISSION_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><PermissionManagementPage /></ProtectedRoute>} />
          <Route path={ROUTES.PERMISSION_ROLE_DETAIL} element={<ProtectedRoute requireAuth={true} roles={['admin']}><RolePermissionDetailPage /></ProtectedRoute>} />

          {/* 網站管理 */}
          <Route path={ROUTES.SITE_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><SiteManagementPage /></ProtectedRoute>} />

          {/* 備份管理 */}
          <Route path={ROUTES.BACKUP_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><BackupManagementPage /></ProtectedRoute>} />

          {/* 部署管理 */}
          <Route path={ROUTES.DEPLOYMENT_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><DeploymentManagementPage /></ProtectedRoute>} />

          {/* AI 助理管理（整合同義詞管理 + Prompt 管理） */}
          <Route path={ROUTES.AI_ASSISTANT_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><AIAssistantManagementPage /></ProtectedRoute>} />

          {/* 知識圖譜探索（獨立全螢幕頁面） */}
          <Route path={ROUTES.KNOWLEDGE_GRAPH} element={<ProtectedRoute><KnowledgeGraphPage /></ProtectedRoute>} />

          {/* 需要認證的路由 */}
          {/* /settings 已統一至 /profile */}
          <Route path={ROUTES.SETTINGS} element={<Navigate to={ROUTES.PROFILE} replace />} />
          <Route path={ROUTES.USER_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><UserManagementPage /></ProtectedRoute>} />
          <Route path={ROUTES.USER_CREATE} element={<ProtectedRoute requireAuth={true} roles={['admin']}><UserFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.USER_EDIT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><UserFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.PROFILE} element={<ProtectedRoute requireAuth={true}><ProfilePage /></ProtectedRoute>} />
          <Route path={ROUTES.DATABASE} element={<ProtectedRoute requireAuth={true} roles={['admin']}><DatabaseManagementPage /></ProtectedRoute>} />

          {/* 404 頁面 */}
          <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </Layout>
  );
};
