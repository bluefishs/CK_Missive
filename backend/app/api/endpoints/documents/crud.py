"""
公文 CRUD API 端點

包含：詳情查詢、建立、更新、刪除

@version 3.0.0
@date 2026-01-18
"""
import os
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from sqlalchemy import select, func

from .common import (
    logger, Depends, AsyncSession, get_async_db,
    OfficialDocument, ContractProject, GovernmentAgency, DocumentAttachment, User,
    DocumentResponse, DocumentCreateRequest, DocumentUpdateRequest,
    DeleteResponse, PaginationMeta,
    NotFoundException, ForbiddenException,
    RLSFilter, DocumentUpdateGuard, NotificationService, CRITICAL_FIELDS,
    require_auth, require_permission, parse_date_string,
)

router = APIRouter()


# ============================================================================
# 公文 CRUD API（POST-only 資安機制）
# ============================================================================

@router.post(
    "/{document_id}/detail",
    response_model=DocumentResponse,
    summary="取得公文詳情"
)
async def get_document_detail(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """取得單一公文詳情（POST-only 資安機制，含擴充欄位與權限檢查）"""
    try:
        query = select(OfficialDocument).where(OfficialDocument.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": {
                        "code": "ERR_NOT_FOUND",
                        "message": f"公文 (ID: {document_id}) 不存在"
                    }
                }
            )

        # 🔒 行級別權限檢查 (RLS) - 使用統一 RLSFilter
        if not current_user.is_admin and not current_user.is_superuser:
            if document.contract_project_id:
                has_access = await RLSFilter.check_user_project_access(
                    db, current_user.id, document.contract_project_id
                )
                if not has_access:
                    raise ForbiddenException("您沒有權限查看此公文")
            # 無專案關聯的公文視為公開，不需額外檢查

        # 準備擴充欄位
        doc_dict = {k: v for k, v in document.__dict__.items() if not k.startswith('_')}

        # 查詢承攬案件名稱
        if document.contract_project_id:
            project_query = select(ContractProject.project_name).where(
                ContractProject.id == document.contract_project_id
            )
            project_result = await db.execute(project_query)
            doc_dict['contract_project_name'] = project_result.scalar()

        # 查詢機關名稱（2026-01-08 新增）
        if document.sender_agency_id:
            agency_query = select(GovernmentAgency.agency_name).where(
                GovernmentAgency.id == document.sender_agency_id
            )
            agency_result = await db.execute(agency_query)
            doc_dict['sender_agency_name'] = agency_result.scalar()

        if document.receiver_agency_id:
            agency_query = select(GovernmentAgency.agency_name).where(
                GovernmentAgency.id == document.receiver_agency_id
            )
            agency_result = await db.execute(agency_query)
            doc_dict['receiver_agency_name'] = agency_result.scalar()

        # 查詢附件數量
        attachment_count_query = select(func.count(DocumentAttachment.id)).where(
            DocumentAttachment.document_id == document_id
        )
        attachment_result = await db.execute(attachment_count_query)
        doc_dict['attachment_count'] = attachment_result.scalar() or 0

        return DocumentResponse.model_validate(doc_dict)
    except Exception as e:
        logger.error(f"取得公文詳情失敗: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "ERR_INTERNAL",
                    "message": f"取得公文詳情失敗: {str(e)}"
                }
            }
        )


