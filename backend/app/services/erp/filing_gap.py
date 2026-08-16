"""填報缺口 —— 誰該填、還沒填什麼。

## 為什麼有這支（2026-08-16）

owner：「承攬報價案件對應填報人員通報管控」。

實測缺口（同日量測）：

    承攬案件 89 筆 → **32 筆沒有合約金額**（36%）
    報價單   78 筆 → **23 筆沒有總價**（29%）
    核銷      9 筆 → **6 筆卡在審核**（其中 4 筆自 7/31 起 16 天沒動）
    → 毛利算得出來的只有 40/78（51%）

**這些不是系統故障，是沒有人知道自己該去填。** 系統裡沒有任何機制在問
「這個案件的資料誰負責、缺的東西通知了誰」——缺口就這樣一直躺著，
而畫面上只是一個空欄位，看起來像「還沒到」。

## 設計取捨

**不新增負責人欄位** —— `project_user_assignments` 已經有
`is_primary`（主要負責人），43 筆指派涵蓋 26 個專案。
再加一個欄位就是第二份事實（本專案反覆踩的那個形狀）。

**不新建通知管道** —— 走既有的 `line_digest_buffer`，
由 07:30 晨報一次帶出。核銷卡了 16 天沒人知道，不是因為少一個通道，
是因為沒有人在算這件事。

**找不到負責人的缺口要單獨列出，不可以吞掉** ——
實測 32 筆無金額的承攬案件裡有 14 筆完全沒有指派人。
把它們算進「未指派」比假裝沒有這些缺口誠實。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

UNASSIGNED = "（未指派負責人）"


@dataclass
class GapItem:
    kind: str          # 缺什麼
    ref: str           # 案號或單號
    label: str         # 給人看的名稱
    detail: str        # 缺口說明
    url: str           # 直接可以點進去填的地方


@dataclass
class PersonGaps:
    user_id: Optional[int]
    name: str
    items: list[GapItem] = field(default_factory=list)


# 承攬案件缺合約金額。
# 負責人取 `is_primary` 優先，沒有 primary 就取任一指派人
# （有人負責總比沒有好；真的沒有指派才歸「未指派」）。
SQL_CONTRACT_NO_AMOUNT = """
SELECT p.case_code, p.project_code, COALESCE(p.project_name, '') AS name,
       a.user_id, COALESCE(u.full_name, u.username, a.staff_name, '') AS staff
FROM contract_projects p
LEFT JOIN LATERAL (
    SELECT x.user_id, x.staff_name
    FROM project_user_assignments x
    WHERE x.project_id = p.id
    ORDER BY x.is_primary DESC NULLS LAST, x.id
    LIMIT 1
) a ON TRUE
LEFT JOIN users u ON u.id = a.user_id
WHERE p.contract_amount IS NULL
ORDER BY p.case_code
"""

# 報價缺總價 —— 沒有總價，收入端是空的，毛利無從算起。
SQL_QUOTATION_NO_PRICE = """
SELECT q.case_code, COALESCE(q.case_name, '') AS name,
       a.user_id, COALESCE(u.full_name, u.username, a.staff_name, '') AS staff
FROM erp_quotations q
LEFT JOIN contract_projects p ON p.case_code = q.case_code
LEFT JOIN LATERAL (
    SELECT x.user_id, x.staff_name
    FROM project_user_assignments x
    WHERE x.project_id = p.id
    ORDER BY x.is_primary DESC NULLS LAST, x.id
    LIMIT 1
) a ON TRUE
LEFT JOIN users u ON u.id = a.user_id
WHERE q.total_price IS NULL OR q.total_price = 0
ORDER BY q.case_code
"""

# 核銷卡在審核。
# 這一類的負責人是**送單的人自己**（user_id），不是案件負責人 ——
# 卡住的多半是「送了但忘了它還沒過」。
SQL_EXPENSE_STUCK = """
SELECT e.id, e.inv_num, e.amount, e.status, e.case_code,
       (CURRENT_DATE - e.created_at::date) AS age_days,
       e.user_id, COALESCE(u.full_name, u.username, '') AS staff
FROM expense_invoices e
LEFT JOIN users u ON u.id = e.user_id
WHERE e.status IN ('pending', 'manager_approved', 'finance_approved')
  AND (CURRENT_DATE - e.created_at::date) >= :stuck_days
ORDER BY e.created_at
"""


class FilingGapService:
    """算出「誰還沒填什麼」。**唯讀**，不改任何資料。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def collect(self, stuck_days: int = 3) -> dict[str, Any]:
        by_person: dict[str, PersonGaps] = {}

        def bucket(user_id: Optional[int], staff: str) -> PersonGaps:
            name = (staff or "").strip() or UNASSIGNED
            key = f"{user_id}:{name}" if user_id else name
            if key not in by_person:
                by_person[key] = PersonGaps(user_id=user_id, name=name)
            return by_person[key]

        rows = (await self.db.execute(text(SQL_CONTRACT_NO_AMOUNT))).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="承攬案件缺合約金額",
                ref=r.case_code or r.project_code or "",
                label=(r.name or "")[:28],
                detail="沒有合約金額 —— 毛利與應收都算不出來",
                url=f"/contract-cases?case_code={r.case_code or ''}",
            ))

        rows = (await self.db.execute(text(SQL_QUOTATION_NO_PRICE))).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="報價缺總價",
                ref=r.case_code or "",
                label=(r.name or "")[:28],
                detail="沒有總價 —— 收入端是空的",
                url=f"/erp/quotations?case_code={r.case_code or ''}",
            ))

        rows = (await self.db.execute(
            text(SQL_EXPENSE_STUCK), {"stuck_days": stuck_days}
        )).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="核銷卡在審核",
                ref=r.inv_num or str(r.id),
                label=f"{int(r.amount or 0):,} 元",
                detail=f"停在「{r.status}」已 {r.age_days} 天",
                url=f"/erp/expenses/{r.id}",
            ))

        people = sorted(
            by_person.values(),
            key=lambda p: (p.name == UNASSIGNED, -len(p.items), p.name),
        )
        total = sum(len(p.items) for p in people)
        return {
            "total": total,
            "people": [
                {
                    "user_id": p.user_id,
                    "name": p.name,
                    "count": len(p.items),
                    "items": [vars(i) for i in p.items],
                }
                for p in people
            ],
        }

    async def for_user(self, user_id: int, stuck_days: int = 3) -> dict[str, Any]:
        """單一使用者的待填報 —— 給「我的待辦」用。"""
        data = await self.collect(stuck_days=stuck_days)
        mine = [p for p in data["people"] if p["user_id"] == user_id]
        return {
            "total": sum(p["count"] for p in mine),
            "items": [i for p in mine for i in p["items"]],
        }

    def to_digest_text(self, data: dict[str, Any], max_people: int = 6) -> str:
        """組成晨報要帶的一段文字。

        **只講人與數量，不列明細** —— 明細在系統裡點得到，
        而一則塞滿 60 行的推播只會被略過（本專案記過的告警疲勞）。
        """
        if not data["total"]:
            return ""
        lines = [f"📋 待填報 {data['total']} 項："]
        for p in data["people"][:max_people]:
            kinds: dict[str, int] = {}
            for it in p["items"]:
                kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
            brief = "、".join(f"{k} {v}" for k, v in kinds.items())
            lines.append(f"　{p['name']}：{brief}")
        rest = len(data["people"]) - max_people
        if rest > 0:
            lines.append(f"　⋯另 {rest} 人")
        return "\n".join(lines)
