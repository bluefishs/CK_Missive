# -*- coding: utf-8 -*-
"""案件金流異常 —— **推導**出來的，不是有人去打的旗標。

## owner 2026-09-08

> 「5 筆的『已收 17,850』已付清、發票多開 —— 是否異常案件標註機制並增列篩選查詢，
>  以利解除或處理異常費用之案件機制」

那五筆（`CK2025_PM_02_117/120/129/143/152`）的形狀完全一樣：
請款 17,850（未稅 17,000）、已收 17,850 已付清，而發票開了 18,690（未稅 17,800）。
**它是事實不是輸入錯誤** —— 所以要的不是「把數字改成一致」，
是讓這種案件**看得見、篩得出來、判讀完可以解除**。

## 為什麼異常是推導的，不是欄位

本 repo 反覆出事的形狀是「同一件事有兩份宣告，改一份另一份不動，
而沒有任何一方報錯」（L145 家族）。若把「異常」存成報價單上的一個 boolean，
那一刻起它就是第二份宣告：發票改了、請款補了，旗標不會跟著動
⇒ **列表說異常而數字已經正常了**，或更糟，反過來。

⇒ 異常一律由**當下的數字**推導。人能做的是「判讀」（ack）：
   在 `erp_finance_anomaly_acks` 留一筆「我看過了，原因是 X」。
   判讀不會讓異常消失 —— 數字還是那樣 —— 它讓這一筆從
   「待處理」移到「已判讀」。**解除的是待辦，不是事實。**

## 判準與 weekly 104 的關係（**不是同一份，故意的**）

`scripts/checks/erp_amount_semantics_audit.py`（weekly 104）問的是同一族問題，
但**粒度不同**：它逐筆比對（這張發票 vs 它綁的那次請款），
這裡是**逐案彙總**（這一案的發票合計 vs 請款合計）。

兩種粒度都需要，而且會給出不同的答案：一案分兩次開票、金額互相補足時，
逐筆會紅而逐案不紅；反過來，發票沒綁 `billing_id` 時逐筆看不到而逐案看得到。
**把它們硬做成同一份，會有一邊被迫改成錯的粒度。**

⇒ 不宣稱兩者相等。要防的是「一邊改了另一邊不動」——
由 weekly 127（`finance_anomaly_parity_audit.py`）盯**方向一致性**：
同一族的判準，一邊抓到而另一邊完全是 0，就是有人只改了一邊。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnomalyType:
    code: str
    label: str
    severity: str          # "red" ＝數字互相矛盾；"yellow" ＝需要人判斷
    explain: str           # 給畫面用的一句話：為什麼這算異常
    #: 回傳 `(quotation_id, detail)` 的 SQL。detail 是給人看的差額說明。
    sql: str


#: 這些聚合在四條判準裡重複出現 —— 抽成一段，避免同一個「已作廢發票要不要算」
#: 在四個地方各寫一次而其中一個忘了排除（那正是本檔開頭說的形狀）。
_AGG = """
    LEFT JOIN (SELECT erp_quotation_id,
                      SUM(billing_amount) AS billed,
                      SUM(COALESCE(payment_amount, 0)) AS paid
                 FROM erp_billings GROUP BY 1) b ON b.erp_quotation_id = q.id
    LEFT JOIN (SELECT erp_quotation_id, SUM(amount) AS inv
                 FROM erp_invoices WHERE voided_at IS NULL GROUP BY 1) i
              ON i.erp_quotation_id = q.id
