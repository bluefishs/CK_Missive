"""Schema 共用文字正規化 util（57e SSOT，2026-06-12）

收斂 agency/vendor schema 各自重複的 `normalize_name`（完全同碼）。
新 schema 需名稱正規化一律 import 此處，勿再各自寫。
"""
import re
import unicodedata
from typing import Optional


def normalize_cjk_compat(value: str) -> str:
    """把康熙部首與 CJK 相容漢字轉成標準漢字。

    2026-08-16 加入。實測 `documents.subject` **1560/2009（78%）**帶相容字
    （`年 U+F98E` vs 標準 `U+5E74`）—— 字形一模一樣、長度一樣、md5 不同，
    於是**所有以名稱比對的管控都會靜默失效**，包括 2026-08-10 才加的
    承攬案件防重（同名＋同年度＋同委託單位）。

    判準與轉法沿用 `app/scripts/normalize_unicode.py`（已存在且正確），
    不造第二份：**刻意不用全域 NFKC** —— 那會把全形逗號（，）轉成半形（,），
    而中文語境中全形標點是正常的。只逐字元轉換異常範圍。
    """
    if not value or not isinstance(value, str):
        return value
    out = []
    for ch in value:
        cp = ord(ch)
        if 0x2F00 <= cp <= 0x2FDF or 0xF900 <= cp <= 0xFAFF:
            out.append(unicodedata.normalize('NFKC', ch))
        else:
            out.append(ch)
    return ''.join(out)


def normalize_name(value: Optional[str]) -> Optional[str]:
    """標準化名稱字串：

    - 移除前後空白 + 全形空白（\\u3000）
    - 統一全形括號（）→ 半形 ()
    - 合併連續空白為單一空白
    - 結果為空 → None
    """
    if not value:
        return value
    result = normalize_cjk_compat(value).strip()
    result = result.replace('　', '')
    result = result.replace('（', '(').replace('）', ')')
    result = re.sub(r'\s+', ' ', result)
    return result if result else None
