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

**連結必須指向詳情頁而非列表加查詢參數**（2026-08-17 owner 回報）——
我原本產 `/erp/quotations?case_code=CK2026_PM_01_005`，
而**列表頁根本沒有讀 query 參數**，點過去只會停在未篩選的列表。
那是「產了一個沒有人在接的連結」——同型的形狀本專案記過多次
（送出端與接收端各說各話，而兩邊都不會報錯）。
產連結時要確認**接收端真的處理那個參數**，不能只看網址長得合理。

**負責人一律取 canonical 帳號**（ADR-0025）—— 首跑時「王駿穠」與
「王駿穠(fly)」被算成兩個人，而 id 7 的 `canonical_user_id` 就是 13。
既有規則在 `core/rls_filter.py`（`COALESCE(canonical_user_id, id)`），
這裡沿用同一條、不自寫第二套。

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
    # 2026-08-17：這個案子還在跑嗎。
    #
    # 實測：32 筆無金額的承攬案件裡 **27 筆已結案**、只有 5 筆執行中；
    # 23 筆無總價的報價裡 17 筆已結案、6 筆執行中。
    # 把 11 筆該現在處理的埋在 55 筆歷史補登裡，就是本專案反覆記錄的告警疲勞
    # —— 清單長到某個程度，人就整份略過，連急件一起。
    active: bool = True


@dataclass
class PersonGaps:
    user_id: Optional[int]
    name: str
    items: list[GapItem] = field(default_factory=list)


# PM 已成案／執行中，但下游**整個不存在**（2026-08-17 補）。
#
# ⚠️ 這一條補的是一個**結構性盲區**：其餘五種缺口全部從下游表出發
# （erp_quotations / contract_projects / erp_billings / erp_vendor_payables /
# expense_invoices），於是「上游說已成案，而下游一列都沒有」在座標系之外
# —— 不是判定寬鬆，是**那一列根本不在被掃描的集合裡**。
#
# 而它恰好是最嚴重的一種：代表「一鍵成案」從未執行、或執行到一半斷了，
# 案子在 PM 看起來已成案、在財務端完全不存在（毛利、應收、核銷全都無從掛載）。
#
# 實測命中 1 筆：CK2026_PM_01_006（contracted、0 報價單、0 承攬案件、
# 合約金額 33 元 —— 那個 33 本身也不可能是真的）。**先報出來讓人看見**，
# 不自動補建：缺的是報價單與承攬案件兩個實體，該由誰、用什麼金額建，
# 機器猜不出來（而猜錯會產生一筆看起來合法的假資料）。
#
# `planning` 排除：評估階段還沒有下游是正常的，不是缺口。
SQL_PM_NO_DOWNSTREAM = """
SELECT pm.id AS row_id, pm.case_code, COALESCE(pm.case_name, '') AS name,
       COALESCE(pm.status, '') AS pm_status, pm.contract_amount,
       u.id AS user_id, COALESCE(u.full_name, u.username, '') AS staff
FROM pm_cases pm
-- PM 案件的負責人在 pm_cases 自己的欄位上（沒有 project_user_assignments
-- 可用 —— 那張表掛在 contract_projects.id 上，而這批案子的痛點正是
-- 「沒有 contract_projects」）。
LEFT JOIN users au ON au.id = pm.created_by
LEFT JOIN users u ON u.id = COALESCE(au.canonical_user_id, au.id)
WHERE COALESCE(pm.status, '') NOT IN ('closed', 'planning', '已結案')
  AND NOT EXISTS (
      SELECT 1 FROM erp_quotations q
       WHERE q.case_code = pm.case_code AND q.deleted_at IS NULL
  )
  AND NOT EXISTS (
      SELECT 1 FROM contract_projects cp WHERE cp.case_code = pm.case_code
  )
ORDER BY pm.case_code
"""

