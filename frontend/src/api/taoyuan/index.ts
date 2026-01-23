/**
 * 桃園查估派工管理系統 API 模組入口
 *
 * 將 taoyuanDispatchApi.ts (738行) 拆分為 6 個模組：
 * 1. projects.ts - 轄管工程 API
 * 2. dispatchOrders.ts - 派工單 API
 * 3. payments.ts - 契金管控/總控表/統計 API
 * 4. documentLinks.ts - 公文關聯 API
 * 5. projectLinks.ts - 工程關聯 API
 * 6. attachments.ts - 派工單附件 API
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

// 各模組 API
export { taoyuanProjectsApi } from './projects';
export { dispatchOrdersApi } from './dispatchOrders';
export { contractPaymentsApi, masterControlApi, statisticsApi } from './payments';
export { documentLinksApi, documentProjectLinksApi } from './documentLinks';
export { projectLinksApi } from './projectLinks';
export {
  dispatchAttachmentsApi,
  type DispatchAttachment,
  type DispatchAttachmentListResponse,
  type DispatchAttachmentUploadResult,
  type DispatchAttachmentDeleteResult,
  type DispatchAttachmentVerifyResult,
} from './attachments';

// 關聯型別重新匯出
export type {
  LinkType,
  DocumentDispatchLink,
  DocumentProjectLink,
  ProjectDispatchLink,
} from '../../types/api';

// 統一入口物件（向後相容）
import { taoyuanProjectsApi } from './projects';
import { dispatchOrdersApi } from './dispatchOrders';
import { contractPaymentsApi, masterControlApi, statisticsApi } from './payments';
import { documentLinksApi, documentProjectLinksApi } from './documentLinks';
import { projectLinksApi } from './projectLinks';
import { dispatchAttachmentsApi } from './attachments';

/**
 * 桃園派工管理 API 統一入口
 */
export const taoyuanDispatchApi = {
  projects: taoyuanProjectsApi,
  dispatchOrders: dispatchOrdersApi,
  payments: contractPaymentsApi,
  masterControl: masterControlApi,
  statistics: statisticsApi,
  documentLinks: documentLinksApi,
  documentProjectLinks: documentProjectLinksApi,
  projectLinks: projectLinksApi,
  attachments: dispatchAttachmentsApi,
};

export default taoyuanDispatchApi;
