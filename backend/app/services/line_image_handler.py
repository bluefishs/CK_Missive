"""
LINE Image Handler — 圖片訊息處理 (OCR 發票辨識)

提供：
- LINE Content API 圖片下載
- Tesseract OCR 辨識 → 發票資訊提取
- 自動建立費用紀錄 (LINE user → system user 對應)

Version: 1.0.0
Created: 2026-03-26
Extracted from: line_bot_service.py
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


def format_ocr_reply(ocr_result: "InvoiceOCRResult", expense_msg: Optional[str] = None) -> str:
    """格式化 OCR 辨識結果為回覆訊息"""
    if ocr_result.inv_num:
        lines = [
            "📄 發票辨識結果",
            f"發票號碼：{ocr_result.inv_num}",
        ]
        if ocr_result.date:
            lines.append(f"日期：{ocr_result.date.strftime('%Y-%m-%d')}")
        if ocr_result.amount:
            lines.append(f"金額：NT$ {ocr_result.amount:,.0f}")
        if ocr_result.tax_amount:
            lines.append(f"稅額：NT$ {ocr_result.tax_amount:,.0f}")
        if ocr_result.seller_ban:
            lines.append(f"賣方統編：{ocr_result.seller_ban}")
        if ocr_result.buyer_ban:
            lines.append(f"買方統編：{ocr_result.buyer_ban}")

        lines.append(f"信心度：{ocr_result.confidence:.0%}")

        if expense_msg:
            lines.append("")
            lines.append(expense_msg)

        if ocr_result.warnings:
            lines.append("")
            lines.append("⚠️ " + "、".join(ocr_result.warnings))

        return "\n".join(lines)
    else:
        reply = (
            "📄 未能辨識發票資訊\n\n"
            "請確認：\n"
            "• 拍攝清晰、光線充足\n"
            "• 發票完整入鏡\n"
            "• 避免反光或模糊\n"
        )
        if ocr_result.warnings:
            reply += "\n⚠️ " + "、".join(ocr_result.warnings)
        return reply
