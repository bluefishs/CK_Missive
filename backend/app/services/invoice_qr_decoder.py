"""
發票 QR Code 解碼器

從 invoice_recognizer.py 拆分，負責：
  - pyzbar QR Code 掃描
  - 左側 Head QR 解析 (財政部規範 77 字元)
  - 右側 Detail QR 解析 (品項明細)

Version: 1.0.0 (拆分自 invoice_recognizer v2.0.0)
"""
import base64
import logging
from datetime import date
from decimal import Decimal
from typing import List

from app.services.invoice_recognizer import RecognitionResult, InvoiceItem

logger = logging.getLogger(__name__)


def scan_all_qr(file_path: str) -> List[str]:
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


def parse_head_qr(raw: str, result: RecognitionResult):
    """解析左側 Head QR Code (財政部規範 77 字元)

    欄位佈局:
      [0:10]   發票號碼 (2英+8數)
      [10:17]  民國日期 YYYMMDD
      [17:21]  隨機碼 4 碼
      [21:29]  銷售額 hex 8 碼 (未稅)
      [29:37]  總額 hex 8 碼 (含稅)
      [37:45]  買方統編 8 碼 (無則 00000000)
      [45:53]  賣方統編 8 碼
      [53:77]  驗證碼 24 碼
    """
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


def parse_detail_qr(raw: str) -> List[InvoiceItem]:
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
