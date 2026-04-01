"""
公文刪除 API 端點

包含端點：
- POST /{document_id}/delete - 刪除公文

拆分自 crud.py (v3.2.0)

@version 1.0.0
@date 2026-03-30
"""
import os
from fastapi import APIRouter, Request
from starlette.responses import Response
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.rate_limiter import limiter

from .common import (
    logger, Depends,
    OfficialDocument, DocumentAttachment, User,
    DeleteResponse,
    NotFoundException, ForbiddenException,
    RLSFilter, NotificationService,
    require_auth, require_permission,
    DocumentService, get_document_service,
)

router = APIRouter()


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

        # 5. 清理衍生資料（NER entities / chunks / AI analyses — 不阻塞刪除）
        from sqlalchemy import text as sql_text
        try:
            for derived_table in [
                "document_entity_mentions",
                "entity_relations",
                "document_entities",
                "document_chunks",
                "document_ai_analyses",
                "graph_ingestion_events",
            ]:
                await db.execute(
                    sql_text(f"DELETE FROM {derived_table} WHERE document_id = :did"),
                    {"did": document_id},
                )
        except Exception as cleanup_err:
            logger.warning(f"衍生資料清理部分失敗 (doc {document_id}): {cleanup_err}")

        # 5b. 取消關聯行事曆事件
        try:
            from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder
            builder = CalendarEventAutoBuilder(db)
            await builder.cancel_events_for_document(document_id)
        except Exception as cal_err:
            logger.warning(f"取消行事曆事件失敗 (不影響刪除): {cal_err}")

        # 6. 刪除資料庫記錄（CASCADE 會自動刪除 document_attachments）
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
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            # 精確判斷：僅 SQLAlchemy IntegrityError 才回傳 409
            logger.warning(
                f"刪除公文 {document_id} 失敗 (IntegrityError): "
                f"type={type(e).__name__}, orig={getattr(e, 'orig', '')}, detail={e}"
            )
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
        logger.error(f"刪除公文失敗: type={type(e).__name__}, {e}", exc_info=True)
        raise
