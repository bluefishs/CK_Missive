"""
LINE Image Handler — 圖片訊息處理 (統一辨識器 QR+OCR)

提供：
- LINE Content API 圖片下載
- 統一辨識器 (QR Code + Tesseract OCR) → 發票資訊提取
- 自動建立費用紀錄 (LINE user → system user 對應)

Version: 2.0.0 — 升級為統一 invoice_recognizer
Created: 2026-03-26
Updated: 2026-04-03
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

LINE_DATA_API_BASE = "https://api-data.line.me/v2/bot"
RECEIPT_UPLOAD_DIR = Path(os.getenv("RECEIPT_UPLOAD_DIR", "uploads/receipts"))
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def download_line_content(
    message_id: str, access_token: str,
) -> Optional[Path]:
    """從 LINE Content API 下載檔案"""
    RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{LINE_DATA_API_BASE}/message/{message_id}/content",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                logger.warning("LINE content download failed: %d", resp.status_code)
                return None

            content_type = resp.headers.get("content-type", "image/jpeg")
            ext_map = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
            }
            ext = ext_map.get(content_type, ".jpg")

            filename = f"line_{uuid.uuid4().hex}{ext}"
            file_path = RECEIPT_UPLOAD_DIR / filename

            file_path.write_bytes(resp.content)
            logger.info("LINE image saved: %s (%d bytes)", filename, len(resp.content))
            return file_path

    except Exception as e:
        logger.error("LINE content download error: %s", e)
        return None


async def try_create_expense_from_ocr(
    line_user_id: str,
    ocr_result: "InvoiceOCRResult",
    image_path: str,
) -> Optional[str]:
    """嘗試用 OCR 結果建立費用紀錄 (需要 LINE user → system user 對應)"""
    if not ocr_result.inv_num or not ocr_result.amount:
        return None

    try:
        from app.db.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.extended.models import User

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.line_user_id == line_user_id)
            )
            user = result.scalars().first()

            if not user:
                return "💡 請先在系統中綁定 LINE 帳號，即可自動建立費用紀錄。"

            from app.services.expense_invoice_service import ExpenseInvoiceService

            expense_service = ExpenseInvoiceService(db)
            relative_path = f"receipts/{Path(image_path).name}"

            from app.schemas.erp.expense import ExpenseInvoiceCreate
            from datetime import date as date_cls

            create_data = ExpenseInvoiceCreate(
                inv_num=ocr_result.inv_num,
                amount=ocr_result.amount,
                tax_amount=ocr_result.tax_amount,
                date=ocr_result.date or date_cls.today(),
                buyer_ban=ocr_result.buyer_ban or "",
                seller_ban=ocr_result.seller_ban or "",
                category="其他",
                source="line_upload",
                receipt_image_path=relative_path,
            )

            try:
                expense = await expense_service.create(create_data, user_id=user.id)
                return f"✅ 費用紀錄已建立 (ID: {expense.get('id', '?')})"
            except ValueError as e:
                err_msg = str(e)
                if "已存在" in err_msg:
                    return f"ℹ️ 發票 {ocr_result.inv_num} 已存在系統中。"
                return f"⚠️ 建立失敗：{err_msg}"

    except Exception as e:
        logger.warning("Auto-create expense from LINE failed: %s", e)
        return None


async def try_create_expense_from_recognition(
    line_user_id: str,
    recognition: "RecognitionResult",
    image_path: str,
) -> Optional[str]:
    """用統一辨識結果建立費用紀錄"""
    if not recognition.success or not recognition.inv_num:
        return None

    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.extended.models import User

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.line_user_id == line_user_id)
            )
            user = result.scalars().first()

            if not user:
                return "💡 請先在系統中綁定 LINE 帳號，即可自動建立費用紀錄。"

            from app.services.expense_invoice_service import ExpenseInvoiceService
            from app.schemas.erp.expense import ExpenseInvoiceCreate
            from datetime import date as date_cls

            svc = ExpenseInvoiceService(db)
            relative_path = f"uploads/receipts/{Path(image_path).name}"

            create_data = ExpenseInvoiceCreate(
                inv_num=recognition.inv_num,
                amount=recognition.amount or recognition.total_amount or 0,
                tax_amount=recognition.tax_amount,
                date=recognition.date or date_cls.today(),
                buyer_ban=recognition.buyer_ban or "",
                seller_ban=recognition.seller_ban or "",
                category="其他",
                source=f"line_{recognition.method}",
            )

            try:
                expense = await svc.create(create_data, user_id=user.id,
                                           receipt_image_path=relative_path)
                await db.commit()
                eid = expense.id if hasattr(expense, 'id') else expense.get('id', '?')
                items_msg = ""
                if recognition.items:
                    items_msg = f"\n📋 品項 {len(recognition.items)} 項"
                return f"✅ 費用紀錄已建立 (ID: {eid}){items_msg}"
            except ValueError as e:
                if "已存在" in str(e):
                    return f"ℹ️ 發票 {recognition.inv_num} 已存在系統中。"
                return f"⚠️ 建立失敗：{e}"

    except Exception as e:
        logger.warning("Auto-create expense from LINE failed: %s", e)
        return None


def format_recognition_reply(recognition: "RecognitionResult", expense_msg: Optional[str] = None) -> str:
    """格式化統一辨識結果為 LINE 回覆訊息"""
    if recognition.success:
        method_label = {"qr": "QR Code", "ocr": "OCR", "qr+ocr": "QR+OCR"}.get(recognition.method, recognition.method)
        lines = [
            f"📄 發票辨識成功 ({method_label})",
            f"發票號碼：{recognition.inv_num}",
        ]
        if recognition.date:
            lines.append(f"日期：{recognition.date.isoformat()}")
        if recognition.total_amount:
            lines.append(f"含稅總額：NT$ {recognition.total_amount:,.0f}")
        if recognition.sales_amount:
            lines.append(f"未稅金額：NT$ {recognition.sales_amount:,.0f}")
        if recognition.tax_amount and recognition.tax_amount > 0:
            lines.append(f"稅額：NT$ {recognition.tax_amount:,.0f}")
        if recognition.seller_ban:
            lines.append(f"賣方統編：{recognition.seller_ban}")
        if recognition.buyer_ban:
            lines.append(f"買方統編：{recognition.buyer_ban}")

        # 品項明細
        if recognition.items:
            lines.append(f"\n📋 品項明細 ({len(recognition.items)} 項)：")
            for item in recognition.items[:5]:  # 最多顯示 5 項
                lines.append(f"  • {item.name} x{item.qty:.0f} = ${item.amount:,.0f}")
            if len(recognition.items) > 5:
                lines.append(f"  ... 共 {len(recognition.items)} 項")

        lines.append(f"\n信心度：{recognition.confidence:.0%}")

        if expense_msg:
            lines.append("")
            lines.append(expense_msg)

        if recognition.warnings:
            lines.append("\n⚠️ " + "、".join(recognition.warnings))

        return "\n".join(lines)
    else:
        return (
            "📄 未能辨識發票資訊\n\n"
            "請確認：\n"
            "• 電子發票請對準 QR Code\n"
            "• 傳統發票請拍攝完整正面\n"
            "• 光線充足、避免反光模糊\n"
        )


# --- Legacy wrappers (保持舊 API 相容) ---

def format_ocr_reply(ocr_result: "InvoiceOCRResult", expense_msg: Optional[str] = None) -> str:
    """[相容] 格式化 OCR 結果為回覆訊息"""
    if ocr_result.inv_num:
        lines = [
            "📄 發票辨識結果",
            f"發票號碼：{ocr_result.inv_num}",
        ]
        if ocr_result.date:
            lines.append(f"日期：{ocr_result.date.strftime('%Y-%m-%d')}")
        if ocr_result.amount:
            lines.append(f"金額：NT$ {ocr_result.amount:,.0f}")
        if ocr_result.seller_ban:
            lines.append(f"賣方統編：{ocr_result.seller_ban}")
        lines.append(f"信心度：{ocr_result.confidence:.0%}")
        if expense_msg:
            lines.append("")
            lines.append(expense_msg)
        return "\n".join(lines)
    return "📄 未能辨識發票資訊"
