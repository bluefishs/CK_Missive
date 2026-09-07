# -*- coding: utf-8 -*-
"""稽催的時間錨點 —— 唯一定義（2026-09-07）。

owner：「4 處計算預期無統整稽催機制嗎？」

## 問題

「這筆請款逾期幾天」在本 repo 有**三份各自獨立的實作**：

| 消費端 | 用途 |
|---|---|
| `ai/proactive/proactive_triggers_erp.py` | 主動推播（逾期未收、即將到期） |
| `erp/filing_gap.py` | 填報缺口的 `age_days` |
| `erp/my_summary_service.py` | 個人儀表板的 `overdue_count`／`overdue_30_count` |

三份都寫著 `CURRENT_DATE - billing_date`，沒有任何一處指向另一處。
2026-09-07 把自動建立的第一期改成**請款日留白**時，這件事的代價立刻具體化：
**只要漏改其中一處，那 86 筆佔位就會從那個消費端的逾期名單裡整批消失**
（實測：只認 `billing_date` 的話逾期從 198 掉到 118，少的 80 筆正是留白的那些），
而畫面上只會看到「逾期變少了」，沒有任何錯誤。

## 定義

**稽催的時間錨點 ＝ `COALESCE(請款日, 報價單日期)`。**

* 有真正的請款日 → 用它（人排定的請款日）
* 自動建立的佔位（請款日留白）→ 退回報價單日期，它是這件事真實存在的時間錨點
* 兩者都沒有 → 催不到（實測 6 筆，都是報價單本身沒有日期）

⚠️ **型別要轉**：`billing_date` 是 `date`，而 `quoted_at` 是 `datetime`。
不轉的話 `COALESCE` 回 timestamp，於是 `today - 它` 直接 TypeError（Python 端），
SQL 端則是 `CURRENT_DATE - 它` 回 interval ⇒ 「逾期 557 days 天」這種字串。
兩個症狀都是實跑才看到的 —— 靜態讀程式碼看不出 `date` 與 `datetime` 的差別。

⚠️ 「即將到期」**刻意不套這條**：佔位沒有排定的請款日，它不是「即將到期」，
是「還沒請款」—— 那一群由逾期段用報價單日期接住。兩件事不要混。

## 為什麼是一個模組而不是資料庫視圖

三個消費端一個用 SQLAlchemy 表達式、兩個用原生 SQL，形式本來就不同。
硬做成視圖要改三段查詢的 FROM，動的面積比收益大。
這裡把**定義**放在一處（兩種形式各一個出口），並由 `billing_dunning_ssot_audit`
盯著「有沒有人又自己寫了一份」——真正要防的是第四份實作出現，不是形式統一。
"""
from __future__ import annotations

#: 原生 SQL 用。假設查詢裡 `b` 是 `erp_billings`、`q` 是 `erp_quotations` 的別名。
#: 用字串而不是函式，是因為它會被拼進既有的多行 SQL 常數裡。
EFFECTIVE_BILLING_DATE_SQL = "COALESCE(b.billing_date, q.quoted_at::date)"

#: 這個模組的檔名 —— 稽核用它排除自己。
MODULE_BASENAME = "billing_dunning.py"


def effective_billing_date(billing_cls, quotation_cls):
    """SQLAlchemy 表達式版本。

    用法：`effective_billing_date(ERPBilling, ERPQuotation) < today`
    （查詢本身要先 join 到報價單，這裡不代為 join —— 代 join 會讓呼叫端
    看不出多了一個 join，而 join 的方向會影響筆數。）
    """
    from sqlalchemy import Date, cast, func
    return func.coalesce(billing_cls.billing_date, cast(quotation_cls.quoted_at, Date))


def is_overdue(billing_cls, quotation_cls, today):
    """逾期述語：時間錨點早於今天。未付狀態由呼叫端自己加（各處的定義不同：
    有的只算 pending，有的含 partial）。"""
    return effective_billing_date(billing_cls, quotation_cls) < today
