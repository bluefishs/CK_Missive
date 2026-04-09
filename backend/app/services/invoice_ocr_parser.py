"""
發票 OCR 解析器

從 invoice_recognizer.py 拆分，負責：
  - Tesseract OCR 解析
  - Gemma 4 Vision 同步 OCR (備援)
  - OCR 結果欄位提取

Version: 1.0.0 (拆分自 invoice_recognizer v2.0.0)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def try_ocr(file_path: str) -> Optional[dict]:
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
        return try_vision_ocr(file_path)
    except Exception:
        return None


def try_vision_ocr(file_path: str) -> Optional[dict]:
    """用 Gemma 4 Vision 做發票 OCR (同步 HTTP 版)"""
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
        from app.services.ai.core.ai_config import get_ai_config
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
