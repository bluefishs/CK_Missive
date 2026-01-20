"""
公文匯入 API 端點

包含：Excel 預覽、Excel 匯入、下載範本

@version 3.0.0
@date 2026-01-18
"""
from io import BytesIO
from urllib.parse import quote
from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from .common import (
    logger, Depends, AsyncSession, get_async_db,
)

router = APIRouter()


# ============================================================================
# Excel 匯入（手動公文匯入）
# ============================================================================

@router.post("/import/excel/preview", summary="Excel 匯入預覽")
async def preview_excel_import(
    file: UploadFile = File(..., description="要預覽的 Excel 檔案（.xlsx）"),
    preview_rows: int = Query(default=10, ge=1, le=50, description="預覽筆數"),
    check_duplicates: bool = Query(default=True, description="是否檢查資料庫重複"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    預覽 Excel 檔案內容（不執行匯入）

    功能：
    - 顯示前 N 筆資料預覽
    - 驗證欄位格式
    - 標示可能的問題（重複、缺欄位等）
    - 檢查資料庫中已存在的公文字號
    - 統計預計新增/更新筆數

    使用情境：
    - 使用者上傳檔案後，先預覽確認再正式匯入
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供檔案")

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="檔案格式不正確，僅支援 Excel 檔案（.xlsx, .xls）"
        )

    try:
        file_content = await file.read()
        filename = file.filename

        logger.info(f"Excel 匯入預覽: {filename}, 大小: {len(file_content)} bytes")

        from app.services.excel_import_service import ExcelImportService
        import_service = ExcelImportService(db)
        result = await import_service.preview_excel(
            file_content, filename, preview_rows, check_duplicates
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel 預覽失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"預覽失敗: {str(e)}")


@router.post("/import/excel", summary="手動公文匯入（Excel）")
async def import_documents_excel(
    file: UploadFile = File(..., description="要匯入的 Excel 檔案（.xlsx）"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    從 Excel 檔案匯入公文資料（手動公文匯入）

    適用情境：
    - 紙本郵寄紀錄
    - 手動輸入的公文資料
    - 匯出後修改再匯入

    匯入規則：
    - 公文ID 有值：更新現有資料
    - 公文ID 空白：新增資料（自動生成流水號）
    - 必填欄位：公文字號、主旨、類別

    與「電子公文檔匯入」(CSV) 的差異：
    - CSV 匯入：電子公文系統匯出的固定格式
    - Excel 匯入：本系統匯出格式，支援新增/更新
    """

    # 驗證檔案格式
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供檔案")

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="檔案格式不正確，僅支援 Excel 檔案（.xlsx, .xls）"
        )

    try:
        # 讀取檔案內容
        file_content = await file.read()
        filename = file.filename

        logger.info(f"開始 Excel 匯入: {filename}, 大小: {len(file_content)} bytes")

        # 使用 ExcelImportService 處理
        from app.services.excel_import_service import ExcelImportService
        import_service = ExcelImportService(db)
        result = await import_service.import_from_excel(file_content, filename)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel 匯入失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Excel 匯入失敗: {str(e)}")


@router.post("/import/excel/template", summary="下載 Excel 匯入範本")
async def download_excel_template():
    """
    下載 Excel 匯入範本（POST 方法，符合資安規範）

    範本包含：
    - 標題列（欄位名稱）
    - 範例資料（1-2 筆）
    - 欄位說明
    """
    try:
        import pandas as pd

        # 建立範本資料（欄位順序與匯出一致：19 欄）
        template_data = [
            {
                "公文ID": "",  # 空白=新增
                "流水號": "",  # 系統自動生成
                "發文形式": "紙本郵寄",
                "類別": "收文",
                "公文類型": "函",
                "公文字號": "XX字第1140000001號",
                "主旨": "（請輸入公文主旨）",
                "說明": "（請輸入公文內容說明）",
                "公文日期": "2026-01-07",
                "收文日期": "2026-01-07",
                "發文日期": "",
                "發文單位": "○○單位",
                "受文單位": "乾坤測繪科技有限公司",
                "附件紀錄": "",  # 僅供參考，匯入忽略
                "備註": "",
                "狀態": "active",
                "承攬案件": "",
                "建立時間": "",  # 系統自動
                "更新時間": "",  # 系統自動
            }
        ]

        df = pd.DataFrame(template_data)

        # 產生 Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='公文匯入')

            # 調整欄位寬度
            worksheet = writer.sheets['公文匯入']
            for idx, col in enumerate(df.columns):
                col_letter = chr(65 + idx) if idx < 26 else f"A{chr(65 + idx - 26)}"
                worksheet.column_dimensions[col_letter].width = 15

        output.seek(0)

        filename_cn = "公文匯入範本.xlsx"
        filename_encoded = quote(filename_cn)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
            }
        )

    except Exception as e:
        logger.error(f"下載範本失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下載範本失敗: {str(e)}")
