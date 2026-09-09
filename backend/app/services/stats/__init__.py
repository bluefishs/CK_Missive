# -*- coding: utf-8 -*-
"""統計的中心服務 —— **案件與經費的口徑只在這裡定義**。

⭐ owner 2026-09-09：「這就是異值同工問題，案件與經費等統計請整合建構中心服務，
各頁面同步配合調整一致。」

## 這裡放什麼

| 模組 | 管什麼 | 為什麼要有唯一定義 |
|---|---|---|
| `finance` | **指標**：承攬金額／已請款／已收款／應付／已付 | 盤點時各有 3–4 份實作，「已收款」三份的狀態條件已經不同 |
| `case_scope` | **範圍**：年度／身分／類別／狀態 | 承攬案與 PM 案兩份平行實作，改一邊另一邊不動 |

**統計 ＝ 範圍 × 指標。** 過去這兩者都散在各頁面自己的查詢裡，
於是「同一個名詞、不同的算法」到處都是 —— 那就是異值同工。

## 用法

```python
from app.services.stats import finance, case_scope

sql = f"SELECT {finance.awarded_amount()} FROM ... WHERE {finance.case_year_condition(2026)}"
scope = case_scope.CaseStatsScope(year=2026, staff_user_id=7)
query = await scope.apply(db, query, case_scope.CONTRACT_PROJECT_COLUMNS)
```

## 守門

`scripts/checks/finance_metrics_ssot_audit.py`（weekly 132）——
在這個套件之外自己寫金額算式即紅；存量走基線、逐一清。
"""
from app.services.stats import case_scope, finance  # noqa: F401

__all__ = ["finance", "case_scope"]
