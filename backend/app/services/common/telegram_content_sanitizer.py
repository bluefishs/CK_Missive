"""
Telegram 推播內容敏感詞過濾器

背景：2026-04-21 用戶 Telegram 個人帳號被官方永久封禁，申訴駁回。
推測與 bot 推播內容中出現類詐騙特徵（身分證格式、金額、長編號）有關。
本模組提供 regex mask，在 bot push / send 之前套用，降低內容被誤判風險。

Version: 1.0.0
Created: 2026-04-21 (ADR-0027)
"""
from __future__ import annotations

import re
from typing import Iterable

# 身分證 / 統一編號 / 類詐騙 ID 格式：1~2 個英文字母 + 7~10 位數字
# 例：A123456789 / AB12345678 / B2345678901
_ID_LIKE = re.compile(r"\b[A-Z]{1,2}\d{7,10}\b")

# 金額格式：NT$ 50500 / NT$50,500 / NTD 1,234.56 / $12345
# 兩個分支：有逗號（需 1+ 個 ,\d{3} 組）或純數字（長度不限）
_MONEY_LIKE = re.compile(
    r"(?:NT\$|NTD|NT|\$)\s?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?",
    flags=re.IGNORECASE,
)

# 長數字串（10+ 位數字連續）：常見詐騙文號 / 帳號
_LONG_DIGITS = re.compile(r"\b\d{10,}\b")

# 類詐騙觸發詞彙（保留，方便未來擴充；目前不阻擋，只計數）
_SCAM_KEYWORDS: tuple[str, ...] = (
    "中獎", "匯款", "解除分期", "ATM", "警政署", "臨櫃", "驗證碼",
    "請勿透露", "立即處理", "即將停用",
)


def sanitize(text: str) -> str:
    """
    將文字中的身分證 / 金額 / 長編號 mask 為語意標籤。

    目的：避免 Telegram bot 推播內容被反詐騙系統誤判。
    """
    if not text:
        return text
    cleaned = _ID_LIKE.sub("[識別碼]", text)
    cleaned = _MONEY_LIKE.sub("[金額]", cleaned)
    cleaned = _LONG_DIGITS.sub("[編號]", cleaned)
    return cleaned


def has_scam_keywords(text: str, keywords: Iterable[str] = _SCAM_KEYWORDS) -> bool:
    """偵測是否含類詐騙詞彙（目前僅 observability，未來可作阻擋依據）"""
    if not text:
        return False
    return any(kw in text for kw in keywords)


__all__ = ["sanitize", "has_scam_keywords"]
