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
const EntryPage = lazy(() => import('../pages/EntryPage'));
const LoginPage = lazy(() => import('../pages/LoginPage'));
const RegisterPage = lazy(() => import('../pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('../pages/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('../pages/ResetPasswordPage'));
const MFAVerifyPage = lazy(() => import('../pages/MFAVerifyPage'));
const VerifyEmailPage = lazy(() => import('../pages/VerifyEmailPage'));
const LineCallbackPage = lazy(() => import('../pages/LineCallbackPage'));
const LineBindCallbackPage = lazy(() => import('../pages/LineBindCallbackPage'));
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
const ClientListPage = lazy(() => import('../pages/ClientListPage'));
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
const UnifiedFormDemoPage = lazy(() => import('../pages/UnifiedFormDemoPage'));
const AdminDashboardPage = lazy(() => import('../pages/AdminDashboardPage'));
const DeploymentManagementPage = lazy(() => import('../pages/DeploymentManagementPage'));
const UnifiedAgentPage = lazy(() => import('../pages/UnifiedAgentPage'));
const KnowledgeGraphPage = lazy(() => import('../pages/KnowledgeGraphPage'));
const SkillsCapabilityMapPage = lazy(() => import('../pages/SkillsCapabilityMapPage'));
const CodeGraphManagementPage = lazy(() => import('../pages/CodeGraphManagementPage'));
const ERPGraphPage = lazy(() => import('../pages/ERPGraphPage'));
const DatabaseGraphPage = lazy(() => import('../pages/DatabaseGraphPage'));
const KnowledgeBasePage = lazy(() => import('../pages/KnowledgeBasePage'));
const WikiPage = lazy(() => import('../pages/WikiPage'));
const SkillEvolutionPage = lazy(() => import('../pages/SkillEvolutionPage'));

// 桃園查估專區
const TaoyuanDispatchPage = lazy(() => import('../pages/TaoyuanDispatchPage'));
const TaoyuanDispatchCreatePage = lazy(() => import('../pages/TaoyuanDispatchCreatePage'));
const TaoyuanDispatchDetailPage = lazy(() => import('../pages/TaoyuanDispatchDetailPage'));
const TaoyuanProjectCreatePage = lazy(() => import('../pages/TaoyuanProjectCreatePage'));
const TaoyuanProjectDetailPage = lazy(() => import('../pages/TaoyuanProjectDetailPage'));
const WorkRecordFormPage = lazy(() => import('../pages/WorkRecordFormPage'));

// 專案管理 (PM)
const PMCaseListPage = lazy(() => import('../pages/PMCaseListPage'));
const PMCaseDetailPage = lazy(() => import('../pages/PMCaseDetailPage'));
const PMCaseFormPage = lazy(() => import('../pages/PMCaseFormPage'));

// 財務管理 (ERP)
const ERPHubPage = lazy(() => import('../pages/ERPHubPage'));
const ERPQuotationListPage = lazy(() => import('../pages/ERPQuotationListPage'));
const ERPQuotationDetailPage = lazy(() => import('../pages/ERPQuotationDetailPage'));
const ERPQuotationFormPage = lazy(() => import('../pages/ERPQuotationFormPage'));
const ERPExpenseListPage = lazy(() => import('../pages/ERPExpenseListPage'));
const ERPExpenseCreatePage = lazy(() => import('../pages/ERPExpenseCreatePage'));
const ERPExpenseDetailPage = lazy(() => import('../pages/ERPExpenseDetailPage'));
const ERPLedgerPage = lazy(() => import('../pages/ERPLedgerPage'));
const ERPLedgerCreatePage = lazy(() => import('../pages/ERPLedgerCreatePage'));
const ERPFinancialDashboardPage = lazy(() => import('../pages/ERPFinancialDashboardPage'));
const ERPEInvoiceSyncPage = lazy(() => import('../pages/ERPEInvoiceSyncPage'));
const ERPVendorAccountsPage = lazy(() => import('../pages/ERPVendorAccountsPage'));
const ERPVendorAccountDetailPage = lazy(() => import('../pages/ERPVendorAccountDetailPage'));
const ERPClientAccountsPage = lazy(() => import('../pages/ERPClientAccountsPage'));
const ERPClientAccountDetailPage = lazy(() => import('../pages/ERPClientAccountDetailPage'));
const ERPInvoiceSummaryPage = lazy(() => import('../pages/ERPInvoiceSummaryPage'));
const ERPAssetListPage = lazy(() => import('../pages/ERPAssetListPage'));
const ERPAssetDetailPage = lazy(() => import('../pages/ERPAssetDetailPage'));
const ERPAssetFormPage = lazy(() => import('../pages/ERPAssetFormPage'));
const ERPOperationalListPage = lazy(() => import('../pages/ERPOperationalListPage'));
const ERPOperationalDetailPage = lazy(() => import('../pages/ERPOperationalDetailPage'));
const ERPOperationalFormPage = lazy(() => import('../pages/ERPOperationalFormPage'));

// 數位分身 → redirect to /agent/dashboard
// 智能體中心 → UnifiedAgentPage (defined above)

// 資安管理
const SecurityCenterPage = lazy(() => import('../pages/SecurityCenterPage'));
const CaseNatureManagementPage = lazy(() => import('../pages/CaseNatureManagementPage'));
const AdminLoginHistoryPage = lazy(() => import('../pages/AdminLoginHistoryPage'));
const TenderSearchPage = lazy(() => import('../pages/TenderSearchPage'));
const TenderDetailPage = lazy(() => import('../pages/TenderDetailPage'));
const TenderGraphPage = lazy(() => import('../pages/TenderGraphPage'));
const TenderDashboardPage = lazy(() => import('../pages/TenderDashboardPage'));
const TenderOrgEcosystemPage = lazy(() => import('../pages/TenderOrgEcosystemPage'));
const TenderCompanyProfilePage = lazy(() => import('../pages/TenderCompanyProfilePage'));

// ProtectedRoute 已移至獨立模組：./ProtectedRoute.tsx

// 主路由器組件
export const AppRouter: React.FC = () => {
  return (
    <Layout>
      <Suspense fallback={<PageLoading message="載入頁面中..." />}>
        <Routes>
          {/* 首頁重導向至儀表板 */}
          <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.ENTRY} replace />} />

          {/* 公開入口 + 登入 */}
          <Route path={ROUTES.ENTRY} element={<EntryPage />} />
          <Route path={ROUTES.LOGIN} element={<LoginPage />} />
          <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
          <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPasswordPage />} />
          <Route path={ROUTES.RESET_PASSWORD} element={<ResetPasswordPage />} />
          <Route path={ROUTES.MFA_VERIFY} element={<MFAVerifyPage />} />
          <Route path={ROUTES.VERIFY_EMAIL} element={<VerifyEmailPage />} />
          <Route path={ROUTES.LINE_CALLBACK} element={<LineCallbackPage />} />
          <Route path={ROUTES.LINE_BIND_CALLBACK} element={<LineBindCallbackPage />} />

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
          <Route path={ROUTES.CLIENTS} element={<ProtectedRoute><ClientListPage /></ProtectedRoute>} />
          <Route path={ROUTES.CLIENT_CREATE} element={<ProtectedRoute><VendorFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.CLIENT_EDIT} element={<ProtectedRoute><VendorFormPage /></ProtectedRoute>} />

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
          <Route path={ROUTES.TAOYUAN} element={<Navigate to={ROUTES.TAOYUAN_DISPATCH} replace />} />
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

          {/* AI 智能體管理（管理模式） */}
          <Route path={ROUTES.AI_ASSISTANT_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><UnifiedAgentPage mode="admin" /></ProtectedRoute>} />

          {/* 公文圖譜 */}
          <Route path={ROUTES.KNOWLEDGE_GRAPH} element={<ProtectedRoute><KnowledgeGraphPage /></ProtectedRoute>} />
          {/* Skills 能力圖譜 */}
          <Route path={ROUTES.SKILLS_MAP} element={<ProtectedRoute><SkillsCapabilityMapPage /></ProtectedRoute>} />
          {/* 技能演化樹 */}
          <Route path={ROUTES.SKILL_EVOLUTION} element={<ProtectedRoute><SkillEvolutionPage /></ProtectedRoute>} />
          {/* 代碼圖譜 */}
          <Route path={ROUTES.CODE_GRAPH} element={<ProtectedRoute><CodeGraphManagementPage /></ProtectedRoute>} />
          {/* 代碼圖譜（舊路由相容重導向） */}
          <Route path={ROUTES.CODE_WIKI} element={<Navigate to={ROUTES.CODE_GRAPH} replace />} />
          {/* 代碼圖譜管理（舊路由相容重導向） */}
          <Route path={ROUTES.CODE_GRAPH_MANAGEMENT} element={<Navigate to={ROUTES.CODE_GRAPH} replace />} />
          {/* ERP 財務圖譜 */}
          <Route path={ROUTES.ERP_GRAPH} element={<ProtectedRoute><ERPGraphPage /></ProtectedRoute>} />
          {/* 資料庫圖譜 */}
          <Route path={ROUTES.DB_GRAPH} element={<ProtectedRoute><DatabaseGraphPage /></ProtectedRoute>} />
          {/* 數位分身（重導向至智能體中心） */}
          <Route path={ROUTES.DIGITAL_TWIN} element={<Navigate to={ROUTES.AGENT_DASHBOARD} replace />} />
          {/* 智能體中心（使用者模式） */}
          <Route path={ROUTES.AGENT_DASHBOARD} element={<ProtectedRoute><UnifiedAgentPage mode="user" /></ProtectedRoute>} />
          {/* 資安管理中心 */}
          <Route path={ROUTES.SECURITY_CENTER} element={<ProtectedRoute requireAuth={true} roles={['admin']}><SecurityCenterPage /></ProtectedRoute>} />
          {/* 作業性質代碼管理 */}
          <Route path={ROUTES.CASE_NATURE_MANAGEMENT} element={<ProtectedRoute requireAuth={true} roles={['admin']}><CaseNatureManagementPage /></ProtectedRoute>} />
          {/* 標案檢索 */}
          <Route path={ROUTES.TENDER_SEARCH} element={<ProtectedRoute><TenderSearchPage /></ProtectedRoute>} />
          <Route path={ROUTES.TENDER_DETAIL} element={<ProtectedRoute><TenderDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.TENDER_GRAPH} element={<ProtectedRoute><TenderGraphPage /></ProtectedRoute>} />
          <Route path={ROUTES.TENDER_DASHBOARD} element={<ProtectedRoute><TenderDashboardPage /></ProtectedRoute>} />
          <Route path={ROUTES.TENDER_ORG_ECOSYSTEM} element={<ProtectedRoute><TenderOrgEcosystemPage /></ProtectedRoute>} />
          <Route path={ROUTES.TENDER_COMPANY_PROFILE} element={<ProtectedRoute><TenderCompanyProfilePage /></ProtectedRoute>} />
          {/* 已整合路由重導向 (v5.5.3 — 功能已併入 TenderDetailPage) */}
          <Route path="/tender/company" element={<Navigate to="/tender/search" replace />} />
          <Route path="/tender/battle-room" element={<Navigate to="/tender/search" replace />} />
          <Route path="/tender/price-analysis" element={<Navigate to="/tender/search" replace />} />
          {/* 知識庫瀏覽器 */}
          <Route path={ROUTES.KNOWLEDGE_BASE} element={<ProtectedRoute requireAuth={true} roles={['admin']}><KnowledgeBasePage /></ProtectedRoute>} />
          <Route path={ROUTES.WIKI} element={<ProtectedRoute requireAuth={true}><WikiPage /></ProtectedRoute>} />

          {/* 專案管理 (PM) — 與 contract-cases 功能對齊 */}
          <Route path={ROUTES.PM_CASES} element={<ProtectedRoute><PMCaseListPage /></ProtectedRoute>} />
          <Route path={ROUTES.PM_CASE_CREATE} element={<ProtectedRoute><PMCaseFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.PM_CASE_EDIT} element={<ProtectedRoute><PMCaseFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.PM_CASE_DETAIL} element={<ProtectedRoute><PMCaseDetailPage /></ProtectedRoute>} />

          {/* 財務管理 (ERP) */}
          <Route path={ROUTES.ERP_QUOTATIONS} element={<ProtectedRoute><ERPQuotationListPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_QUOTATION_CREATE} element={<ProtectedRoute><ERPQuotationFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_QUOTATION_EDIT} element={<ProtectedRoute><ERPQuotationFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_QUOTATION_DETAIL} element={<ProtectedRoute><ERPQuotationDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_EXPENSES} element={<ProtectedRoute><ERPExpenseListPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_EXPENSE_CREATE} element={<ProtectedRoute><ERPExpenseCreatePage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_EXPENSE_DETAIL} element={<ProtectedRoute><ERPExpenseDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_LEDGER} element={<ProtectedRoute><ERPLedgerPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_LEDGER_CREATE} element={<ProtectedRoute><ERPLedgerCreatePage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_FINANCIAL_DASHBOARD} element={<ProtectedRoute><ERPFinancialDashboardPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_EINVOICE_SYNC} element={<ProtectedRoute><ERPEInvoiceSyncPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_VENDOR_ACCOUNT_DETAIL} element={<ProtectedRoute><ERPVendorAccountDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_VENDOR_ACCOUNTS} element={<ProtectedRoute><ERPVendorAccountsPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_CLIENT_ACCOUNT_DETAIL} element={<ProtectedRoute><ERPClientAccountDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_CLIENT_ACCOUNTS} element={<ProtectedRoute><ERPClientAccountsPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_INVOICE_SUMMARY} element={<ProtectedRoute><ERPInvoiceSummaryPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_ASSET_CREATE} element={<ProtectedRoute><ERPAssetFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_ASSET_EDIT} element={<ProtectedRoute><ERPAssetFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_ASSET_DETAIL} element={<ProtectedRoute><ERPAssetDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_ASSETS} element={<ProtectedRoute><ERPAssetListPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_OPERATIONAL_CREATE} element={<ProtectedRoute><ERPOperationalFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_OPERATIONAL_EDIT} element={<ProtectedRoute><ERPOperationalFormPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_OPERATIONAL_DETAIL} element={<ProtectedRoute><ERPOperationalDetailPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_OPERATIONAL} element={<ProtectedRoute><ERPOperationalListPage /></ProtectedRoute>} />
          <Route path={ROUTES.ERP_HUB} element={<ProtectedRoute><ERPHubPage /></ProtectedRoute>} />

          {/* 資安管理 */}
          <Route path={ROUTES.ADMIN_LOGIN_HISTORY} element={<ProtectedRoute roles={['admin', 'superuser']}><AdminLoginHistoryPage /></ProtectedRoute>} />

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
