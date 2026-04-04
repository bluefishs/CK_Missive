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

Version: 2.0.0
"""
import base64
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict

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
    method: str = ""  # "qr", "ocr", "qr+ocr", "none"

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


def recognize_invoice(file_path: str) -> RecognitionResult:
    """
    統一發票辨識入口 — QR 優先，OCR 補充

    Args:
        file_path: 影像檔案路徑

    Returns:
        RecognitionResult (含 Head + Detail)
    """
    result = RecognitionResult()

    # --- Step 1: QR Code (可能掃到左右兩個) ---
    qr_texts = _scan_all_qr(file_path)

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
            _parse_head_qr(head_text, result)
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
            items = _parse_detail_qr(detail_text)
            result.items = items
            if result.method == "qr":
                result.method = "qr"  # still qr
            logger.info(f"QR Detail 辨識: {len(items)} 品項")
        except Exception as e:
            result.warnings.append(f"QR Detail 解析失敗: {e}")

    # --- Step 2: OCR 補充 ---
    if not result.success:
        ocr = _try_ocr(file_path)
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
        ocr = _try_ocr(file_path)
        if ocr and ocr.get("tax_amount"):
            result.tax_amount = Decimal(str(ocr["tax_amount"]))
            result.method = "qr+ocr"

    if not result.success:
        result.method = "none"
        result.warnings.append("QR 和 OCR 均未辨識出發票資訊")

    return result


# ---------------------------------------------------------------------------
# Head QR 解析 (財政部規範 77 字元)
# ---------------------------------------------------------------------------

def _parse_head_qr(raw: str, result: RecognitionResult):
    """解析左側 Head QR Code"""
    result.inv_num = raw[0:10]

    # 民國日期
    roc_y = int(raw[10:13])
    m = int(raw[13:15])
    d = int(raw[15:17])
    result.date = date(roc_y + 1911, m, d)

    result.random_code = raw[17:21]

    # 銷售額 (未稅) — hex 8 碼
    sales_hex = raw[21:29]
    result.sales_amount = Decimal(str(int(sales_hex, 16)))

    # 總額 (含稅) — hex 8 碼
    total_hex = raw[29:37]
    result.total_amount = Decimal(str(int(total_hex, 16)))

    # 統一用 total_amount 作為 amount
    result.amount = result.total_amount

    # 稅額 = 總額 - 銷售額
    result.tax_amount = result.total_amount - result.sales_amount

    # 買方統編 (00000000 = 無)
    buyer = raw[37:45]
    result.buyer_ban = buyer if buyer != "00000000" else None

    # 賣方統編
    seller = raw[45:53]
    result.seller_ban = seller


# ---------------------------------------------------------------------------
# Detail QR 解析 (品項明細)
# ---------------------------------------------------------------------------

def _parse_detail_qr(raw: str) -> List[InvoiceItem]:
    """解析右側 Detail QR Code (UTF-8 格式)

    格式: **:品名1:數量1:單價1:品名2:數量2:單價2:...
    或可能是 base64 編碼
    """
    items = []

    # 嘗試 base64 解碼
    text = raw
    if not text.startswith("**"):
        try:
            text = base64.b64decode(raw).decode("utf-8", errors="ignore")
        except Exception:
            pass

    # 去除前綴 **
    if text.startswith("**"):
        text = text[2:]
    if text.startswith(":"):
        text = text[1:]

    parts = text.split(":")
    # 每 3 個為一組: 品名, 數量, 單價
    i = 0
    while i + 2 < len(parts):
        try:
            name = parts[i].strip()
            qty = float(parts[i + 1]) if parts[i + 1] else 1.0
            price = float(parts[i + 2]) if parts[i + 2] else 0.0
            if name:
                items.append(InvoiceItem(
                    name=name,
                    qty=qty,
                    unit_price=price,
                    amount=round(qty * price, 2),
                ))
            i += 3
        except (ValueError, IndexError):
            i += 1

    return items


# ---------------------------------------------------------------------------
# QR 掃描 (pyzbar)
# ---------------------------------------------------------------------------

def _scan_all_qr(file_path: str) -> List[str]:
    """掃描影像中所有 QR Code，回傳解碼文字列表"""
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode
        img = Image.open(file_path)
        results = decode(img)
        texts = []
        for r in results:
            text = r.data.decode("utf-8", errors="ignore")
            if text:
                texts.append(text)
        return texts
    except Exception as e:
        logger.debug(f"QR 掃描失敗: {e}")
        return []


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def _try_ocr(file_path: str) -> Optional[dict]:
    """嘗試 Tesseract OCR，失敗時用 Gemma 4 Vision 備援"""
    # Step A: Tesseract
    try:
        from app.services.invoice_ocr_service import InvoiceOCRService
        svc = InvoiceOCRService()
        result = svc.parse_image(file_path)
        if result.confidence > 0.3 and result.inv_num:
            return result.model_dump()
    except Exception:
        pass

    # Step B: Gemma 4 Vision (Tesseract 失敗或低信心度時)
    try:
        return _try_vision_ocr(file_path)
    except Exception:
        return None


def _try_vision_ocr(file_path: str) -> Optional[dict]:
    """用 Gemma 4 Vision 做發票 OCR"""
    import base64, httpx, json as _json, re

    try:
        with open(file_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None

    prompt = (
        "這是一張台灣發票照片。請提取以下資訊並以 JSON 格式回覆：\n"
        '{"inv_num":"發票號碼(2英文+8數字)","date":"YYYY-MM-DD","amount":含稅金額數字,'
        '"tax_amount":稅額數字,"buyer_ban":"買方統編8碼","seller_ban":"賣方統編8碼"}\n'
        "如果某欄位無法辨識就設為 null。只回 JSON，不要其他文字。"
    )

    try:
        from app.services.ai.ai_config import get_ai_config
        config = get_ai_config()
        resp = httpx.post(
            f"{config.ollama_base_url}/api/chat",
            json={
                "model": config.ollama_model,
                "messages": [{"role": "user", "content": prompt, "images": [img_b64]}],
                "stream": False,
                "think": False,
                "options": {"temperature": 0.1, "num_predict": 150},
            },
            timeout=30,
        )
        raw = resp.json().get("message", {}).get("content", "")

        # 提取 JSON
        json_match = re.search(r'\{[^}]+\}', raw)
        if not json_match:
            return None
        data = _json.loads(json_match.group())

        if not data.get("inv_num"):
            return None

        # 轉換日期
        inv_date = None
        if data.get("date"):
            from datetime import date as date_type
            try:
                inv_date = date_type.fromisoformat(data["date"])
            except ValueError:
                pass

        return {
            "inv_num": data["inv_num"],
            "date": inv_date,
            "amount": float(data["amount"]) if data.get("amount") else None,
            "tax_amount": float(data["tax_amount"]) if data.get("tax_amount") else None,
            "buyer_ban": data.get("buyer_ban"),
            "seller_ban": data.get("seller_ban"),
            "confidence": 0.7,  # Vision OCR 信心度固定 0.7
        }
    except Exception as e:
        logger.debug(f"Vision OCR 失敗: {e}")
        return None
