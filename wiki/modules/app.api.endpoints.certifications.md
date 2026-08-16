---
title: app.api.endpoints.certifications
kg_entity_id: 10807
type: module
module_lines: 451
module_relations: 21
file_path: /app/app/api/endpoints/certifications.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.certifications

## 概述
此模組提供了證照管理的 API 端點，支援承辦同仁證照的 CRUD（Create, Read, Update, Delete）操作。所有端點均使用 POST 方法以提高安全性。

## 主要類別
- 無

## 公開函數
1. `create_certification`
2. `get_user_certifications`
3. `get_certification_detail`
4. `update_certification`
5. `delete_certification`
6. `get_certification_stats`
7. `calculate_checksum`
8. `get_cert_upload_path`
9. `upload_certification_attachment`
10. `download_certification_attachment`

## 依賴關係
- `app.api.response_helper`
- `app.core.config`
- `app.core.dependencies`
- `app.db.database`
- `app.extended.models`
- `app.repositories`
- `app.schemas.certification`

### 記錄變更
- **2026-01-26**: 新增附件上傳端點 `/cert_id/upload-attachment`。
- **2026-02-21**: 遷移至 `StaffCertificationRepository` + `UserRepository` (版本 v1.59.0)。
```

此 Markdown 文檔概括了模組 `app.api.endpoints.certifications` 的主要信息，包括概述、公開函數和依賴關係。
