"""排序解析與 PM 列管範圍的回歸鎖（2026-08-31）

鎖兩件當天修掉的事。兩者的共通點是**失敗時不會報錯**：

1. `getattr(Model, sort_by, Model.id)` 對「存在但不是欄位」的屬性會放行，
   然後在 `.desc()` 當場 500。容器內實測 `metadata`、`registry` 皆爆。

2. `include_converted` 的預設值。它現在是 `True`（向後相容），
   若有人「順手」改成 `False`，尚未更新的前端不送這個參數 ⇒
   費用報銷的案件下拉會少掉 136 個選項，**而且不會報錯**。

刻意不打 DB：這兩件事都是純結構性的，能在毫秒內鎖住。
"""

import pytest

from app.extended.models.pm import PMCase
from app.extended.models.core import ContractProject
from app.repositories.sort_utils import order_by_clause, resolve_sort_column, sortable_fields
from app.schemas.pm import PMCaseListRequest, PMSummaryRequest


# --- 1. 排序欄位解析 -------------------------------------------------

@pytest.mark.parametrize("model", [PMCase, ContractProject])
@pytest.mark.parametrize(
    "bad",
    [
        "metadata",      # SQLAlchemy 掛在類別上的 MetaData —— 舊寫法會通過再爆
        "registry",      # 同上
        "__class__",     # 任何 dunder
        "no_such_field",
        "",
        None,
    ],
)
def test_非欄位輸入一律退回預設(model, bad):
    col = resolve_sort_column(model, bad, model.id)
    # 退回的必須是可排序的東西 —— 呼叫 .desc() 不得拋例外
    col.desc()
    assert col is model.id


@pytest.mark.parametrize("model", [PMCase, ContractProject])
def test_真欄位可以排序(model):
    for name in ("id", "created_at"):
        col = resolve_sort_column(model, name, model.id)
        col.desc()
        assert col is getattr(model, name)


def test_排序子句必須把空值排最後():
    """PostgreSQL 的 `DESC` 預設是 **NULLS FIRST** ——「由大到小」的第一頁
    會是一整頁空值。2026-09-01 實測：報價單依 `total_price` 遞減，
    前三筆金額都是 0/NULL，而該範圍的真實最大值是 22,675,000。

    兩個方向都要 NULLS LAST：空值代表「沒有這筆資料」，升冪降冪都該排最後。
    """
    from sqlalchemy.sql.elements import UnaryExpression

    for desc in (True, False):
        clause = order_by_clause(PMCase, "contract_amount", PMCase.id, descending=desc)
        sql = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert "NULLS LAST" in sql.upper(), f"descending={desc} 沒有 NULLS LAST：{sql}"
        assert ("DESC" in sql.upper()) is desc, f"排序方向錯：{sql}"
        assert isinstance(clause, UnaryExpression)


def test_排序子句對非欄位輸入也安全():
    """壞輸入退回預設，而且**退回的那個也要 NULLS LAST** ——
    只在 happy path 補防護，等於沒補。"""
    sql = str(order_by_clause(PMCase, "metadata", PMCase.id, descending=True)
              .compile(compile_kwargs={"literal_binds": True}))
    assert "NULLS LAST" in sql.upper()
    assert "pm_cases.id" in sql


def test_負向對照_舊寫法確實會爆():
    """證明上面那組綠燈是有意義的。

    如果哪天 SQLAlchemy 讓 `MetaData.desc()` 變成合法，
    上面的測試就會退化成「怎樣都會過」的假綠 —— 這條會先紅，
    提醒有人回來重新評估這個修法還需不需要。
    """
    old_style = getattr(PMCase, "metadata", PMCase.id)
    assert old_style is not PMCase.id, "getattr 的預設值只在屬性不存在時生效"
    with pytest.raises(AttributeError):
        old_style.desc()


def test_白名單來自ORM而非手抄():
    """名單必須與 model 的欄位集合一致 —— 手抄的清單會跟著 model 漂移。

    2026-08-31 的第一版就是手抄的，裡面放了 `quotation_amount`，
    而它根本不是 `pm_cases` 的欄位（報價金額是從報價單聚合來的）。
    """
    fields = sortable_fields(PMCase)
    assert "quotation_amount" not in fields, "聚合欄位不得出現在可排序集合"
    assert {"id", "case_code", "contract_amount"} <= fields


# --- 2. PM 列管範圍的預設值 ------------------------------------------

def test_include_converted_預設為True_向後相容():
    """**不要因為「業務規則是排除」就把預設改成 False。**

    業務規則（已成案移交 /contract-cases 列管）由**呼叫端明寫 False** 表達。
    預設值管的是「沒有人表態時怎麼辦」，而沒有表態的那些呼叫端
    （尚未更新的前端、費用報銷的案件下拉）要的是全部。
    """
    assert PMCaseListRequest().include_converted is True
    assert PMSummaryRequest().include_converted is True


def test_include_converted_可被明確關閉():
    assert PMCaseListRequest(include_converted=False).include_converted is False
    assert PMSummaryRequest(include_converted=False).include_converted is False
