# -*- coding: utf-8 -*-
"""案名相似度比對 — CJK 可用（2026-07-31）

## 為何不用 pg_trgm

本專案 DB 已裝 pg_trgm（標案搜尋的 GIN index 用它），但它對中文**完全無效**：

    SELECT show_trgm('測量');          -- {}      ← 零個 trigram
    SELECT similarity('測量','測量');   -- 0.0     ← 連自己比自己都是 0

原因：pg_trgm 只對 ASCII/字母數字切 trigram，CJK 字元被忽略。

**危險之處在於它不會報錯，而是回一個看似合理的數字**：
實測 `similarity(標案標題, 案件名稱) >= 0.6` 撈出 33 筆「相似」案件，
逐筆檢查後發現全是噪音 —— 只因雙方都含 ASCII「115」（年度），
於是「115年度圖根點補建、新建作業」與「115學年度八年級戶外教學隔宿露營活動」
被判為 **相似度 1.00**。若直接上線，建案畫面會列出一堆風馬牛不相及的候選。

（這與 07-30「沉默成功」四例同型：函式回了值、沒有例外，但做的不是你以為的事。）

## 改用字元 bigram Jaccard

資料量極小（承攬案件 87 + 邀標案件 73 = 160 筆），在 Python 端算完全無壓力，
且不依賴任何 DB extension。

- 正規化：去除空白與常見標點，全形數字→半形
- 相似度：字元 bigram 的 Jaccard 係數
- 包含關係：一方為另一方子字串時給高分（「…作業」vs「…作業(第二期)」是常見型態）
"""
from __future__ import annotations

import re
import unicodedata

# 案名常見雜訊：括號、標點、空白。移除後再比對，避免「(開口契約)」造成假性差異。
_NOISE = re.compile(r"[\s　（）()「」『』【】\[\]、,，。.．・･:：;；/／\\－\-—_~～]+")

# 一方包含另一方時的最低分數（「…第二期」「…(開口契約)」型態）
CONTAINMENT_SCORE = 0.85


def normalize_case_name(name: str | None) -> str:
    """正規化案名：全形→半形、去雜訊字元"""
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", str(name))
    return _NOISE.sub("", s)


def _bigrams(s: str) -> set[str]:
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def name_similarity(a: str | None, b: str | None) -> float:
    """0.0–1.0；對中文有效。完全相同回 1.0。"""
    na, nb = normalize_case_name(a), normalize_case_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return CONTAINMENT_SCORE
    A, B = _bigrams(na), _bigrams(nb)
    union = A | B
    if not union:
        return 0.0
    return len(A & B) / len(union)
