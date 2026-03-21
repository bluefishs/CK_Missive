import cv2
import numpy as np
from pyzbar.pyzbar import decode
from datetime import date
from typing import Dict, List, Optional

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """把圖片轉成 cv2 格式並進行二值化、去噪處理以強化 QR 辨識率"""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    # 轉灰階
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 高斯模糊去噪
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # 自適應二值化 (Adaptive Thresholding)
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return binary

def roc_to_iso(roc_date_str: str) -> date:
    """將民國年 (e.g. 1130515) 轉為 date(2024, 5, 15)"""
    if len(roc_date_str) != 7:
        raise ValueError("日期格式不正確，應為 7 位碼")
    year = int(roc_date_str[0:3]) + 1911
    month = int(roc_date_str[3:5])
    day = int(roc_date_str[5:7])
    return date(year, month, day)

def hex_to_int(hex_str: str) -> int:
    """發票金額 16 進位字串轉整數"""
    try:
        return int(hex_str, 16)
    except Exception:
        return 0

def parse_invoice_qr(left_qr: str, right_qr: Optional[str] = None) -> Dict:
    """
    根據台灣財政部 MIG 規格解析
    左碼: 發票字軌(10) + 開立日期(7) + 隨機碼(4) + 銷售額Hex(8) + 總計額Hex(8) + 買方統編(8) + 賣方統編(8) + 驗證碼(24)
    右碼: 品名等明細 (** 分隔)
    """
    if len(left_qr) < 77:
        raise ValueError("無效的左側 QR Code 字串 (長度需 >= 77)")

    inv_num = left_qr[0:10]
    roc_date_str = left_qr[10:17]
    random_code = left_qr[17:21]
    sales_amt_hex = left_qr[21:29]
    total_amt_hex = left_qr[29:37]
    buyer_ban = left_qr[37:45]
    seller_ban = left_qr[45:53]

    # 過濾統編為 00000000 的情況 (B2C 發票通常買方無統編)
    buyer_ban = buyer_ban if buyer_ban != "00000000" else None
    
    parsed_date = roc_to_iso(roc_date_str)
    amount = hex_to_int(total_amt_hex)

    # 處理右側品名明細
    items = []
    if right_qr and right_qr.startswith("**"):
        parts = right_qr.split(":")
        # 簡易切分示範 (實務上右碼會依據多種商品品項堆疊，如品名:數量:單價)
        # 需特別注意 MIG 規格中的分隔符號處理
        parsed_items = right_qr.strip("*").split(":")
        for idx in range(0, len(parsed_items) - 2, 3):
            if idx + 2 < len(parsed_items):
                try:
                    name = parsed_items[idx]
                    qty = int(parsed_items[idx+1])
                    price = int(parsed_items[idx+2])
                    items.append({
                        "item_name": name,
                        "qty": qty,
                        "unit_price": price,
                        "amount": qty * price
                    })
                except Exception:
                    pass

    return {
        "inv_num": inv_num,
        "date": parsed_date,
        "amount": amount,
        "buyer_ban": buyer_ban,
        "seller_ban": seller_ban,
        "items": items,
        "raw_qr": left_qr + (right_qr or "")
    }

def scan_and_parse_invoice(image_bytes: bytes) -> Dict:
    """
    完整流程：影像處理 -> pyzbar 掃描 -> 合併左右碼 -> 拋出格式化字典
    """
    processed_img = preprocess_image(image_bytes)
    decoded_objects = decode(processed_img)
    
    if not decoded_objects:
        raise ValueError("無法從圖片中辨識出 QR Code")
    
    # 找尋長度 >= 77 的左碼，另一則為右碼
    qr_strings = [obj.data.decode("utf-8") for obj in decoded_objects]
    
    left_qr = None
    right_qr = None
    
    for s in qr_strings:
        if len(s) >= 77 and s[0:2].isalpha():  # 發票字軌首兩碼為英文字母
            left_qr = s
        elif s.startswith("**"):
            right_qr = s

    if not left_qr:
        # 可能是沒有照到左碼，或是單純只有一碼的電子發票
        # 如果只有一個碼且長度夠，把它當作左碼試試看
        if len(qr_strings) == 1 and len(qr_strings[0]) >= 77:
            left_qr = qr_strings[0]
        else:
            raise ValueError("圖片中找不到符合規格的發票主 QR Code (左碼)")

    return parse_invoice_qr(left_qr, right_qr)