@router.post(
    "/create",
    response_model=DocumentResponse,
    summary="建立公文"
)
async def create_document(
    data: DocumentCreateRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("documents:create"))
):
    """
    建立新公文（POST-only 資安機制，含使用者追蹤）

    🔒 權限要求：documents:create
    """
    try:
        create_data = data.model_dump(exclude_unset=True)

        # OfficialDocument 模型的有效欄位（與資料庫 schema 對齊）
        valid_model_fields = {
            'auto_serial', 'doc_number', 'doc_type', 'subject', 'sender', 'receiver',
            'doc_date', 'receive_date', 'send_date', 'status', 'category',
            'delivery_method', 'has_attachment', 'contract_project_id',
            'sender_agency_id', 'receiver_agency_id', 'title', 'cloud_file_link',
            'dispatch_format', 'assignee', 'notes', 'ck_note', 'content'
        }

        # 過濾掉不存在於模型的欄位（避免 TypeError）
        filtered_data = {k: v for k, v in create_data.items() if k in valid_model_fields}

        # 自動產生 auto_serial（若未提供）
        if not filtered_data.get('auto_serial'):
            doc_type = filtered_data.get('doc_type', '收文')
            prefix = 'R' if doc_type == '收文' else 'S'
            # 查詢當前最大流水號
            result = await db.execute(
                select(func.max(OfficialDocument.auto_serial)).where(
                    OfficialDocument.auto_serial.like(f'{prefix}%')
                )
            )
            max_serial = result.scalar_one_or_none()
            if max_serial:
                try:
                    num = int(max_serial[1:]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            filtered_data['auto_serial'] = f'{prefix}{num:04d}'

        # 日期欄位需要特別處理：字串轉換為 date 物件
        date_fields = ['doc_date', 'receive_date', 'send_date']
        for field in date_fields:
            if field in filtered_data and isinstance(filtered_data[field], str):
                filtered_data[field] = parse_date_string(filtered_data[field])

        document = OfficialDocument(**filtered_data)
        db.add(document)
        await db.commit()
        await db.refresh(document)

        # 審計日誌（使用 AuditService，自動使用獨立 session，不會污染主交易）
        user_id = current_user.id if current_user else None
        user_name = current_user.username if current_user else "Anonymous"
        logger.info(f"公文 {document.id} 建立 by {user_name}")

        from app.services.audit_service import AuditService
        await AuditService.log_document_change(
            document_id=document.id,
            action="CREATE",
            changes={"created": filtered_data},
            user_id=user_id,
            user_name=user_name,
            source="API"
        )

        return DocumentResponse.model_validate(document)
    except Exception as e:
        await db.rollback()
        logger.error(f"建立公文失敗: {e}", exc_info=True)
        raise


@router.post(
    "/{document_id}/update",
    response_model=DocumentResponse,
    summary="更新公文"
)
async def update_document(
    document_id: int,
    data: DocumentUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("documents:edit"))
):
    """
    更新公文（POST-only 資安機制，含審計日誌與使用者追蹤）

    🔒 權限要求：documents:edit
    🔒 行級別權限：一般使用者只能編輯關聯專案的公文
    """
    try:
        logger.info(f"[更新公文] 開始更新公文 ID: {document_id}")
        logger.debug(f"[更新公文] 收到資料: {data.model_dump()}")

        query = select(OfficialDocument).where(OfficialDocument.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundException(resource="公文", resource_id=document_id)

        # 🔒 行級別權限檢查 (RLS) - 使用統一 RLSFilter
        if not current_user.is_admin and not current_user.is_superuser:
            if document.contract_project_id:
                has_access = await RLSFilter.check_user_project_access(
                    db, current_user.id, document.contract_project_id
                )
                if not has_access:
                    raise ForbiddenException("您沒有權限編輯此公文")

        # 初始化審計保護器，記錄原始資料
        guard = DocumentUpdateGuard(db, document_id)
        original_data = {
            col.name: getattr(document, col.name)
            for col in document.__table__.columns
        }

        update_data = data.model_dump(exclude_unset=True)
        logger.debug(f"[更新公文] 過濾前 update_data: {update_data}")

        # OfficialDocument 模型的有效欄位（與資料庫 schema 對齊）
        valid_model_fields = {
            'auto_serial', 'doc_number', 'doc_type', 'subject', 'sender', 'receiver',
            'doc_date', 'receive_date', 'send_date', 'status', 'category',
            'delivery_method', 'has_attachment', 'contract_project_id',
            'sender_agency_id', 'receiver_agency_id', 'title', 'cloud_file_link',
            'dispatch_format', 'assignee', 'notes', 'ck_note', 'content'
        }

        # 過濾掉不存在於模型的欄位
        update_data = {k: v for k, v in update_data.items() if k in valid_model_fields}
        logger.debug(f"[更新公文] 過濾後 update_data: {update_data}")

        # 日期欄位需要特別處理：字串轉換為 date 物件
        date_fields = ['doc_date', 'receive_date', 'send_date']
        processed_data = {}

        for key, value in update_data.items():
            if value is not None:
                # 處理日期欄位
                if key in date_fields:
                    parsed_date = parse_date_string(value) if isinstance(value, str) else value
                    setattr(document, key, parsed_date)
                    processed_data[key] = parsed_date
                else:
                    setattr(document, key, value)
                    processed_data[key] = value

        # 記錄審計日誌（變更前後比對）
        changes = {}
        for key, new_value in processed_data.items():
            old_value = original_data.get(key)
            if old_value != new_value:
                changes[key] = {"old": str(old_value), "new": str(new_value)}

        # 先提交主要更新操作
        await db.commit()
        await db.refresh(document)

        # 審計日誌和通知（使用統一服務，自動管理獨立 session）
        if changes:
            user_id = current_user.id if current_user else None
            user_name = current_user.username if current_user else "Anonymous"
            logger.info(f"公文 {document_id} 更新 by {user_name}: {list(changes.keys())}")

            # 使用 AuditService（自動使用獨立 session，不會污染主交易）
            from app.services.audit_service import AuditService
            await AuditService.log_document_change(
                document_id=document_id,
                action="UPDATE",
                changes=changes,
                user_id=user_id,
                user_name=user_name,
                source="API"
            )

            # 關鍵欄位變更通知（使用 safe_* 方法，自動使用獨立 session）
            critical_field_names = CRITICAL_FIELDS.get("documents", {})
            for field_key, change_info in changes.items():
                if field_key in critical_field_names:
                    await NotificationService.safe_notify_critical_change(
                        document_id=document_id,
                        field=field_key,
                        old_value=change_info.get("old", ""),
                        new_value=change_info.get("new", ""),
                        user_id=user_id,
                        user_name=user_name,
                        table_name="documents"
                    )

        return DocumentResponse.model_validate(document)
    except NotFoundException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新公文失敗: {e}", exc_info=True)
        raise


@router.post(
    "/{document_id}/delete",
    response_model=DeleteResponse,
    summary="刪除公文"
)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission("documents:delete"))
):
    """
    刪除公文（POST-only 資安機制）

    🔒 權限要求：documents:delete
    🔒 行級別權限：一般使用者只能刪除關聯專案的公文

    同步刪除：
    - 公文資料庫記錄
    - 附件資料庫記錄（CASCADE）
    - 實體附件檔案
    - 公文附件資料夾（若為空）
    """
    try:
        # 1. 查詢公文是否存在
        query = select(OfficialDocument).where(OfficialDocument.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundException(resource="公文", resource_id=document_id)

        # 🔒 行級別權限檢查 (RLS) - 使用統一 RLSFilter
        if not current_user.is_admin and not current_user.is_superuser:
            if document.contract_project_id:
                has_access = await RLSFilter.check_user_project_access(
                    db, current_user.id, document.contract_project_id
                )
                if not has_access:
                    raise ForbiddenException("您沒有權限刪除此公文")

        # 2. 查詢關聯的附件記錄（在刪除前取得檔案路徑）
        attachment_query = select(DocumentAttachment).where(
            DocumentAttachment.document_id == document_id
        )
        attachment_result = await db.execute(attachment_query)
        attachments = attachment_result.scalars().all()

        # 3. 收集需要刪除的檔案路徑和資料夾
        file_paths_to_delete = []
        folders_to_check = set()

        for attachment in attachments:
            if attachment.file_path:
                file_paths_to_delete.append(attachment.file_path)
                # 記錄父資料夾路徑（doc_{id} 層級）
                parent_folder = os.path.dirname(attachment.file_path)
                if parent_folder:
                    folders_to_check.add(parent_folder)

        # 4. 記錄公文資訊（在刪除前保存，用於後續審計日誌）
        user_id = current_user.id
        user_name = current_user.username
        doc_number = document.doc_number or ""
        subject = document.subject or ""
        attachments_count = len(attachments)
        logger.info(f"公文 {document_id} 刪除 by {user_name}")

        # 5. 刪除資料庫記錄（CASCADE 會自動刪除 document_attachments）
        await db.delete(document)
        await db.commit()

        # 6. 審計日誌和通知（使用統一服務，自動管理獨立 session）
        from app.services.audit_service import AuditService
        await AuditService.log_document_change(
            document_id=document_id,
            action="DELETE",
            changes={
                "deleted": {
                    "doc_number": doc_number,
                    "subject": subject,
                    "attachments_count": attachments_count
                }
            },
            user_id=user_id,
            user_name=user_name,
            source="API"
        )

        # 公文刪除通知（使用 safe_* 方法，自動使用獨立 session）
        await NotificationService.safe_notify_document_deleted(
            document_id=document_id,
            doc_number=doc_number,
            subject=subject,
            user_id=user_id,
            user_name=user_name
        )

        # 7. 刪除實體檔案（在資料庫成功刪除後執行）
        deleted_files = 0
        file_errors = []

        for file_path in file_paths_to_delete:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files += 1
                    logger.info(f"已刪除附件檔案: {file_path}")
            except Exception as e:
                file_errors.append(f"{file_path}: {str(e)}")
                logger.warning(f"刪除附件檔案失敗: {file_path}, 錯誤: {e}")

        # 8. 嘗試刪除空的公文資料夾（doc_{id}）
        deleted_folders = 0
        for folder in folders_to_check:
            try:
                if os.path.exists(folder) and os.path.isdir(folder):
                    # 只刪除空資料夾
                    if not os.listdir(folder):
                        os.rmdir(folder)
                        deleted_folders += 1
                        logger.info(f"已刪除空資料夾: {folder}")
            except Exception as e:
                logger.warning(f"刪除資料夾失敗: {folder}, 錯誤: {e}")

        # 9. 建構回應訊息
        message = f"公文已刪除"
        if deleted_files > 0:
            message += f"，同步刪除 {deleted_files} 個附件檔案"
        if deleted_folders > 0:
            message += f"，清理 {deleted_folders} 個空資料夾"
        if file_errors:
            message += f"（{len(file_errors)} 個檔案刪除失敗）"

        return DeleteResponse(
            success=True,
            message=message,
            deleted_id=document_id
        )
    except NotFoundException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"刪除公文失敗: {e}", exc_info=True)
        raise
