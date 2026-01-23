/**
 * 桃園查估派工管理系統 API 服務
 *
 * 此檔案為向後相容入口，實際實作已模組化至 ./taoyuan/ 目錄
 *
 * 模組結構:
 * - ./taoyuan/projects.ts - 轄管工程 API
 * - ./taoyuan/dispatchOrders.ts - 派工單 API
 * - ./taoyuan/payments.ts - 契金管控/總控表/統計 API
 * - ./taoyuan/documentLinks.ts - 公文關聯 API
 * - ./taoyuan/projectLinks.ts - 工程關聯 API
 * - ./taoyuan/attachments.ts - 派工單附件 API
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

// 重新匯出所有模組 API
export {
  // API 服務
  taoyuanProjectsApi,
  dispatchOrdersApi,
  contractPaymentsApi,
  masterControlApi,
  statisticsApi,
  documentLinksApi,
  documentProjectLinksApi,
  projectLinksApi,
  dispatchAttachmentsApi,
  // 統一入口
  taoyuanDispatchApi,
} from './taoyuan';

// 重新匯出型別
export type {
  // 關聯型別
  LinkType,
  DocumentDispatchLink,
  DocumentProjectLink,
  ProjectDispatchLink,
  // 附件型別
  DispatchAttachment,
  DispatchAttachmentListResponse,
  DispatchAttachmentUploadResult,
  DispatchAttachmentDeleteResult,
  DispatchAttachmentVerifyResult,
} from './taoyuan';

// 預設匯出
export { taoyuanDispatchApi as default } from './taoyuan';
