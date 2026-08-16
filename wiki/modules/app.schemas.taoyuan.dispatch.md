---
title: app.schemas.taoyuan.dispatch
kg_entity_id: 12725
type: module
module_lines: 337
module_relations: 33
file_path: /app/app/schemas/taoyuan/dispatch.py
created: 2026-08-03
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.taoyuan.dispatch

## 概述
此 Python 模組包含了與桃園查估派工相關的派工紀錄Schema定義，用於描述和驗證不同類型的派工數據。

## 主要類別
- **DispatchOrderBase**: 基本派工單 Schema。
- **DispatchOrderCreate**: 創建派工單時使用的 Schema。
- **DispatchOrderUpdate**: 更新派工單時使用的 Schema。
- **DispatchWorkTypeItem**: 派工工作項目 Schema。
- **WorkProgressSummary**: 工作進度摘要 Schema。
- **DispatchOrder**: 完整的派工單 Schema。
- **BatchSetRequest**: 批量設置請求 Schema。
- **BatchSetResponse**: 批量設置回應 Schema。
- **BatchRelinkRequest**: 批量重新連接請求 Schema。
- **BatchRelinkResult**: 批量重新連接結果 Schema。
- **DispatchOrderListQuery**: 派工單列表查詢 Schema。
- **DispatchOrderListResponse**: 派工單列表回應 Schema。
- **DocumentHistoryItem**: 文件歷史項目 Schema。
- **DocumentHistoryMatchRequest**: 文件歷史匹配請求 Schema。
- **DocumentHistoryResponse**: 文件歷史回應 Schema。
- **DispatchOrderWithHistory**: 包含歷史記錄的派工單 Schema。
- **DispatchAttachmentBase**: 派工附件基本 Schema。
- **DispatchAttachment**: 派工附件 Schema。
- **DispatchSuccessResponse**: 派工成功回應 Schema。
- **ContractProjectListResponse**: 合約項目列表回應 Schema。
- **NextDispatchNoResponse**: 下一個派工單號回應 Schema。
- **EnrichFromExcelResponse**: 从 Excel 富化回應 Schema。
- **DocumentStubsResponse**: 文件草稿回應 Schema。
- **AsyncExportResponse**: 异步导出回應 Schema。
- **ExportProgressResponse**: 导出进度回應 Schema。
- **DispatchDetailWithHistoryResponse**: 包含歷史記錄的派工詳情回應 Schema。
- **DispatchAttachmentListResponse**: 派工附件列表回應 Schema。
- **DispatchAttachmentUploadResult**: 上传派工附件結果 Schema。
- **DispatchAttachmentDeleteResult**: 删除派工附件結果 Schema。
- **DispatchAttachmentVerifyResult**: 验证派工附件结果 Schema。