# 承攬案件缺合約金額。
# 負責人取 `is_primary` 優先，沒有 primary 就取任一指派人
# （有人負責總比沒有好；真的沒有指派才歸「未指派」）。
SQL_CONTRACT_NO_AMOUNT = """
SELECT p.id AS row_id, p.case_code, p.project_code, COALESCE(p.project_name, '') AS name,
       p.status,
       u.id AS user_id, COALESCE(u.full_name, u.username, a.staff_name, '') AS staff
FROM contract_projects p
LEFT JOIN LATERAL (
    SELECT x.user_id, x.staff_name
    FROM project_user_assignments x
    WHERE x.project_id = p.id
    ORDER BY x.is_primary DESC NULLS LAST, x.id
    LIMIT 1
) a ON TRUE
-- ADR-0025：以 canonical 人為準，否則同一個人的分身帳號會被算成兩個人
LEFT JOIN users au ON au.id = a.user_id
LEFT JOIN users u ON u.id = COALESCE(au.canonical_user_id, au.id)
WHERE p.contract_amount IS NULL
ORDER BY p.case_code
"""

# 報價缺總價 —— 沒有總價，收入端是空的，毛利無從算起。
SQL_QUOTATION_NO_PRICE = """
SELECT q.id AS row_id, q.case_code, COALESCE(q.case_name, '') AS name,
       COALESCE(p.status, '') AS status,
       u.id AS user_id, COALESCE(u.full_name, u.username, a.staff_name, '') AS staff
FROM erp_quotations q
LEFT JOIN contract_projects p ON p.case_code = q.case_code
LEFT JOIN LATERAL (
    SELECT x.user_id, x.staff_name
    FROM project_user_assignments x
    WHERE x.project_id = p.id
    ORDER BY x.is_primary DESC NULLS LAST, x.id
    LIMIT 1
) a ON TRUE
-- ADR-0025：以 canonical 人為準，否則同一個人的分身帳號會被算成兩個人
LEFT JOIN users au ON au.id = a.user_id
LEFT JOIN users u ON u.id = COALESCE(au.canonical_user_id, au.id)
WHERE q.total_price IS NULL OR q.total_price = 0
ORDER BY q.case_code
"""

# 執行中案件缺**估列成本** —— 2026-08-17 新增。
#
# 有總價只是收入端；沒有成本就算不出毛利。實測對比很清楚：
#
#     已結案 64 張報價 → 47 張有總價、**40 張有估列成本**
#     執行中 14 張報價 →  8 張有總價、**0 張有估列成本**
#
# 而那 40 張的 `updated_at` **全部落在 2026-03-17～04-01**（一次性歷史匯入）。
# 換句話說：**04-04 之後建立的報價，沒有任何一筆填過成本**，已經 4.5 個月。
# 毛利算不出來的真因不是「結案後才回填」，是這個欄位沒有人在用。
SQL_QUOTATION_NO_COST = """
SELECT q.id AS row_id, q.case_code, COALESCE(q.case_name, '') AS name,
       COALESCE(p.status, '') AS status,
       u.id AS user_id, COALESCE(u.full_name, u.username, a.staff_name, '') AS staff
FROM erp_quotations q
JOIN contract_projects p ON p.case_code = q.case_code
LEFT JOIN LATERAL (
    SELECT x.user_id, x.staff_name
    FROM project_user_assignments x
    WHERE x.project_id = p.id
    ORDER BY x.is_primary DESC NULLS LAST, x.id
    LIMIT 1
) a ON TRUE
-- ADR-0025：以 canonical 人為準，否則同一個人的分身帳號會被算成兩個人
LEFT JOIN users au ON au.id = a.user_id
LEFT JOIN users u ON u.id = COALESCE(au.canonical_user_id, au.id)
WHERE p.status <> '已結案'
  -- ⭐ 2026-08-17 owner：「專案包含報價與標案兩類 —— 報價可明列作業單價
  -- 統計成本，而標案涉及多項程序**不易填列成本**」。
  --
  -- ⚠️ **當日改過一次**：原本 `AND p.category = '02'`（只對承攬報價要求成本）。
  -- 那個限縮對「估列成本四欄」是對的，但實測揭露成本還有三個來源，
  -- 而那三個**標案也填得出來**：
  --
  --   · 應付（給廠商的錢）—— 執行中 12 張標案裡 3 張已經有
  --   · 核銷（`expense_invoices`）
  --   · 帳本已入帳支出
  --
  -- 於是判準改為「**完全沒有任何成本資訊**」而不是「沒填估列四欄」。
  -- 這樣既不會要求標案做它做不到的事（逐項估列），
  -- 也不會讓 4 筆「有總價卻連一筆應付／核銷都沒有」的案子完全沒人報
  -- —— 實測就是 4 筆，全部是標案，先前依 category 限縮而靜默。
  --
  -- ⚠️ 判準**必須與 `business_vital_signs.py` 的「毛利可算」一致** ——
  -- 那條指標與這條待辦問的是同一件事（毛利算不算得出來）。
  -- 兩份判準會讓「指標說 23% 而待辦說 0 件」同時成立，
  -- 而不一致時沒有任何一方會報錯（本專案反覆記錄的形狀）。
  AND q.total_price > 0
  AND COALESCE(q.outsourcing_fee,0) + COALESCE(q.personnel_fee,0)
    + COALESCE(q.overhead_fee,0) + COALESCE(q.other_cost,0) = 0
  AND NOT EXISTS (SELECT 1 FROM erp_vendor_payables vp
                   WHERE vp.erp_quotation_id = q.id)
  AND NOT EXISTS (SELECT 1 FROM expense_invoices e
                   WHERE e.case_code = q.case_code)
  AND NOT EXISTS (SELECT 1 FROM finance_ledgers l
                   WHERE l.case_code = q.case_code AND l.entry_type = 'expense')
ORDER BY q.case_code
"""

