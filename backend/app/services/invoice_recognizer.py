"""
統一發票辨識服務 (Invoice Recognizer)

整合 QR Code + OCR 為單一入口，供所有管道共用：
  - 前端拍照上傳 (Web/Mobile)
  - LINE Bot 圖片訊息
  - Watchdog 資料夾監控
  - 手動匯入

台灣電子發票 QR Code 規格 (財政部規範):
  ■ 左側 QR (Head): 77+ 字元
    [0:10]   發票號碼 (2英+8數)
    [10:17]  民國日期 YYYMMDD
    [17:21]  隨機碼 4 碼
    [21:29]  銷售額 hex 8 碼 (未稅)
    [29:37]  總額 hex 8 碼 (含稅)
    [37:45]  買方統編 8 碼 (無則 00000000)
    [45:53]  賣方統編 8 碼
    [53:77]  驗證碼 24 碼 (AES 加密)
    [77:]    營業人自訂區 (選用)

  ■ 右側 QR (Detail): Base64/UTF-8 編碼
    **:**:品名1:數量1:單價1:品名2:數量2:單價2:...

辨識策略：
  1. 優先 QR Code (pyzbar) — 同時掃描左右兩個 QR
  2. QR 失敗則 OCR (Tesseract)
  3. 合併最佳結果

Version: 3.0.0 (拆分為 invoice_qr_decoder + invoice_ocr_parser)
"""
import base64
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class InvoiceItem:
    """品項明細"""
    name: str
    qty: float
    unit_price: float
    amount: float


@dataclass
class RecognitionResult:
    """統一辨識結果"""
    success: bool = False
    method: str = ""  # "qr", "ocr", "qr+ocr", "vision", "none"

    # Head 資訊
    inv_num: Optional[str] = None
    date: Optional[date] = None
    random_code: Optional[str] = None
    sales_amount: Optional[Decimal] = None   # 未稅銷售額
    total_amount: Optional[Decimal] = None   # 含稅總額
    amount: Optional[Decimal] = None         # 對外使用金額 (= total_amount)
    tax_amount: Optional[Decimal] = None     # 稅額 (= total - sales)
    buyer_ban: Optional[str] = None
    seller_ban: Optional[str] = None

    # Detail 明細
    items: List[InvoiceItem] = field(default_factory=list)

    # Meta
    confidence: float = 0.0
    raw_qr_head: Optional[str] = None
    raw_qr_detail: Optional[str] = None
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "method": self.method,
            "inv_num": self.inv_num,
            "date": self.date.isoformat() if self.date else None,
            "random_code": self.random_code,
            "sales_amount": float(self.sales_amount) if self.sales_amount else None,
            "total_amount": float(self.total_amount) if self.total_amount else None,
            "amount": float(self.amount) if self.amount else None,
            "tax_amount": float(self.tax_amount) if self.tax_amount else None,
            "buyer_ban": self.buyer_ban,
            "seller_ban": self.seller_ban,
            "items": [{"name": i.name, "qty": i.qty, "unit_price": i.unit_price, "amount": i.amount} for i in self.items],
            "confidence": round(self.confidence, 2),
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Backward-compatible aliases for internal functions (used by tests)
# ---------------------------------------------------------------------------
def _parse_head_qr(raw: str, result: RecognitionResult):
    from app.services.invoice_qr_decoder import parse_head_qr
    return parse_head_qr(raw, result)


def _parse_detail_qr(raw: str) -> List[InvoiceItem]:
    from app.services.invoice_qr_decoder import parse_detail_qr
    return parse_detail_qr(raw)


def _scan_all_qr(file_path: str) -> List[str]:
    from app.services.invoice_qr_decoder import scan_all_qr
    return scan_all_qr(file_path)


def _try_ocr(file_path: str) -> Optional[dict]:
    from app.services.invoice_ocr_parser import try_ocr
    return try_ocr(file_path)


# ---------------------------------------------------------------------------
# Main entry point — QR first, OCR fallback
# ---------------------------------------------------------------------------

