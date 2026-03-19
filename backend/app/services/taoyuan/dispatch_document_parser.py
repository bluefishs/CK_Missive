# -*- coding: utf-8 -*-
"""
派工單公文文號解析器

從 dispatch_enrichment_service.py 提取的純函數模組：
- parse_doc_line: 解析單行公文文號
- parse_roc_date: 解析民國日期
- parse_sequence_no: 解析項次
- parse_amount: 解析金額
- safe_cell: 安全取得儲存格值
- AGENCY_MAP / COMPANY_NAME: 文號前綴 → 發文單位映射

這些都是無狀態的工具函數，可獨立測試與複用。
"""
import re
from datetime import date
from typing import Optional, Dict, Any


# 文號前綴 → 發文單位映射
AGENCY_MAP = {
    '桃工用字': '桃園市政府工務局',
    '桃工字': '桃園市政府工務局',
    '府工用字': '桃園市政府工務局',
    '府工字': '桃園市政府工務局',
    '乾坤測字': '乾坤測繪科技有限公司',
    '乾坤測繪字': '乾坤測繪科技有限公司',
}
COMPANY_NAME = '乾坤測繪科技有限公司'


def parse_roc_date(raw: Any) -> Optional[date]:
    """解析民國日期字串 → 西元 date

    支援格式：112.7.14 / 112.07.14 / 113.5.2
    排除非日期值：未訂、不派工、派工暫緩
    """
    if not raw:
        return None
    text = str(raw).strip()
    if text in ('未訂', '不派工', '派工暫緩', ''):
        return None
    m = re.match(r'^(\d{2,3})\.(\d{1,2})\.(\d{1,2})', text)
    if not m:
        return None
    try:
        year = int(m.group(1)) + 1911
        month = int(m.group(2))
        day = int(m.group(3))
        return date(year, month, day)
    except (ValueError, OverflowError):
        return None


def parse_sequence_no(raw: Any) -> Optional[int]:
    """解析項次 (容許 '43\\n暫緩' 等含備註格式)"""
    if raw is None:
        return None
    text = str(raw).strip()
    first_line = text.split('\n')[0].strip()
    m = re.match(r'^(\d+)$', first_line)
    return int(m.group(1)) if m else None


def parse_amount(raw: Any) -> Optional[float]:
    """解析金額（int/float/str 皆可），None/空值回傳 None"""
    if raw is None:
        return None
    try:
        val = float(raw)
        return val
    except (ValueError, TypeError):
        return None


def safe_cell(row: tuple, col: int) -> Any:
    """安全取得 row[col]，超出範圍回傳 None"""
    return row[col] if len(row) > col else None


def parse_doc_line(line: str) -> Optional[Dict[str, Any]]:
    """解析單行公文文號：'112.5.26桃工用字第1120021701號' → {date, doc_number, sender}

    回傳 None 表示不可解析（空行、括號備註、非標準格式）。
    """
    line = line.strip()
    if not line or line.startswith('('):
        return None

    # 嘗試匹配：日期 + 文號
    m = re.match(
        r'^(\d{2,3})\.(\d{1,2})\.(\d{1,2})\s*'  # ROC date
        r'([\u4e00-\u9fff]+字第\d+號)',            # doc number
        line,
    )
    if not m:
        # 兩文號黏在一行的 fallback（取第一筆）— 用 findall 允許文號前有其他文字
        found = re.findall(
            r'(\d{2,3})\.(\d{1,2})\.(\d{1,2})\s*'
            r'([\u4e00-\u9fff]+字第\d+號)',
            line,
        )
        if not found:
            return None
        m = re.match(
            r'.*?(\d{2,3})\.(\d{1,2})\.(\d{1,2})\s*'
            r'([\u4e00-\u9fff]+字第\d+號)',
            line,
        )
        if not m:
            return None

    try:
        doc_date = date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))
    except (ValueError, OverflowError):
        return None

    doc_number = m.group(4)

    # 從文號前綴推斷發文單位
    sender = None
    for prefix, agency in AGENCY_MAP.items():
        if doc_number.startswith(prefix):
            sender = agency
            break

    return {
        'doc_date': doc_date,
        'doc_number': doc_number,
        'sender': sender,
    }
