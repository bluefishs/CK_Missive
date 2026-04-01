/**
 * 桃園查估派工管理端點
 */

/** 桃園派工管理 API 端點 */
export const TAOYUAN_DISPATCH_ENDPOINTS = {
  // 轄管工程清單
  /** 工程列表 POST /taoyuan-dispatch/projects/list */
  PROJECTS_LIST: '/taoyuan-dispatch/projects/list',
  /** 建立工程 POST /taoyuan-dispatch/projects/create */
  PROJECTS_CREATE: '/taoyuan-dispatch/projects/create',
  /** 工程詳情 POST /taoyuan-dispatch/projects/:id/detail */
  PROJECTS_DETAIL: (id: number) => `/taoyuan-dispatch/projects/${id}/detail`,
  /** 更新工程 POST /taoyuan-dispatch/projects/:id/update */
  PROJECTS_UPDATE: (id: number) => `/taoyuan-dispatch/projects/${id}/update`,
  /** 刪除工程 POST /taoyuan-dispatch/projects/:id/delete */
  PROJECTS_DELETE: (id: number) => `/taoyuan-dispatch/projects/${id}/delete`,
  /** Excel 匯入工程 POST /taoyuan-dispatch/projects/import */
  PROJECTS_IMPORT: '/taoyuan-dispatch/projects/import',
  /** 下載匯入範本 POST /taoyuan-dispatch/projects/import-template */
  PROJECTS_IMPORT_TEMPLATE: '/taoyuan-dispatch/projects/import-template',

  // 承攬案件切換
  /** 桃園派工承攬案件列表 POST /taoyuan-dispatch/dispatch/contract-projects */
  DISPATCH_CONTRACT_PROJECTS: '/taoyuan-dispatch/dispatch/contract-projects',

  // 派工紀錄
  /** 派工單列表 POST /taoyuan-dispatch/dispatch/list */
  DISPATCH_ORDERS_LIST: '/taoyuan-dispatch/dispatch/list',
  /** 取得下一個派工單號 POST /taoyuan-dispatch/dispatch/next-dispatch-no */
  DISPATCH_NEXT_NO: '/taoyuan-dispatch/dispatch/next-dispatch-no',
  /** 建立派工單 POST /taoyuan-dispatch/dispatch/create */
  DISPATCH_ORDERS_CREATE: '/taoyuan-dispatch/dispatch/create',
  /** Excel 匯入派工紀錄 POST /taoyuan-dispatch/dispatch/import */
  DISPATCH_IMPORT: '/taoyuan-dispatch/dispatch/import',
  /** 下載派工紀錄匯入範本 POST /taoyuan-dispatch/dispatch/import-template */
  DISPATCH_IMPORT_TEMPLATE: '/taoyuan-dispatch/dispatch/import-template',
  /** 派工單詳情 POST /taoyuan-dispatch/dispatch/:id/detail */
  DISPATCH_ORDERS_DETAIL: (id: number) => `/taoyuan-dispatch/dispatch/${id}/detail`,
  /** 更新派工單 POST /taoyuan-dispatch/dispatch/:id/update */
  DISPATCH_ORDERS_UPDATE: (id: number) => `/taoyuan-dispatch/dispatch/${id}/update`,
  /** 刪除派工單 POST /taoyuan-dispatch/dispatch/:id/delete */
  DISPATCH_ORDERS_DELETE: (id: number) => `/taoyuan-dispatch/dispatch/${id}/delete`,
  /** 批量設定結案批次 POST /taoyuan-dispatch/dispatch/batch-set-batch */
  DISPATCH_BATCH_SET_BATCH: '/taoyuan-dispatch/dispatch/batch-set-batch',

  // 派工單公文關聯
  /** 新增公文關聯 POST /taoyuan-dispatch/dispatch/:id/link-document */
  DISPATCH_LINK_DOCUMENT: (id: number) => `/taoyuan-dispatch/dispatch/${id}/link-document`,
  /** 移除派工單公文關聯 POST /taoyuan-dispatch/dispatch/:id/unlink-document/:linkId */
  DISPATCH_UNLINK_DOCUMENT: (id: number, linkId: number) => `/taoyuan-dispatch/dispatch/${id}/unlink-document/${linkId}`,
  /** 取得派工單公文 POST /taoyuan-dispatch/dispatch/:id/documents */
  DISPATCH_DOCUMENTS: (id: number) => `/taoyuan-dispatch/dispatch/${id}/documents`,
  /** 搜尋可關聯的桃園派工公文 POST /taoyuan-dispatch/dispatch/search-linkable-documents */
  DISPATCH_SEARCH_LINKABLE_DOCUMENTS: '/taoyuan-dispatch/dispatch/search-linkable-documents',
  /** 知識圖譜實體配對建議 POST /taoyuan-dispatch/dispatch/:id/entity-similarity */
  DISPATCH_ENTITY_SIMILARITY: (id: number) => `/taoyuan-dispatch/dispatch/${id}/entity-similarity`,
  /** NER 驅動公文對照建議 POST /taoyuan-dispatch/dispatch/:id/correspondence-suggestions */
  DISPATCH_CORRESPONDENCE_SUGGESTIONS: (id: number) => `/taoyuan-dispatch/dispatch/${id}/correspondence-suggestions`,
  /** 確認公文對照配對（回饋圖譜） POST /taoyuan-dispatch/dispatch/:id/confirm-correspondence */
  DISPATCH_CONFIRM_CORRESPONDENCE: (id: number) => `/taoyuan-dispatch/dispatch/${id}/confirm-correspondence`,

  // 匯出
  /** 派工總表 Excel 匯出 POST /taoyuan-dispatch/dispatch/export/excel */
  DISPATCH_EXPORT_EXCEL: '/taoyuan-dispatch/dispatch/export/excel',
  /** 非同步匯出 POST /taoyuan-dispatch/dispatch/export/excel/async */
  DISPATCH_EXPORT_ASYNC: '/taoyuan-dispatch/dispatch/export/excel/async',
  /** 匯出進度 POST /taoyuan-dispatch/dispatch/export/excel/progress */
  DISPATCH_EXPORT_PROGRESS: '/taoyuan-dispatch/dispatch/export/excel/progress',
  /** 下載匯出結果 POST /taoyuan-dispatch/dispatch/export/excel/download */
  DISPATCH_EXPORT_DOWNLOAD: '/taoyuan-dispatch/dispatch/export/excel/download',

  // 公文歷程匹配 (對應原始需求欄位 14-17)
  /** 匹配公文歷程 POST /taoyuan-dispatch/dispatch/match-documents */
  MATCH_DOCUMENTS: '/taoyuan-dispatch/dispatch/match-documents',
  /** 派工單詳情含公文歷程 POST /taoyuan-dispatch/dispatch/:id/detail-with-history */
  DISPATCH_DETAIL_WITH_HISTORY: (id: number) => `/taoyuan-dispatch/dispatch/${id}/detail-with-history`,

  // 以公文為主體的關聯 API
  /** 查詢公文關聯的派工單 POST /taoyuan-dispatch/document/:id/dispatch-links */
  DOCUMENT_DISPATCH_LINKS: (id: number) => `/taoyuan-dispatch/document/${id}/dispatch-links`,
  /** 將公文關聯到派工單 POST /taoyuan-dispatch/document/:id/link-dispatch */
  DOCUMENT_LINK_DISPATCH: (id: number) => `/taoyuan-dispatch/document/${id}/link-dispatch`,
  /** 移除公文與派工的關聯 POST /taoyuan-dispatch/document/:docId/unlink-dispatch/:linkId */
  DOCUMENT_UNLINK_DISPATCH: (docId: number, linkId: number) => `/taoyuan-dispatch/document/${docId}/unlink-dispatch/${linkId}`,
  /** 批次查詢多筆公文的派工關聯 POST /taoyuan-dispatch/documents/batch-dispatch-links */
  DOCUMENTS_BATCH_DISPATCH_LINKS: '/taoyuan-dispatch/documents/batch-dispatch-links',

  // 以工程為主體的關聯 API
  /** 查詢工程關聯的派工單 POST /taoyuan-dispatch/project/:id/dispatch-links */
  PROJECT_DISPATCH_LINKS: (id: number) => `/taoyuan-dispatch/project/${id}/dispatch-links`,
  /** 將工程關聯到派工單 POST /taoyuan-dispatch/project/:id/link-dispatch */
  PROJECT_LINK_DISPATCH: (id: number) => `/taoyuan-dispatch/project/${id}/link-dispatch`,
  /** 移除工程與派工的關聯 POST /taoyuan-dispatch/project/:projId/unlink-dispatch/:linkId */
  PROJECT_UNLINK_DISPATCH: (projId: number, linkId: number) => `/taoyuan-dispatch/project/${projId}/unlink-dispatch/${linkId}`,
  /** 批次查詢多筆工程的派工關聯 POST /taoyuan-dispatch/projects/batch-dispatch-links */
  PROJECTS_BATCH_DISPATCH_LINKS: '/taoyuan-dispatch/projects/batch-dispatch-links',

  // 公文-工程直接關聯 API (不經過派工單)
  /** 查詢公文關聯的工程 POST /taoyuan-dispatch/document/:id/project-links */
  DOCUMENT_PROJECT_LINKS: (id: number) => `/taoyuan-dispatch/document/${id}/project-links`,
  /** 將公文關聯到工程 POST /taoyuan-dispatch/document/:id/link-project */
  DOCUMENT_LINK_PROJECT: (id: number) => `/taoyuan-dispatch/document/${id}/link-project`,
  /** 移除公文與工程的關聯 POST /taoyuan-dispatch/document/:docId/unlink-project/:linkId */
  DOCUMENT_UNLINK_PROJECT: (docId: number, linkId: number) => `/taoyuan-dispatch/document/${docId}/unlink-project/${linkId}`,
  /** 批次查詢多筆公文的工程關聯 POST /taoyuan-dispatch/documents/batch-project-links */
  DOCUMENTS_BATCH_PROJECT_LINKS: '/taoyuan-dispatch/documents/batch-project-links',

  // 契金管控
  /** 契金列表 POST /taoyuan-dispatch/payments/list */
  PAYMENTS_LIST: '/taoyuan-dispatch/payments/list',
  /** 建立契金 POST /taoyuan-dispatch/payments/create */
  PAYMENTS_CREATE: '/taoyuan-dispatch/payments/create',
  /** 更新契金 POST /taoyuan-dispatch/payments/:id/update */
  PAYMENTS_UPDATE: (id: number) => `/taoyuan-dispatch/payments/${id}/update`,
  /** 刪除契金 POST /taoyuan-dispatch/payments/:id/delete */
  PAYMENTS_DELETE: (id: number) => `/taoyuan-dispatch/payments/${id}/delete`,
  /** 契金管控展示 POST /taoyuan-dispatch/payments/control */
  PAYMENTS_CONTROL: '/taoyuan-dispatch/payments/control',

  // 總控表
  /** 總控表查詢 POST /taoyuan-dispatch/master-control */
  MASTER_CONTROL: '/taoyuan-dispatch/master-control',

  // 統計資料
  /** 桃園查估派工統計 POST /taoyuan-dispatch/statistics */
  STATISTICS: '/taoyuan-dispatch/statistics',

  // 派工單附件
  /** 上傳派工單附件 POST /taoyuan-dispatch/dispatch/:id/attachments/upload */
  DISPATCH_ATTACHMENTS_UPLOAD: (id: number) => `/taoyuan-dispatch/dispatch/${id}/attachments/upload`,
  /** 取得派工單附件列表 POST /taoyuan-dispatch/dispatch/:id/attachments/list */
  DISPATCH_ATTACHMENTS_LIST: (id: number) => `/taoyuan-dispatch/dispatch/${id}/attachments/list`,
  /** 下載附件 POST /taoyuan-dispatch/dispatch/attachments/:id/download */
  DISPATCH_ATTACHMENT_DOWNLOAD: (id: number) => `/taoyuan-dispatch/dispatch/attachments/${id}/download`,
  /** 刪除附件 POST /taoyuan-dispatch/dispatch/attachments/:id/delete */
  DISPATCH_ATTACHMENT_DELETE: (id: number) => `/taoyuan-dispatch/dispatch/attachments/${id}/delete`,
  /** 驗證附件完整性 POST /taoyuan-dispatch/dispatch/attachments/:id/verify */
  DISPATCH_ATTACHMENT_VERIFY: (id: number) => `/taoyuan-dispatch/dispatch/attachments/${id}/verify`,

  // 作業歷程
  /** 作業歷程列表（依派工單）POST /taoyuan-dispatch/workflow/list */
  WORKFLOW_LIST: '/taoyuan-dispatch/workflow/list',
  /** 作業歷程列表（依工程）POST /taoyuan-dispatch/workflow/by-project */
  WORKFLOW_BY_PROJECT: '/taoyuan-dispatch/workflow/by-project',
  /** 建立作業紀錄 POST /taoyuan-dispatch/workflow/create */
  WORKFLOW_CREATE: '/taoyuan-dispatch/workflow/create',
  /** 取得作業紀錄 POST /taoyuan-dispatch/workflow/:id */
  WORKFLOW_DETAIL: (id: number) => `/taoyuan-dispatch/workflow/${id}`,
  /** 更新作業紀錄 POST /taoyuan-dispatch/workflow/:id/update */
  WORKFLOW_UPDATE: (id: number) => `/taoyuan-dispatch/workflow/${id}/update`,
  /** 刪除作業紀錄 POST /taoyuan-dispatch/workflow/:id/delete */
  WORKFLOW_DELETE: (id: number) => `/taoyuan-dispatch/workflow/${id}/delete`,
  /** 批量更新批次歸屬 POST /taoyuan-dispatch/workflow/batch-update */
  WORKFLOW_BATCH_UPDATE: '/taoyuan-dispatch/workflow/batch-update',
  /** 工程歷程總覽 POST /taoyuan-dispatch/workflow/summary/:projectId */
  WORKFLOW_SUMMARY: (projectId: number) => `/taoyuan-dispatch/workflow/summary/${projectId}`,
} as const;
