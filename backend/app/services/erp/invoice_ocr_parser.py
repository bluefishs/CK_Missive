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
        from .invoice_ocr_service import InvoiceOCRService
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

    # ⚠️ 必須用「視覺」模型，不能用 config.ollama_model（實為 qwen2.5:7b 純文字）。
    # 2026-06-02 L64 已修過同一個 bug，但只修了 async 路徑
    # （_vision_ocr_async → vision_completion(task_type="vision")）；
    # smart-scan 實際走的是本 sync 路徑，它繞過 ai_connector 直接打 ollama，
    # 於是「圖片送純文字模型 → silent 失敗」在此原封不動存活至 2026-07-30。
    # 改讀 TASK_MODEL_MAP（SSOT）避免再各寫一份而漂移。
    # 置於 try 之外：except 分支要記錄 model 名稱，避免 NameError。
    try:
        from app.core.ai_connector import TASK_MODEL_MAP
        vision_model = TASK_MODEL_MAP.get("vision", "gemma4:e2b")
    except Exception:
        vision_model = "gemma4:e2b"

    try:
        from app.services.ai.core.ai_config import get_ai_config
        config = get_ai_config()
        resp = httpx.post(
            f"{config.ollama_base_url}/api/chat",
            json={
                "model": vision_model,
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
        # 去 silent（ADR-0028）：原為 logger.debug，導致「三條辨識路徑全滅」時
        # 使用者只看到「未辨識出發票資訊」，log 裡卻查不到任何線索。
        logger.warning("Vision OCR 失敗（model=%s）: %s", vision_model, e, exc_info=True)
        return None
