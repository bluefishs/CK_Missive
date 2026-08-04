---
title: app.schemas.taoyuan.dispatch
kg_entity_id: 12725
type: module
module_lines: 330
module_relations: 33
file_path: /app/app/schemas/taoyuan/dispatch.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.taoyuan.dispatch

## 概述
此 Python 模組定義了與桃園查估派工相關的各種派工紀錄（Dispatch Order）及其相關操作的 Schema。這些 Schema 主要被用於數據模型和API接口之間的數據轉換。

## 主要類別
- **DispatchOrderBase**: 基本的派工單模式。
- **DispatchOrderCreate**: 用于創建新派工單的模式。
- **DispatchOrderUpdate**: 更新現有派工單的模式。
- **DispatchWorkTypeItem**: 派工工作項目模式。
- **WorkProgressSummary**: 工作進度摘要模式。
- **DispatchOrder**: 結合了基本和更新模式的完整派工單模式。
- **BatchSetRequest**: 批量設置請求模式。
- **BatchSetResponse**: 批量設置響應模式。
- **BatchRelinkRequest**: 批量重新連接請求模式。
- **BatchRelinkResult**: 批量重新連接結果模式。
- **DispatchOrderListQuery**: 派工單列表查詢模式。
- **DispatchOrderListResponse**: 派工單列表響應模式。
- **DocumentHistoryItem**: 文件歷史項目模式。
- **DocumentHistoryMatchRequest**: 文件歷史匹配請求模式。
- **DocumentHistoryResponse**: 文件歷史響應模式。
- **DispatchOrderWithHistory**: 包含歷史記錄的派工單模式。
- **DispatchAttachmentBase**: 附件基本模式。
- **DispatchAttachment**: 附件模式。
- **DispatchSuccessResponse**: 派工成功響應模式。
- **ContractProjectListResponse**: 合同項目列表響應模式。
- **NextDispatchNoResponse**: 下一個派工單號響應模式。
- **EnrichFromExcelResponse**: 實體從 Excel 文件豐富的響應模式。
- **DocumentStubsResponse**: 文件草稿響應模式。
- **AsyncExportResponse**: 异步导出响应模式。
- **ExportProgressResponse**: 导出进度响应模式。
- **DispatchDetailWithHistoryResponse**: 包含歷史記錄的派工詳情響應模式。
- **DispatchAttachmentListResponse**: 附件列表響應模式。
- **DispatchAttachmentUploadResult**: 附件上传结果模式。
- **DispatchAttachmentDeleteResult**: 附件删除结果模式。
- **DispatchAttachmentVerifyResult
