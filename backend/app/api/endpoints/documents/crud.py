"""
公文 CRUD API 端點

包含：詳情查詢、建立、更新
刪除端點已遷移至 delete.py

@version 3.2.0
@date 2026-03-12

變更紀錄:
- v3.2.0: 新增公文建立/更新後自動觸發背景 NER 提取
- v3.1.0: 業務邏輯下沉至 DocumentService (get_document_with_extra_info)
- v3.0.0: 初始模組化版本
"""
import asyncio
from fastapi import APIRouter, Body, Request
from starlette.responses import Response
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core.rate_limiter import limiter

from .common import (
    logger, Depends,
    OfficialDocument, User,
    DocumentResponse, DocumentCreateRequest, DocumentUpdateRequest,
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
        # 注意：generate_auto_serial 需要 category（收文/發文），不是 doc_type（函/書函/公告等）
        if not filtered_data.get('auto_serial'):
            category = filtered_data.get('category', '收文')
            filtered_data['auto_serial'] = await service.generate_auto_serial(category)

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

        # 日期欄位變更時同步更新行事曆事件
        date_changed = any(k in changes for k in ('doc_date', 'receive_date', 'send_date'))
        subject_changed = 'subject' in changes
        if date_changed or subject_changed:
            try:
                from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder
                builder = CalendarEventAutoBuilder(db)
                updated_count = await builder.update_event_for_document(document)
                if updated_count:
                    await db.commit()
                    logger.info(f"公文 {document_id}: 同步更新 {updated_count} 個行事曆事件")
            except Exception as cal_err:
                logger.warning(f"行事曆同步失敗 (不影響主流程): {cal_err}")

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
