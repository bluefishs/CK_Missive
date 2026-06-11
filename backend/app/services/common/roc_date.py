"""ROC（民國）日期/時間解析 SSOT（2026-06-11，架構標準化）

背景：`code_duplication_audit` 揭發全專案 parse_date×10 / parse_roc×5 競爭實作、無 SSOT。
本模組為**唯一**民國日期/時間解析來源；散落各處的 ROC 解析應逐步遷移至此（收斂多重標準）。

對齊 L71 圖譜治理：建立 SSOT util，新代碼一律引用、勿再各自寫 regex。
"""
from __future__ import annotations

import re
from datetime import datetime, date
from typing import Optional

# 民國年(2-3碼) 月 日：「112.11.16」「112年9月21日」「112-9-21」
_ROC_DATE_RE = re.compile(r'(\d{2,3})\s*[.\-/年]\s*(\d{1,2})\s*[.\-/月]\s*(\d{1,2})')
# 時段：「下午2時」「上午9時30分」「14:00」
_TIME_RE = re.compile(r'(上午|下午|晚上)?\s*(\d{1,2})\s*[時點:]\s*(\d{1,2})?\s*分?')

# 民國紀年起點（西元 = 民國 + 1911）
ROC_OFFSET = 1911


def roc_to_ad(roc_year: int) -> int:
    """民國年 → 西元年（≥1000 視為已是西元，原樣回傳）"""
    return roc_year + ROC_OFFSET if roc_year < 1000 else roc_year


def parse_roc_date(text: str) -> Optional[date]:
    """從文字抽取民國日期 → date；無/格式異常回 None。"""
    if not text:
        return None
    m = _ROC_DATE_RE.search(text)
    if not m:
        return None
    year = roc_to_ad(int(m.group(1)))
    mo, d = int(m.group(2)), int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    try:
        return date(year, mo, d)
    except ValueError:
        return None


def parse_roc_datetime(text: str) -> Optional[datetime]:
    """從文字抽取民國日期 + 時段 → datetime；無時段回 None（呼叫端據此決定全天 vs 定時）。

    規則：下午/晚上 <12 時 +12；上午 12 時 → 0；時段須在日期之後出現。
    """
    if not text:
        return None
    dm = _ROC_DATE_RE.search(text)
    if not dm:
        return None
    year = roc_to_ad(int(dm.group(1)))
    mo, d = int(dm.group(2)), int(dm.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    tm = _TIME_RE.search(text, dm.end())
    if not tm:
        return None
    ap, hh, mm = tm.group(1), int(tm.group(2)), int(tm.group(3) or 0)
    if ap in ('下午', '晚上') and hh < 12:
        hh += 12
    elif ap == '上午' and hh == 12:
        hh = 0
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    try:
        return datetime(year, mo, d, hh, mm)
    except ValueError:
        return None
