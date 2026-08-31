"""排序欄位解析（共用）

2026-08-31 建立。起因：`/pm/cases` 的表頭排序改由後端執行，於是 `sort_by`
從「內部呼叫端寫死的字串」變成「使用者點得到的輸入」，而全庫 8 個 repository
都是同一個寫法：

    sort_column = getattr(SomeModel, sort_by, SomeModel.id)

`getattr` 的預設值只在**屬性不存在**時生效。ORM 類別上存在、卻不是欄位的
屬性一大票（`metadata`、`registry`、relationship、classmethod），它們會通過
這一關，然後在 `.desc()` 當場炸掉：

    ?sort_by=metadata  →  AttributeError: 'MetaData' object has no attribute 'desc'

已在容器內實測（2026-08-31）：`metadata`、`registry` 兩者都是 500。

## 為什麼不用手寫白名單

`taoyuan/dispatch_order_repository` 用的是手抄的 `allowed_sort_fields`。
那能擋，但**清單會跟著 model 漂移** —— 加了欄位沒有人記得回來補，
症狀是「排序沒反應」而不會報錯。ORM 自己就知道哪些屬性對應到欄位
（`mapper.column_attrs`），問它比抄一份可靠。

我第一版也是手抄的：`PMCase` 那份裡放了 `quotation_amount`，
而它根本不是該表的欄位（報價金額是聚合出來的）。**手抄當下就已經錯了一項。**
"""

from typing import Any, Optional

from sqlalchemy import inspect as sa_inspect


def sortable_fields(model: Any) -> frozenset:
    """該 model 可用於排序的屬性名（＝真正對應到資料表欄位的那些）。

    用 `mapper.column_attrs` 而不是 `__table__.columns`：前者給的是
    **ORM 屬性名**，後者給的是欄位名。兩者在 `mapped_column(name=...)`
    的情況下會不一樣，而呼叫端 `getattr` 用的是屬性名。
    """
    return frozenset(attr.key for attr in sa_inspect(model).mapper.column_attrs)


def resolve_sort_column(model: Any, sort_by: Optional[str], default: Any) -> Any:
    """把 `sort_by` 解析成可排序的欄位，不合格就回 `default`。

    不合格＝空值、不是字串、或不在該 model 的欄位集合內。
    **不猜、不部分比對** —— 猜錯的代價是使用者拿到一個沒有說明的順序。
    """
    if not sort_by or not isinstance(sort_by, str):
        return default
    if sort_by not in sortable_fields(model):
        return default
    return getattr(model, sort_by)