# ---------------------------------------------------------------------------
# 案件財務待辦（2026-08-17 owner 回報「原機制消失了」後補）
#
# 我在同一天做了三次收窄（核准停用不報卡審核／標案類不要求成本／
# 只推執行中），每一次個別都對，但**疊起來把 owner 的卡片清成 0 項**
# —— 而「0 項不顯示」讓整張卡消失。
#
# 更根本的問題是範圍：filing_gap 原本只涵蓋「**填報**缺口」，
# 而 owner 的目標是「個人專案財務通知與管理」—— 那是更廣的東西。
# 實測 owner 負責 5 個執行中案件、合約金額全部有填（所以不在填報缺口裡），
# 但底下有 **2 筆未收款請款、4 筆未付應付** 完全沒有人通知他。
#
# 這兩類不是「沒填」，是「**該收沒收、該付沒付**」——
# 對案件負責人來說那比填欄位重要得多。
# ---------------------------------------------------------------------------
SQL_UNPAID_BILLING = """
SELECT b.id AS row_id, q.id AS quotation_id, q.case_code, COALESCE(q.case_name,'') AS name,
       b.billing_amount AS amount, b.payment_status,
       (CURRENT_DATE - b.billing_date) AS age_days,
       u.id AS user_id, COALESCE(u.full_name, u.username, a.staff_name, '') AS staff
FROM erp_billings b
JOIN erp_quotations q ON q.id = b.erp_quotation_id
JOIN contract_projects p ON p.case_code = q.case_code
LEFT JOIN LATERAL (
    SELECT x.user_id, x.staff_name FROM project_user_assignments x
    WHERE x.project_id = p.id ORDER BY x.is_primary DESC NULLS LAST, x.id LIMIT 1
) a ON TRUE
LEFT JOIN users au ON au.id = a.user_id
LEFT JOIN users u ON u.id = COALESCE(au.canonical_user_id, au.id)
WHERE p.status <> '已結案' AND b.payment_status <> 'paid'
ORDER BY b.billing_date
"""

SQL_UNPAID_PAYABLE = """
SELECT v.id AS row_id, q.id AS quotation_id, q.case_code, COALESCE(q.case_name,'') AS name,
       v.payable_amount AS amount, v.payment_status, v.vendor_name,
       u.id AS user_id, COALESCE(u.full_name, u.username, a.staff_name, '') AS staff
FROM erp_vendor_payables v
JOIN erp_quotations q ON q.id = v.erp_quotation_id
JOIN contract_projects p ON p.case_code = q.case_code
LEFT JOIN LATERAL (
    SELECT x.user_id, x.staff_name FROM project_user_assignments x
    WHERE x.project_id = p.id ORDER BY x.is_primary DESC NULLS LAST, x.id LIMIT 1
) a ON TRUE
LEFT JOIN users au ON au.id = a.user_id
LEFT JOIN users u ON u.id = COALESCE(au.canonical_user_id, au.id)
WHERE p.status <> '已結案' AND v.payment_status <> 'paid'
ORDER BY v.id
"""

