"""Schema 共用文字正規化 util（57e SSOT，2026-06-12）

收斂 agency/vendor schema 各自重複的 `normalize_name`（完全同碼）。
新 schema 需名稱正規化一律 import 此處，勿再各自寫。
"""
import re
from typing import Optional


def normalize_name(value: Optional[str]) -> Optional[str]:
    """標準化名稱字串：

    - 移除前後空白 + 全形空白（\\u3000）
    - 統一全形括號（）→ 半形 ()
    - 合併連續空白為單一空白
    - 結果為空 → None
    """
    if not value:
        return value
    result = value.strip()
    result = result.replace('　', '')
    result = result.replace('（', '(').replace('）', ')')
    result = re.sub(r'\s+', ' ', result)
    return result if result else None
