# -*- coding: utf-8 -*-
"""財務健檢摘要 —— 把散在各支稽核的結果收斂成一則「今天要看的」（2026-09-07）。

owner：「建立相關專案、財務等智能檢核與提醒機制，降低人工重複複核」。

## 為什麼是「摘要」而不是「再寫一支稽核」

檢核已經夠多了（weekly 99／104／106／107／117、daily 16 業務鏈探針）。人工重複複核的成本
不在「沒有檢核」，在**要人自己去七個地方看、還要自己判斷哪一條今天變了**。

⇒ 這一支只做三件事：
1. **一次查完**：所有需要人處理的財務異常（不是機制故障，是資料要人補的那種）
2. **只講變化**：與上一次的快照比對，新增的才推播；沒有變化就安靜
3. **落點正確**：進**站內通知 + 個人儀表板**，不是 LINE 推播
   （owner 2026-09-03 明確糾正過：承辦個人的稽催資訊落點是儀表板與站內通知）

## 判準（每一條都是「人要做一個動作」，不是「系統壞了」）

| 條目 | 為什麼要人看 |
|---|---|
| 已收款卻沒有發票（且結算方式是要開票） | 該開的票沒開 —— 稅務風險 |
| 發票額 ≠ 請款額 | 兩邊有一邊填錯，帳會對不起來 |
| 一票多案的分攤合計 ≠ 發票金額 | 有錢沒有落在任何一個案上 |
| 互抵／不開票沒有寫依據 | 事後無法與「漏開發票」分辨 |
| 應付沒有 `billing_id` | 「這筆應付對哪次請款」答不出來 |
| 廠商名對得到主檔卻沒填鍵 | 名稱是快照、鍵才是關聯 |
| 執行中 >365 天 0 請款 | 可能收了沒登，也可能真的忘了請款 |

**刻意不含**：金額語意類的存量問題（那是 weekly 104 的名冊在追），以及任何「系統故障」
（那是 daily runner 的事）。這一支只回答「今天有沒有新的、要人動手的財務缺口」。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SNAPSHOT = Path("/app/wiki/memory/integration-health/finance_digest_snapshot.json")

#: (鍵, 標題, SQL) —— 每一條都回「筆數 + 前幾筆的識別」
CHECKS: list[tuple[str, str, str]] = [
    ("paid_no_invoice", "已收款但沒有發票", """
        SELECT b.id, COALESCE(q.case_code, '') || ' ' || COALESCE(b.billing_period, '') AS label,
               b.payment_amount AS amount
        FROM erp_billings b LEFT JOIN erp_quotations q ON q.id = b.erp_quotation_id
        WHERE b.payment_status IN ('paid','partial')
          AND COALESCE(b.settlement_type, 'invoice') = 'invoice'
          AND NOT EXISTS (SELECT 1 FROM erp_invoices i WHERE i.billing_id = b.id AND i.status <> 'voided')
        ORDER BY b.payment_amount DESC NULLS LAST LIMIT 50
    """),
    ("invoice_ne_billing", "發票額與請款額不一致", """
        SELECT i.id, COALESCE(i.invoice_number, '') AS label, i.amount
        FROM erp_invoices i JOIN erp_billings b ON b.id = i.billing_id
        WHERE i.status <> 'voided' AND abs(COALESCE(i.amount,0) - COALESCE(b.billing_amount,0)) > 1
        ORDER BY abs(COALESCE(i.amount,0) - COALESCE(b.billing_amount,0)) DESC LIMIT 50
    """),
    ("allocation_mismatch", "一票多案的分攤合計與發票金額不符", """
        SELECT i.id, COALESCE(i.invoice_number, '') AS label, i.amount
        FROM erp_invoices i
        WHERE EXISTS (SELECT 1 FROM erp_invoice_allocations a WHERE a.invoice_id = i.id)
          AND abs(COALESCE(i.amount,0) -
                  COALESCE((SELECT sum(a.amount) FROM erp_invoice_allocations a WHERE a.invoice_id = i.id), 0)) > 1
        LIMIT 50
    """),
    ("offset_without_reason", "互抵／不開票沒有寫依據", """
        SELECT b.id, COALESCE(b.billing_code, '') AS label, b.billing_amount AS amount
        FROM erp_billings b
        WHERE COALESCE(b.settlement_type,'invoice') IN ('offset','no_invoice')
          AND COALESCE(btrim(b.settlement_note), '') = ''
        LIMIT 50
    """),
    ("payable_no_billing", "應付沒有對應的請款", """
        SELECT p.id, COALESCE(p.vendor_name, '') AS label, p.payable_amount AS amount
        FROM erp_vendor_payables p
        WHERE p.billing_id IS NULL AND COALESCE(p.payable_amount, 0) > 0
        LIMIT 50
    """),
    ("name_without_key", "廠商名對得到主檔卻沒有填鍵", """
        SELECT p.id, p.vendor_name AS label, p.payable_amount AS amount
        FROM erp_vendor_payables p
        WHERE p.vendor_id IS NULL AND EXISTS (
            SELECT 1 FROM partner_vendors v WHERE btrim(v.vendor_name) = btrim(p.vendor_name))
        LIMIT 50
    """),
    ("long_running_no_billing", "執行中超過 365 天且尚未請款", """
        SELECT c.id, c.case_code AS label, c.contract_amount AS amount
        FROM contract_projects c
        WHERE c.status IN ('in_progress','executing')
          AND c.created_at < now() - interval '365 days'
          AND NOT EXISTS (
              SELECT 1 FROM erp_billings b JOIN erp_quotations q ON q.id = b.erp_quotation_id
              WHERE q.case_code = c.case_code)
        LIMIT 50
    """),
]


async def collect(db: AsyncSession) -> dict[str, Any]:
    """跑完所有條目，回 {鍵: {"title", "count", "items"}}。單條失敗不影響其他條。"""
    out: dict[str, Any] = {}
    for key, title, sql in CHECKS:
        try:
            rows = (await db.execute(text(sql))).all()
        except Exception as exc:  # noqa: BLE001 —— 一條壞掉不該讓整份摘要消失
            out[key] = {"title": title, "count": None, "error": str(exc)[:120], "items": []}
            continue
        out[key] = {
            "title": title,
            "count": len(rows),
            "items": [{"id": r[0], "label": str(r[1] or "")[:40],
                       "amount": float(r[2]) if r[2] is not None else None} for r in rows[:5]],
        }
    return out


def _load_snapshot() -> dict[str, Any]:
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_snapshot(data: dict[str, Any]) -> None:
    try:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def diff_against_snapshot(current: dict[str, Any]) -> list[str]:
    """回「今天新增的」那幾條的人話描述；沒有新增回空 list。

    只比**新增的 id**，不比筆數 —— 筆數一樣但換了一筆，那也是新的東西要看。
    """
    prev = _load_snapshot().get("ids", {})
    lines: list[str] = []
    for key, title, _sql in CHECKS:
        cur_ids = {str(i["id"]) for i in (current.get(key, {}).get("items") or [])}
        new_ids = cur_ids - set(prev.get(key, []))
        cnt = current.get(key, {}).get("count")
        if new_ids and cnt:
            sample = "、".join(
                f"{i['label']}" for i in current[key]["items"] if str(i["id"]) in new_ids
            )[:60]
            lines.append(f"{title}：{cnt} 筆（新增 {len(new_ids)}：{sample}）")
    return lines


def save_current(current: dict[str, Any]) -> None:
    _save_snapshot({
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ids": {k: [str(i["id"]) for i in (v.get("items") or [])] for k, v in current.items()},
        "counts": {k: v.get("count") for k, v in current.items()},
    })


async def run_and_notify(db: AsyncSession, *, notify: bool = True) -> dict[str, Any]:
    """跑一次健檢；有**新增**才發站內通知（沒變化就安靜）。回本次結果供排程記錄。"""
    current = await collect(db)
    new_lines = diff_against_snapshot(current)
    total = sum(v.get("count") or 0 for v in current.values())

    if notify and new_lines:
        from app.services.notification.helpers import _safe_create_notification
        await _safe_create_notification(
            notification_type="finance_health",
            severity="warning",
            title=f"財務健檢：{len(new_lines)} 類有新增項目",
            message="\n".join(f"• {l}" for l in new_lines)
                    + "\n\n（只列今天新增的；完整清單見財務儀表板）",
            dedupe_key=f"finance_health:{datetime.now().date()}",
        )
    save_current(current)
    return {"total": total, "new": new_lines, "detail": current}
