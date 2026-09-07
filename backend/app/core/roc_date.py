# -*- coding: utf-8 -*-
"""民國年日期解析 —— 唯一定義（2026-09-08，A119）。

此前全 repo 有 **8 份**各自的實作（`_roc_to_date` ×4、`_parse_roc_date` ×4），
分散在派工進度／晨報×2／驗證器／財政部發票／報價單匯入／兩支標案爬蟲。
每一份吃的格式都只是自己那個來源的子集：

| 來源 | 格式 |
|---|---|
| 公文／派工文字 | `中華民國114年1月8日`、`民國114年1月8日`、`114年1月8日`（**嵌在句子裡**） |
| 晨報 | `115/04/17`、`115年01月15日` |
| 財政部 API | `1140108`（7 位無分隔）、`114/01/08` |
| 報價單總表 | `114.02.03`，**同一欄混有西元** `2025.02.03`；也有 Excel 原生日期 |
| 標案爬蟲 | `115/04/07` → 要的是 ISO 字串 |

同一件事 8 份定義的代價與 L147 #7（逾期日期三份）相同：格式一改要改八處，
漏一處不報錯。這裡收成兩個出口：`parse_roc_date()` 回 `date`、`roc_to_iso()` 回字串。
原本的 8 個名字保留為薄委派，呼叫端不必改。

規則（`.claude/rules/development-rules.md` §2.5）：外部資料解析完**立即轉西元**再進系統。
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

# 「民國」「中華民國」可有可無；年月日之間可以是 年月日、/、.、- ；也接受 7 位無分隔。
_SEP = re.compile(
    r"(?:中華民國|民國)?\s*(\d{2,4})\s*(?:年|/|\.|-)\s*(\d{1,2})\s*(?:月|/|\.|-)\s*(\d{1,2})\s*日?"
)
_COMPACT = re.compile(r"(?<!\d)(\d{3})(\d{2})(\d{2})(?!\d)")


def _to_ad_year(y: int) -> int:
    """位數判民國／西元：`114` 是民國、`2025` 是西元，同一欄可能兩者都有（報價單總表實況）。"""
    return y + 1911 if y < 1911 else y


def roc_year_to_ad(year: int) -> int:
    """年份（不含月日）民國 → 西元；已是西元（≥1911）原樣回。

    原本 19 處各自寫 `year + 1911`（其中一半自己再包一層 `if year < 1911`）。
    收成一份的意義同上：規則改一次全部生效。
    """
    return _to_ad_year(int(year))


def parse_roc_date(value: Any) -> Optional[date]:
    """任何常見民國年寫法 → `date`；解析不到回 None（不猜）。

    * `date`／`datetime` 直接通過（Excel 原生日期）
    * 字串：先找「年/月/日」形（含嵌在句子裡的），再退到 7 位無分隔 `1140108`
    * 年份 < 1911 視為民國，否則視為西元
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    m = _SEP.search(s)
    if not m:
        m = _COMPACT.search(s)
        if not m:
            return None
    try:
        return date(_to_ad_year(int(m.group(1))), int(m.group(2)), int(m.group(3)))
    except (ValueError, OverflowError):
        return None


def roc_to_iso(value: Any) -> str:
    """同上，但回 `YYYY-MM-DD`；解析不到回空字串（爬蟲既有契約）。"""
    d = parse_roc_date(value)
    return d.isoformat() if d else ""
