"""
公文匯出 API 端點

包含：CSV 匯出、Excel 匯出

@version 4.0.0
@date 2026-01-28
"""
from datetime import datetime
from urllib.parse import quote
from fastapi import APIRouter, Body, HTTPException, Request
from starlette.responses import Response
from fastapi.responses import StreamingResponse

from app.core.rate_limiter import limiter
from .common import (
    logger, Depends,
    DocumentExportQuery, ExcelExportRequest,
    DocumentExportService, get_export_service,
)

router = APIRouter()


# ============================================================================
# 公文匯出 API
# ============================================================================

@router.post("/export", summary="匯出公文資料")
@limiter.limit("10/minute")
async def export_documents(
    request: Request,
    response: Response,
    query: DocumentExportQuery = Body(...),
    service: DocumentExportService = Depends(get_export_service)
):
    """
    匯出公文資料為 CSV 格式

    支援功能:
    - 依指定 ID 列表匯出
    - 依類別/年度篩選後匯出
    - 若未指定條件則匯出全部
    """
    try:
        csv_bytes = await service.export_to_csv(
            document_ids=query.document_ids,
            category=query.category,
            year=query.year
        )

        filename = f"documents_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([csv_bytes]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"匯出公文失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"匯出公文失敗: {str(e)}")


# ============================================================================
# Excel 匯出端點
# ============================================================================

@router.post("/export/excel", summary="匯出公文為 Excel")
@limiter.limit("10/minute")
async def export_documents_excel(
    http_request: Request,
    response: Response,
    request: ExcelExportRequest = Body(default=ExcelExportRequest()),
    service: DocumentExportService = Depends(get_export_service)
):
    """
    匯出公文資料為 Excel 格式 (.xlsx)

    檔名格式: CK公文YYYYMMDD.xlsx

    支援功能:
    - 依指定 ID 列表匯出
    - 依類別/年度/關鍵字/狀態篩選後匯出
    - 若未指定條件則匯出全部（無筆數限制）

    流水號說明:
    - S 開頭: 發文 (Send)
    - R 開頭: 收文 (Receive)
    """
    try:
        excel_bytes = await service.export_to_excel(
            document_ids=request.document_ids,
            category=request.category,
            year=request.year,
            status=request.status,
            keyword=request.keyword,
            contract_case=request.contract_case,
            sender=request.sender,
            receiver=request.receiver,
        )

        # 產生檔名: 乾坤測繪公文總表YYYYMMDD.xlsx
        date_str = datetime.now().strftime('%Y%m%d')
        filename_cn = f"乾坤測繪公文總表{date_str}.xlsx"
        filename_encoded = quote(filename_cn)

        return StreamingResponse(
            iter([excel_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache, no-store, must-revalidate",
            }
        )

    except ValueError as e:
        # Service 層拋出的業務錯誤
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"匯出 Excel 失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"匯出 Excel 失敗: {str(e)}")