def recognize_invoice(file_path: str) -> RecognitionResult:
    """
    統一發票辨識入口 — QR 優先，OCR 補充

    Args:
        file_path: 影像檔案路徑

    Returns:
        RecognitionResult (含 Head + Detail)
    """
    from app.services.invoice_qr_decoder import scan_all_qr, parse_head_qr, parse_detail_qr
    from app.services.invoice_ocr_parser import try_ocr

    result = RecognitionResult()

    # --- Step 1: QR Code (可能掃到左右兩個) ---
    qr_texts = scan_all_qr(file_path)

    head_text = None
    detail_text = None

    for text in qr_texts:
        if len(text) >= 49 and text[:2].isalpha() and text[2:10].isdigit():
            head_text = text  # 左側 Head QR
        elif text.startswith("**"):
            detail_text = text  # 右側 Detail QR
        elif ":" in text and not head_text:
            # 可能是 Detail QR 的 base64 編碼
            try:
                decoded = base64.b64decode(text).decode("utf-8", errors="ignore")
                if ":" in decoded:
                    detail_text = decoded
            except Exception:
                pass

    # 解析 Head QR
    if head_text:
        result.raw_qr_head = head_text
        try:
            parse_head_qr(head_text, result)
            result.method = "qr"
            result.confidence = 1.0
            result.success = True
            logger.info(f"QR Head 辨識: {result.inv_num} / 總額={result.total_amount} / 稅額={result.tax_amount}")
        except Exception as e:
            result.warnings.append(f"QR Head 解析失敗: {e}")

    # 解析 Detail QR (品項明細)
    if detail_text:
        result.raw_qr_detail = detail_text
        try:
            items = parse_detail_qr(detail_text)
            result.items = items
            if result.method == "qr":
                result.method = "qr"  # still qr
            logger.info(f"QR Detail 辨識: {len(items)} 品項")
        except Exception as e:
            result.warnings.append(f"QR Detail 解析失敗: {e}")

    # --- Step 2: OCR 補充 ---
    if not result.success:
        ocr = try_ocr(file_path)
        if ocr:
            result.method = "ocr"
            result.inv_num = ocr.get("inv_num")
            result.date = ocr.get("date")
            result.amount = Decimal(str(ocr["amount"])) if ocr.get("amount") else None
            result.total_amount = result.amount
            result.tax_amount = Decimal(str(ocr["tax_amount"])) if ocr.get("tax_amount") else None
            if result.amount and result.tax_amount:
                result.sales_amount = result.amount - result.tax_amount
            result.buyer_ban = ocr.get("buyer_ban")
            result.seller_ban = ocr.get("seller_ban")
            result.confidence = ocr.get("confidence", 0.0)
            result.success = bool(result.inv_num)
            if result.success:
                logger.info(f"OCR 辨識: {result.inv_num} (conf={result.confidence:.0%})")
    elif not result.tax_amount:
        # QR 成功但缺稅額，OCR 補充
        ocr = try_ocr(file_path)
        if ocr and ocr.get("tax_amount"):
            result.tax_amount = Decimal(str(ocr["tax_amount"]))
            result.method = "qr+ocr"

    if not result.success:
        result.method = "none"
        result.warnings.append("QR 和 OCR 均未辨識出發票資訊")

    return result


# ---------------------------------------------------------------------------
# Async Vision OCR (via ai_connector.vision_completion)
# ---------------------------------------------------------------------------

async def _vision_ocr_async(image_bytes: bytes) -> Optional[dict]:
    """Use Gemma 4 vision_completion for structured invoice extraction.

    Returns a dict compatible with RecognitionResult fields, or None on failure.
    """
    try:
        from app.core.ai_connector import get_ai_connector
        ai = get_ai_connector()
        prompt = (
            "分析此發票圖片，提取以下資訊並以 JSON 格式回覆：\n"
            '{"inv_num": "發票號碼", "inv_date": "日期(YYYY-MM-DD)", '
            '"seller_name": "賣方名稱", "seller_tax_id": "賣方統編", '
            '"buyer_tax_id": "買方統編", "amount": 金額數字, '
            '"tax": 稅額數字, "total": 合計數字, '
            '"items": [{"name": "品名", "qty": 數量, "price": 單價}]}\n'
            "如果無法辨識某欄位，設為 null。"
        )
        result = await ai.vision_completion(prompt, image_bytes, max_tokens=512)
        from app.services.ai.agent_utils import parse_json_safe
        parsed = parse_json_safe(result)
        if parsed and parsed.get("inv_num"):
            return parsed
    except Exception as e:
        logger.debug("Gemma 4 vision OCR (async) failed, falling back: %s", e)
    return None


async def recognize_invoice_async(file_path: str) -> RecognitionResult:
    """Async invoice recognition -- Gemma 4 Vision first, then QR+OCR fallback.

    Uses ai_connector.vision_completion() for full structured extraction
    before falling back to the synchronous QR/Tesseract pipeline.
    """
    # --- Step 0: Try Gemma 4 Vision (primary) ---
    try:
        with open(file_path, "rb") as f:
            image_bytes = f.read()
    except Exception as e:
        logger.warning("Cannot read file for vision OCR: %s", e)
        return recognize_invoice(file_path)

    vision_data = await _vision_ocr_async(image_bytes)

    if vision_data and vision_data.get("inv_num"):
        result = RecognitionResult(success=True, method="vision")
        result.inv_num = vision_data["inv_num"]
        result.confidence = 0.85

        # Parse date
        inv_date_str = vision_data.get("inv_date")
        if inv_date_str:
            try:
                result.date = date.fromisoformat(inv_date_str)
            except (ValueError, TypeError):
                pass

        # Amounts
        total = vision_data.get("total")
        amount = vision_data.get("amount")
        tax = vision_data.get("tax")
        if total is not None:
            result.total_amount = Decimal(str(total))
            result.amount = result.total_amount
        elif amount is not None:
            result.amount = Decimal(str(amount))
            result.total_amount = result.amount
        if tax is not None:
            result.tax_amount = Decimal(str(tax))
        elif result.total_amount and result.amount and result.total_amount != result.amount:
            result.tax_amount = result.total_amount - result.amount

        # Sales amount
        if result.total_amount and result.tax_amount:
            result.sales_amount = result.total_amount - result.tax_amount

        # Tax IDs
        result.seller_ban = vision_data.get("seller_tax_id")
        result.buyer_ban = vision_data.get("buyer_tax_id")

        # Items
        raw_items = vision_data.get("items") or []
        for item in raw_items:
            if isinstance(item, dict) and item.get("name"):
                qty = float(item.get("qty", 1) or 1)
                price = float(item.get("price", 0) or 0)
                result.items.append(InvoiceItem(
                    name=item["name"],
                    qty=qty,
                    unit_price=price,
                    amount=round(qty * price, 2),
                ))

        logger.info(
            "Vision recognition: %s / total=%s / items=%d",
            result.inv_num, result.total_amount, len(result.items),
        )
        return result

    # --- Fallback: sync QR + OCR pipeline ---
    return recognize_invoice(file_path)
