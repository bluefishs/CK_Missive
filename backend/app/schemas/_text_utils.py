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


# ---------------------------------------------------------------------------
# 空字串 → None（2026-08-18）
# ---------------------------------------------------------------------------
def blank_to_none(value):
    """表單清空欄位時送的是 `""`，對選填欄位而言那與 `None` 是同一件事。

    ## 為什麼需要

    `Optional[EmailStr]` 與 `Field(None, min_length=1)` **只接受 None，
    不接受空字串** —— 於是使用者把 email 或姓名清掉再儲存就 **422**，
    而錯誤訊息說「不是有效的電子郵件」，他看不懂自己做錯什麼
    （他做的是「把這一欄清掉」，那是完全正常的操作）。

    owner 2026-08-18 實際踩到：`POST /api/project-agency-contacts/update` 422。
    掃全後發現**同型共 7 支**更新 schema（機關／廠商／專案／使用者／同義詞…），
    也就是這些模組**全部都無法清空 email**。

    ## 為什麼修在 schema 不是前端

    「每個表單都要記得把空字串轉成 null」行不通 —— 漏一個就是一個 422，
    而它只在「使用者剛好清空那一欄」時發生，平常測不到。

    ## 邊界

    只用於**更新類**的選填欄位。建立時的必填欄位仍應拒絕空字串
    （那時「沒填」是真的錯誤，不是「清空」）。

    只吃掉純空白字串；`" a "` 這種會保留原值不 strip ——
    去空白是另一件事，混在一起會讓這支變成「順便做很多事」的工具。
    """
    return None if isinstance(value, str) and not value.strip() else value
