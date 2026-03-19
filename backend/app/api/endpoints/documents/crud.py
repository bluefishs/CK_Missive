"""
公文 CRUD API 端點

包含：詳情查詢、建立、更新、刪除

@version 3.2.0
@date 2026-03-12

變更紀錄:
- v3.2.0: 新增公文建立/更新後自動觸發背景 NER 提取
- v3.1.0: 業務邏輯下沉至 DocumentService (get_document_with_extra_info)
- v3.0.0: 初始模組化版本
"""
import os
import asyncio
from fastapi import APIRouter, Body, Request
from starlette.responses import Response
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.rate_limiter import limiter

from .common import (
    logger, Depends,
    OfficialDocument, DocumentAttachment, User,
    DocumentResponse, DocumentCreateRequest, DocumentUpdateRequest,
    DeleteResponse,
    NotFoundException, ForbiddenException,
    RLSFilter, DocumentUpdateGuard, NotificationService, CRITICAL_FIELDS,
    require_auth, require_permission, parse_date_string,
    DocumentService, get_document_service,
)

router = APIRouter()


async def _trigger_ner_background(doc_id: int, force: bool = False) -> None:
    """背景觸發 NER 實體提取（不阻塞主回應）"""
    try:
        from app.db.database import AsyncSessionLocal
        from app.services.ai.entity_extraction_service import extract_entities_for_document

        async with AsyncSessionLocal() as db:
            result = await extract_entities_for_document(db, doc_id, force=force, commit=True)
            if not result.get("skipped"):
                logger.info(
                    f"[NER] 背景提取完成 doc_id={doc_id}: "
                    f"{result.get('entities_count', 0)} 實體, "
                    f"{result.get('relations_count', 0)} 關係"
                )
    except Exception as e:
        logger.warning(f"[NER] 背景提取失敗 doc_id={doc_id}: {e}")


# ============================================================================
# 公文 CRUD API（POST-only 資安機制）
# ============================================================================

@router.post(
    "/{document_id}/detail",
    response_model=DocumentResponse,
    summary="取得公文詳情"
)
@limiter.limit("30/minute")
async def get_document_detail(
    document_id: int,
    request: Request,
    response: Response,
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(require_auth())
):
    """
    取得單一公文詳情（POST-only 資安機制，含擴充欄位與權限檢查）

    業務邏輯已下沉至 DocumentService.get_document_with_extra_info()
    """
    try:
        # 使用 DocumentService 取得公文及額外資訊
        doc_dict = await service.get_document_with_extra_info(document_id)
        db = service.db

        if not doc_dict:
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
            contract_project_id = doc_dict.get('contract_project_id')
            if contract_project_id:
                has_access = await RLSFilter.check_user_project_access(
                    db, current_user.id, contract_project_id
                )
                if not has_access:
                    raise ForbiddenException("您沒有權限查看此公文")
            # 無專案關聯的公文視為公開，不需額外檢查

        return DocumentResponse.model_validate(doc_dict)
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"取得公文詳情失敗: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "ERR_INTERNAL",
                    "message": "取得公文詳情失敗，請稍後再試"
                }
            }
        )


@router.post(
    "/create",
    response_model=DocumentResponse,
    summary="建立公文"
)
@limiter.limit("30/minute")
async def create_document(
    request: Request,
    response: Response,
    data: DocumentCreateRequest = Body(...),
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(require_permission("documents:create"))
):
    """
    建立新公文（POST-only 資安機制，含使用者追蹤）

    🔒 權限要求：documents:create
    """
    try:
        db = service.db
        create_data = data.model_dump(exclude_unset=True)
        logger.debug(f"[CREATE] create_data date fields: doc_date={create_data.get('doc_date')!r}, receive_date={create_data.get('receive_date')!r}, send_date={create_data.get('send_date')!r}")

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

        # 自動產生 auto_serial（若未提供），委派給 Service 層
        if not filtered_data.get('auto_serial'):
            doc_type = filtered_data.get('doc_type', '收文')
            filtered_data['auto_serial'] = await service.generate_auto_serial(doc_type)

        # 日期欄位需要特別處理：字串轉換為 date 物件
        date_fields = ['doc_date', 'receive_date', 'send_date']
        for field in date_fields:
            if field in filtered_data and isinstance(filtered_data[field], str):
                filtered_data[field] = parse_date_string(filtered_data[field])

        logger.debug(f"[CREATE] filtered_data date fields: doc_date={filtered_data.get('doc_date')!r}, receive_date={filtered_data.get('receive_date')!r}, send_date={filtered_data.get('send_date')!r}")

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

        # 背景觸發 NER 實體提取（非阻塞）
        asyncio.create_task(_trigger_ner_background(document.id))

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
@limiter.limit("30/minute")
async def update_document(
    document_id: int,
    request: Request,
    response: Response,
    data: DocumentUpdateRequest = Body(...),
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(require_permission("documents:edit"))
):
    """
    更新公文（POST-only 資安機制，含審計日誌與使用者追蹤）

    🔒 權限要求：documents:edit
    🔒 行級別權限：一般使用者只能編輯關聯專案的公文
    """
    try:
        db = service.db
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
        # 排除 deferred 欄位（如 embedding）以避免 async lazy-load 觸發 MissingGreenlet
        guard = DocumentUpdateGuard(db, document_id)
        _EXCLUDED_AUDIT_COLUMNS = {'embedding'}
        original_data = {
            col.name: getattr(document, col.name)
            for col in document.__table__.columns
            if col.name not in _EXCLUDED_AUDIT_COLUMNS
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
            # 處理日期欄位（需解析字串 → date 物件）
            if key in date_fields:
                if value is not None:
                    parsed_date = parse_date_string(value) if isinstance(value, str) else value
                    setattr(document, key, parsed_date)
                    processed_data[key] = parsed_date
                else:
                    # 允許清除日期欄位（設為 None）
                    setattr(document, key, None)
                    processed_data[key] = None
            else:
                # 非日期欄位：直接設值（包含 None 清除）
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

        # AI 分析過期標記（輕量 UPDATE，僅影響內容相關欄位變更時）
        content_fields = {'subject', 'content', 'sender'}
        if changes and content_fields & set(changes.keys()):
            try:
                from app.repositories.ai_analysis_repository import AIAnalysisRepository
                ai_repo = AIAnalysisRepository(db)
                await ai_repo.mark_stale(document_id)
                logger.debug(f"已標記公文 {document_id} 的 AI 分析為過期")
            except Exception as e:
                logger.warning(f"標記 AI 分析過期失敗: {e}")

            # 背景重新觸發 NER 提取（force=True 覆蓋舊結果）
            asyncio.create_task(_trigger_ner_background(document_id, force=True))

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
@limiter.limit("30/minute")
async def delete_document(
    document_id: int,
    request: Request,
    response: Response,
    service: DocumentService = Depends(get_document_service),
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
        db = service.db
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
                logger.error(f"刪除附件檔案失敗: {file_path}: {e}")
                file_errors.append(f"{file_path}: 刪除失敗")
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
        # 檢查是否為外鍵約束違反（公文被其他資料引用）
        error_msg = str(e).lower()
        if "foreign key" in error_msg or "integrity" in error_msg or "violates" in error_msg:
            logger.warning(f"刪除公文 {document_id} 失敗 (關聯約束): {e}")
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "error": {
                        "code": "ERR_CONSTRAINT_VIOLATION",
                        "message": "此公文被其他資料引用（如派工單），無法直接刪除。請先解除關聯後再試。"
                    }
                }
            )
        logger.error(f"刪除公文失敗: {e}", exc_info=True)
        raise
