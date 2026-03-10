# -*- coding: utf-8 -*-
"""
文號解析工具

從 Excel 欄位解析公文文號，處理多文號（換行/分號分隔）、
書名號移除、全形→半形轉換等清理邏輯。

@version 1.0.0
@date 2026-03-04
"""
import re
import unicodedata
from typing import List


# 全形→半形映射（僅數字和括號）
_FULLWIDTH_MAP = str.maketrans(
    '０１２３４５６７８９（）',
    '0123456789()',
)


def clean_doc_number(raw: str) -> str:
    """
    清理單一文號

    處理：
    1. strip 前後空白和換行
    2. 移除書名號「」
    3. 全形數字/括號→半形
    4. 壓縮連續空白為單一空格

    Args:
        raw: 原始文號字串

    Returns:
        清理後的文號
    """
    if not raw:
        return ""
    text = raw.strip()
    # 移除書名號
    text = text.replace('「', '').replace('」', '')
    # 全形→半形（僅數字和括號）
    text = text.translate(_FULLWIDTH_MAP)
    # 壓縮連續空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_doc_numbers(raw_input: str) -> List[str]:
    """
    從 Excel 欄位解析多個文號

    支援分隔符：換行 \\n、分號 ；/;、頓號 、
    自動去重但保持順序（第一筆用於向下相容 FK）。

    Args:
        raw_input: Excel 欄位原始值（可能含換行符）

    Returns:
        去重的文號列表（保持順序）
    """
    if not raw_input or not str(raw_input).strip():
        return []

    text = str(raw_input)

    # 分隔：換行 > 分號 > 頓號
    parts = re.split(r'[\n\r]+|[；;、]', text)

    seen = set()
    result = []
    for part in parts:
        cleaned = clean_doc_number(part)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)

    return result
