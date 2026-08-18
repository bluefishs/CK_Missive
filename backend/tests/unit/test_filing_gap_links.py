"""填報缺口的連結必須點得到（2026-08-17 owner 回報）。

owner：「/dashboard 待填報無法直接連結對應案件
`erp/quotations?case_code=CK2026_PM_01_005`」。

我原本產的是「列表頁 ＋ 查詢參數」的網址，而**列表頁根本沒有讀那個參數** ——
點過去只會停在未篩選的列表。那是「產了一個沒有人在接的連結」：
網址長得很合理、不會拋錯、也不會有任何訊號說它沒作用。

同型的形狀本專案記過多次（送出端與接收端各說各話，而兩邊都不會報錯）：
HTTP header 被例外處理器丟掉、CLI 參數被截斷、印 RED 卻 exit 0。

這一支鎖的是：**連結一律指向詳情頁 `/xxx/{id}`**，不得靠列表篩選。
"""
from __future__ import annotations

import re

import pytest

# 前端有註冊的詳情路由（`router/types.ts`）。
# 列表頁 + query param 的形式**刻意不列入** —— 那是這次的缺陷本身。
# 2026-08-17 放寬：允許 `?tab=` —— 但**只允許已查證過接收端會處理的參數**。
# `?tab=` 由 `DetailPageLayout` 於 08-15 開始支援（已讀碼確認）；
# `?case_code=` 則永遠不允許（列表頁不讀它，那正是本檔要防的缺陷）。
#
# 請款/應付沒有自己的詳情路由（08-02 隨 BillingsTab 移除），
# 它們只存在於報價詳情的分頁裡，所以必須連到報價 + tab。
ALLOWED_URL = re.compile(
    # 2026-08-18 補 `pm/cases`：新增的「已成案但財務端不存在」缺口連到 PM 案件詳情
    # （`ROUTES.PM_CASE_DETAIL = /pm/cases/:id`，types.ts 與 AppRouter 皆已註冊，已查證）。
    # 它要連的是「去這裡建報價單／成案」，不是去 ERP 找一個不存在的東西。
    r"^/(erp/quotations|contract-cases|erp/expenses|pm/cases)/\{[a-z_.]+\}"
    r"(\?tab=(receivable|payable|items|info|expenses))?$"
)


def test_gap_urls_point_to_detail_pages():
    """所有 GapItem 的 url 樣板都必須是詳情頁形式。

    用讀原始碼而非跑 DB：這條規則是「怎麼組網址」，
    而組網址的地方就在那幾行 f-string 裡。
    """
    import inspect

    from app.services.erp import filing_gap

    src = inspect.getsource(filing_gap.FilingGapService.collect)
    urls = re.findall(r'url=f"([^"]+)"', src)

    assert urls, "抓不到任何 url= —— 組網址的寫法改了，這支測試要跟著改"

    bad = [u for u in urls if not ALLOWED_URL.match(u)]
    assert not bad, (
        f"這些連結不是詳情頁形式: {bad}。"
        "不得用「列表頁 + 查詢參數」—— 列表頁沒有讀那些參數，"
        "點過去只會停在未篩選的列表（2026-08-17 owner 實際踩到）。"
    )


def test_no_query_param_urls():
    """明確擋掉 `?xxx=` 形式 —— 那是這次缺陷的特徵。"""
    import inspect

    from app.services.erp import filing_gap

    src = inspect.getsource(filing_gap.FilingGapService.collect)
    assert "?case_code=" not in src, (
        "又用了 `?case_code=` —— 列表頁不讀這個參數。"
        "要靠參數篩選的話，得先讓列表頁真的處理它（接收端沒接就是沒作用）。"
    )


def test_row_id_selected_in_every_gap_query():
    """每個缺口 SQL 都要撈出 id，否則組不出詳情頁網址。"""
    from app.services.erp import filing_gap

    for name in ("SQL_CONTRACT_NO_AMOUNT", "SQL_QUOTATION_NO_PRICE",
                 "SQL_QUOTATION_NO_COST"):
        sql = getattr(filing_gap, name)
        assert "row_id" in sql, f"{name} 沒有撈 row_id —— 組不出詳情頁連結"
    # 核銷那條用的是 e.id（欄名就叫 id），不需要別名
    assert "e.id" in filing_gap.SQL_EXPENSE_STUCK
