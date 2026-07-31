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
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from .invoice_recognizer import RecognitionResult, InvoiceItem

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

    _flag_amount_inconsistency(result)


# 營業稅率（加值型）
_VAT_RATE = Decimal("0.05")
# 容差：四捨五入誤差 1 元，或總額的 1%（取大者）
_TOLERANCE_ABS = Decimal("1")
_TOLERANCE_PCT = Decimal("0.01")


def _flag_amount_inconsistency(result) -> None:
    """QR 內含金額自相矛盾時標記（**只警示、不自動修改**）

    真實案例（2026-07-31，發票 DC-09761665 福懋加油站）：
      QR：銷售額 895、總額 957 → 我們算出稅額 62
      紙面：銷售額 895、稅額 45、總計 **940**
      差額 17 恰為收據上的「加油金折抵」——**商家 POS 在折抵前就算了 QR 的總額**。
    也就是 QR 資料本身與紙面不符，解析器並沒有讀錯。

    為何不自動改成 sales×1.05：
      混含免稅／零稅率品項的發票，總額本來就不等於 銷售額×1.05，
      自動「修正」會把正確資料改壞。**偵測得出來的事，交給人確認**。
    """
    sales, total = result.sales_amount, result.total_amount
    if sales is None or total is None or sales <= 0:
        return

    expected = (sales * (1 + _VAT_RATE)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    diff = abs(total - expected)
    tolerance = max(_TOLERANCE_ABS, total * _TOLERANCE_PCT)
    if diff > tolerance:
        result.warnings.append(
            f"QR 金額自相矛盾：銷售額 {sales} × 1.05 應為 {expected}，"
            f"但 QR 總額為 {total}（差 {diff}）。可能含免稅品項或商家折抵未反映，"
            f"請核對紙本『總計』後修正金額與稅額。"
        )


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
