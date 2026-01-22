"""
安全數值轉換工具

提供從 Excel 資料中安全提取數值的函數，支援特殊格式。

@version 1.0.0
@date 2026-01-22
"""
from typing import Optional
import re
import pandas as pd


def _safe_int(value) -> Optional[int]:
    """
    安全轉換為整數，支援特殊格式

    支援格式：
    - 純數字: 123 -> 123
    - 帶文字: '電桿3' -> 3, '3棟' -> 3
    - 加法: '3+1' -> 4
    - 範圍: '3~5' -> 4 (取平均)
    - 無法解析: None

    Args:
        value: 任意輸入值

    Returns:
        轉換後的整數，或 None（無法解析時）

    Examples:
        >>> _safe_int(123)
        123
        >>> _safe_int('3+1')
        4
        >>> _safe_int('3~5')
        4
        >>> _safe_int('電桿3')
        3
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    try:
        # 已經是數字
        if isinstance(value, (int, float)):
            return int(value)

        value_str = str(value).strip()
        if not value_str:
            return None

        # 處理加法格式 (3+1)
        if '+' in value_str:
            parts = value_str.split('+')
            total = 0
            for part in parts:
                nums = re.findall(r'\d+', part)
                if nums:
                    total += int(nums[0])
            return total if total > 0 else None

        # 處理範圍格式 (3~5, 3-5)
        range_match = re.match(r'(\d+)\s*[~\-]\s*(\d+)', value_str)
        if range_match:
            low, high = int(range_match.group(1)), int(range_match.group(2))
            return (low + high) // 2

        # 提取第一個數字
        nums = re.findall(r'\d+', value_str)
        if nums:
            return int(nums[0])

        return None
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> Optional[float]:
    """
    安全轉換為浮點數，支援特殊格式

    支援格式：
    - 純數字: 123.5 -> 123.5
    - 範圍: '9~13' -> 11.0 (取平均)
    - 帶文字: '約100' -> 100.0
    - 無法解析: None

    Args:
        value: 任意輸入值

    Returns:
        轉換後的浮點數，或 None（無法解析時）

    Examples:
        >>> _safe_float(123.5)
        123.5
        >>> _safe_float('9~13')
        11.0
        >>> _safe_float('約100')
        100.0
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    try:
        # 已經是數字
        if isinstance(value, (int, float)):
            return float(value)

        value_str = str(value).strip()
        if not value_str:
            return None

        # 處理範圍格式 (9~13, 9-13)
        range_match = re.match(r'([\d.]+)\s*[~\-]\s*([\d.]+)', value_str)
        if range_match:
            low, high = float(range_match.group(1)), float(range_match.group(2))
            return (low + high) / 2

        # 提取數字（包含小數點）
        nums = re.findall(r'[\d.]+', value_str)
        if nums:
            return float(nums[0])

        return None
    except (ValueError, TypeError):
        return None