# 核銷卡在審核。
# 這一類的負責人是**送單的人自己**（user_id），不是案件負責人 ——
# 卡住的多半是「送了但忘了它還沒過」。
SQL_EXPENSE_STUCK = """
SELECT e.id, e.inv_num, e.amount, e.status, e.case_code,
       (CURRENT_DATE - e.created_at::date) AS age_days,
       u.id AS user_id, COALESCE(u.full_name, u.username, '') AS staff
FROM expense_invoices e
-- ADR-0025：同上
LEFT JOIN users eu ON eu.id = e.user_id
LEFT JOIN users u ON u.id = COALESCE(eu.canonical_user_id, eu.id)
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

        # 這一條放在最前面：它代表「案子在財務端根本不存在」，
        # 比「存在但少填一欄」嚴重一個量級，不該排在 32 筆缺金額的後面。
        rows = (await self.db.execute(text(SQL_PM_NO_DOWNSTREAM))).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="已成案但財務端不存在",
                ref=r.case_code or "",
                label=(r.name or "")[:28],
                detail=(
                    f"PM 狀態為「{r.pm_status}」，但沒有報價單也沒有承攬案件"
                    f" —— 毛利、應收、核銷都無處掛載"
                ),
                # 連回 PM 案件詳情：要補的是「從這裡建報價單／成案」，
                # 而不是去 ERP 端找一個不存在的東西。
                url=f"/pm/cases/{r.row_id}",
                active=True,
            ))

        rows = (await self.db.execute(text(SQL_CONTRACT_NO_AMOUNT))).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="承攬案件缺合約金額",
                ref=r.case_code or r.project_code or "",
                label=(r.name or "")[:28],
                detail="沒有合約金額 —— 毛利與應收都算不出來",
                url=f"/contract-cases/{r.row_id}",
                active=(r.status or "") != "已結案",
            ))

        rows = (await self.db.execute(text(SQL_QUOTATION_NO_PRICE))).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="報價缺總價",
                ref=r.case_code or "",
                label=(r.name or "")[:28],
                detail="沒有總價 —— 收入端是空的",
                url=f"/erp/quotations/{r.row_id}",
                active=(r.status or "") != "已結案",
            ))

        rows = (await self.db.execute(text(SQL_QUOTATION_NO_COST))).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                # 2026-08-17 改名：原本叫「報價缺估列成本」，但判準已改為
                # 「完全沒有任何成本資訊」（估列／應付／核銷／帳本四者皆無）。
                # 名稱若還寫「估列成本」，看到的人會去填那四個欄位 ——
                # 而實測那四欄自系統上線後從來沒有人填過（有值的 40 張
                # 全部是 2026-03-17 一次性 xlsx 匯入）。記一筆應付或核銷
                # 同樣能解除這個缺口，而那是他們本來就會做的事。
                kind="毛利算不出來（無成本資訊）",
                ref=r.case_code or "",
                label=(r.name or "")[:28],
                # detail 明講**三條路都可以**：不指定一定要填估列四欄，
                # 否則就等於在要求標案做它做不到的事（owner 08-17 的原話）。
                detail=(
                    "有總價但完全沒有成本資訊 —— 毛利算不出來。"
                    "填估列成本、或記一筆應付、或核銷一張發票，任一即可"
                ),
                url=f"/erp/quotations/{r.row_id}",
                active=True,   # 這條 SQL 本身就排除了已結案
            ))

        rows = (await self.db.execute(text(SQL_UNPAID_BILLING))).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="請款未收款",
                ref=f"{r.case_code or ''} #{r.row_id}",
                label=f"{int(r.amount or 0):,} 元",
                detail=f"請款已 {r.age_days} 天未收（{r.payment_status}）",
                # ⚠️ 請款/應付**沒有自己的詳情路由**（08-02 隨 BillingsTab 一起移除），
                # 它們只存在於報價詳情的分頁裡。所以連到報價 + `?tab=`
                # —— `?tab=` 是 08-15 才支援的，不能憑印象假設它可用（已查證）。
                url=f"/erp/quotations/{r.quotation_id}?tab=receivable",
                active=True,
            ))

        rows = (await self.db.execute(text(SQL_UNPAID_PAYABLE))).all()
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="應付未付款",
                # ref 帶單據序號 —— 實測 CK2026_PM_01_005 有**兩筆**同廠商同金額的
                # 應付（id 65/66，description 皆空）。只顯示案號的話兩行長得一模一樣，
                # 使用者會以為是畫面重複而略過它們（而其中一筆可能真的是重複建立）。
                ref=f"{r.case_code or ''} #{r.row_id}",
                label=f"{(r.vendor_name or '')[:12]} {int(r.amount or 0):,} 元",
                detail=f"應付尚未付款（{r.payment_status}）",
                url=f"/erp/quotations/{r.quotation_id}?tab=payable",
                active=True,
            ))

        # 2026-08-17：核准機制暫緩時不報「卡在審核」——
        # 沒有核准這個動作，就沒有人卡得住它。繼續報等於製造一個
        # **沒有人能處理**的待辦，那正是告警疲勞的來源。
        from app.schemas.erp.expense import EXPENSE_APPROVAL_ENABLED
        rows = (await self.db.execute(
            text(SQL_EXPENSE_STUCK), {"stuck_days": stuck_days}
        )).all() if EXPENSE_APPROVAL_ENABLED else []
        for r in rows:
            bucket(r.user_id, r.staff).items.append(GapItem(
                kind="核銷卡在審核",
                ref=r.inv_num or str(r.id),
                label=f"{int(r.amount or 0):,} 元",
                detail=f"停在「{r.status}」已 {r.age_days} 天",
                url=f"/erp/expenses/{r.id}",
            ))

        for pg in by_person.values():
            # 執行中的排前面 —— 清單長到某個程度人就整份略過，
            # 急件不能埋在歷史補登下面。
            pg.items.sort(key=lambda i: (not i.active, i.kind, i.ref))

        people = sorted(
            by_person.values(),
            key=lambda p: (
                p.name == UNASSIGNED,
                -sum(1 for i in p.items if i.active),   # 先看誰的急件多
                -len(p.items),
                p.name,
            ),
        )
        total = sum(len(p.items) for p in people)
        active_total = sum(1 for p in people for i in p.items if i.active)
        return {
            "total": total,
            # **執行中的數量才是要行動的量** —— total 62 裡有 51 筆是已結案的
            # 歷史補登，用 total 當標題會讓人以為有 62 件急事。
            "active_total": active_total,
            "closed_total": total - active_total,
            "people": [
                {
                    "user_id": p.user_id,
                    "name": p.name,
                    "count": len(p.items),
                    "active_count": sum(1 for i in p.items if i.active),
                    "items": [vars(i) for i in p.items],
                }
                for p in people
            ],
        }

    async def for_user(self, user_id: int, stuck_days: int = 3) -> dict[str, Any]:
        """單一使用者的待填報 —— 給「我的待辦」用。"""
        data = await self.collect(stuck_days=stuck_days)
        mine = [p for p in data["people"] if p["user_id"] == user_id]
        items = [i for p in mine for i in p["items"]]
        return {
            "total": len(items),
            "active_total": sum(1 for i in items if i.get("active")),
            "items": items,
        }

    def to_digest_text(self, data: dict[str, Any], max_people: int = 6) -> str:
        """組成晨報要帶的一段文字。

        **只講人與數量，不列明細** —— 明細在系統裡點得到，
        而一則塞滿 60 行的推播只會被略過（本專案記過的告警疲勞）。

        2026-08-17：**只推執行中的**。實測 62 項裡有 44 項是已結案案件的
        歷史補登 —— 每天推一則「還有 62 項待填」會讓人以為有 62 件急事，
        而真正該今天處理的只有 18 項。清單長到某個程度人就整份略過，
        連急件一起（本專案反覆記錄的告警疲勞）。
        """
        active = data.get("active_total", data["total"])
        if not active:
            # 只剩已結案的歷史補登就不推 —— 那不是今天要做的事。
            return ""

        lines = [f"案件待辦 {active} 項（執行中）："]
        for p in data["people"][:max_people]:
            if not p.get("active_count"):
                continue
            kinds: dict[str, int] = {}
            for it in p["items"]:
                if it.get("active"):
                    kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
            brief = "、".join(f"{k} {v}" for k, v in kinds.items())
            lines.append(f"　{p['name']}：{brief}")

        closed = data.get("closed_total", 0)
        if closed:
            # 歷史補登只講一個數字、不列人 —— 它是背景資訊不是待辦
            lines.append(f"　（另有已結案歷史補登 {closed} 項，非急件）")
        return "\n".join(lines)