"""

ANOMALY_TYPES: tuple[AnomalyType, ...] = (
    AnomalyType(
        code="invoice_over_billing",
        label="發票額大於請款額",
        severity="red",
        explain="開出去的發票金額比請款金額多 —— 可能是追加未補請款，也可能是發票開錯。",
        sql=f"""
            SELECT q.id, '發票 ' || TO_CHAR(COALESCE(i.inv,0), 'FM999,999,999')
                        || '｜請款 ' || TO_CHAR(COALESCE(b.billed,0), 'FM999,999,999')
                        || '｜多 ' || TO_CHAR(COALESCE(i.inv,0) - COALESCE(b.billed,0), 'FM999,999,999')
              FROM erp_quotations q {_AGG}
             WHERE q.deleted_at IS NULL
               AND COALESCE(i.inv,0) > COALESCE(b.billed,0)
        """,
    ),
    AnomalyType(
        code="paid_over_billing",
        label="已收款大於請款額",
        severity="red",
        explain="收到的錢比請的多 —— 請款單可能少開一期，或收款登記掛錯案。",
        sql=f"""
            SELECT q.id, '已收 ' || TO_CHAR(COALESCE(b.paid,0), 'FM999,999,999')
                        || '｜請款 ' || TO_CHAR(COALESCE(b.billed,0), 'FM999,999,999')
              FROM erp_quotations q {_AGG}
             WHERE q.deleted_at IS NULL
               AND COALESCE(b.paid,0) > COALESCE(b.billed,0)
        """,
    ),
    AnomalyType(
        code="billing_over_contract",
        label="請款額大於合約總價",
        severity="red",
        explain="請款合計超過報價總價 —— 追加工程未反映在報價單，或請款金額打錯。",
        sql=f"""
            SELECT q.id, '請款 ' || TO_CHAR(COALESCE(b.billed,0), 'FM999,999,999')
                        || '｜總價 ' || TO_CHAR(COALESCE(q.total_price,0), 'FM999,999,999')
              FROM erp_quotations q {_AGG}
             WHERE q.deleted_at IS NULL
               AND COALESCE(q.total_price,0) > 0
               -- 千分之一的容差：四捨五入造成的 1 元差不是異常，
               -- 把它算進來只會得到一張沒有人看的清單。
               AND COALESCE(b.billed,0) > COALESCE(q.total_price,0) * 1.001
        """,
    ),
    AnomalyType(
        code="paid_without_invoice",
        label="已收款但未開發票",
        severity="yellow",
        explain="錢收了而發票一張都沒有 —— 可能是還沒開，也可能是開了沒登錄。",
        sql=f"""
            SELECT q.id, '已收 ' || TO_CHAR(COALESCE(b.paid,0), 'FM999,999,999') || '｜發票 0'
              FROM erp_quotations q {_AGG}
             WHERE q.deleted_at IS NULL
               AND COALESCE(b.paid,0) > 0
               AND COALESCE(i.inv,0) = 0
        """,
    ),
)

BY_CODE = {a.code: a for a in ANOMALY_TYPES}


async def scan(
    db: AsyncSession,
    *,
    codes: Optional[Iterable[str]] = None,
    quotation_ids: Optional[Iterable[int]] = None,
) -> dict[int, list[dict[str, Any]]]:
    """掃出 `{quotation_id: [{code,label,severity,detail}, …]}`。

    `quotation_ids` 給列表用（只問畫面上這一頁的那些張）；
    不給就是全庫掃 —— 四條各一次聚合查詢，256 張的規模是毫秒級。
    """
    wanted = list(codes) if codes else [a.code for a in ANOMALY_TYPES]
    ids = list(quotation_ids) if quotation_ids is not None else None
    if ids is not None and not ids:
        return {}

    out: dict[int, list[dict[str, Any]]] = {}
    for code in wanted:
        spec = BY_CODE.get(code)
        if spec is None:
            continue
        sql = spec.sql
        params: dict[str, Any] = {}
        if ids is not None:
            sql += " AND q.id = ANY(:ids)"
            params["ids"] = ids
        try:
            rows = (await db.execute(text(sql), params)).all()
        except Exception as e:  # noqa: BLE001
            # 吞掉一條判準會讓畫面顯示「沒有異常」——那比顯示錯誤更糟。
            # ⇒ 記成 error（不是 warning）並讓呼叫端知道這一條沒跑成。
            logger.error("異常判準 %s 執行失敗：%s", code, e, exc_info=True)
            raise
        for qid, detail in rows:
            out.setdefault(int(qid), []).append({
                "code": spec.code,
                "label": spec.label,
                "severity": spec.severity,
                "explain": spec.explain,
                "detail": detail,
            })
    return out


async def load_acks(db: AsyncSession, quotation_ids: Optional[Iterable[int]] = None
                    ) -> dict[tuple[int, str], dict[str, Any]]:
    """已判讀紀錄，鍵是 `(quotation_id, anomaly_type)`。"""
    sql = ("SELECT quotation_id, anomaly_type, reason, acked_by, acked_at "
           "FROM erp_finance_anomaly_acks")
    params: dict[str, Any] = {}
    ids = list(quotation_ids) if quotation_ids is not None else None
    if ids is not None:
        if not ids:
            return {}
        sql += " WHERE quotation_id = ANY(:ids)"
        params["ids"] = ids
    rows = (await db.execute(text(sql), params)).all()
    return {
        (int(r[0]), r[1]): {"reason": r[2], "acked_by": r[3],
                            "acked_at": r[4].isoformat() if r[4] else None}
        for r in rows
    }


async def annotate(db: AsyncSession, quotation_ids: Iterable[int]
                   ) -> dict[int, list[dict[str, Any]]]:
    """給列表用：掃異常並貼上判讀狀態。

    **已判讀的不會被濾掉** —— 它仍是異常，只是有人看過了。
    濾掉的話，判讀就等於「讓問題從畫面上消失」，而那正是這個機制要避免的。
    """
    ids = list(quotation_ids)
    found = await scan(db, quotation_ids=ids)
    acks = await load_acks(db, ids)
    for qid, items in found.items():
        for it in items:
            ack = acks.get((qid, it["code"]))
            it["acknowledged"] = ack is not None
            it["ack"] = ack
    return found


async def anomaly_ids(db: AsyncSession, *, only_open: bool = False,
                      codes: Optional[Iterable[str]] = None) -> list[int]:
    """有異常的報價單 id —— 給列表的「僅顯示異常」篩選用。

    `only_open=True` ⇒ 只留**還沒有人判讀**的那些（待處理清單）。
    """
    found = await scan(db, codes=codes)
    if not only_open:
        return sorted(found)
    acks = await load_acks(db, list(found))
    return sorted(
        qid for qid, items in found.items()
        if any((qid, it["code"]) not in acks for it in items)
    )
