"""從標案建案 —— 單一實作。

## 為什麼這支存在（2026-08-16）

「從標案建立 PM 案件」原本有**兩份各自獨立的實作**：

| | 一鍵建案（`graph_case.py`）| AI 工具（`auto_tender_to_case`）|
|---|---|---|
| 查重 | 5 道 | 1 道（只比案名、只查 pm_cases）|
| 委託單位 | 查找或建立 PartnerVendor | 沒有 |
| 合約金額 | 由標案 budget 帶入 | 沒寫 |
| 來源標案回指 | 有 | 沒有 |
| **邀標階段的報價單** | **刻意不建** | **建了，`total_price=0`** |

那 5 道查重每一道都是踩過坑才加的（註解裡寫著「案件 187 即為…」「實測 87 承攬
案件中 33 筆有相似標案」），而 AI 工具**一道都沒有繼承**。更嚴重的是最後一列：
兩份對「邀標階段要不要建報價單」的答案是**相反的** —— 那不是欄位漏寫，是業務規則
分歧，而**兩邊都不會報錯**（本專案反覆記錄的那個形狀）。

實際後果 owner 已經遇到：和美案「已承攬但金額空白」。

**修法不是把第二份補成跟第一份一樣** —— 那只會得到兩份今天湊巧一致、明天再度
漂移的副本。入口可以有很多個（按鈕／對話／未來的匯入），但底下的業務操作只能有
一份，就是這裡。

## 不包含什麼

- **手動建案**（`pm/case_service.create`）不走這裡：它不是從標案來的，查重條件
  （案名＋年度）與必填欄位都不同，硬合併就是過度抽象。
- **成案**（`contract/case_code.promote_to_project`）不走這裡：那是後面的階段。
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TenderCaseDuplicateError(Exception):
    """此標案已經建過案。

    刻意不用 HTTPException —— 服務層不該知道 HTTP。
    端點自己轉 409，AI 工具則是跳過並記錄。
    """

    def __init__(self, message: str, existing_code: str = ""):
        super().__init__(message)
        self.existing_code = existing_code


def parse_budget(raw: Any) -> Optional[int]:
    """把標案的預算欄位轉成金額。

    來源格式很雜（`"1,234,567"`／`"新臺幣 123 萬元"`／數字／None），
    取得出數字就用，取不到回 None。

    ⚠️ 回 None 而不是 0：**「沒有填」與「真的是零」意義不同**。
    給 0 會讓報價單一建立就是「成本 0、毛利率 100%」。
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw) if raw > 0 else None
    nums = re.sub(r"[^\d.]", "", str(raw).replace(",", ""))
    if not nums:
        return None
    try:
        val = int(float(nums))
    except ValueError:
        return None
    return val if val > 0 else None


class TenderCaseCreationService:
    """從標案建立 PM 案件（含查重、委託單位、金額帶入、來源回指）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_from_tender(
        self,
        *,
        title: str,
        unit_id: str = "",
        unit_name: str = "",
        job_number: Optional[str] = None,
        budget: Any = None,
        tender_id: Optional[int] = None,
        category: str = "01",
        created_by: Optional[int] = None,
        source_label: str = "政府標案",
    ) -> Dict[str, Any]:
        """建立 PM 案件並回傳 {case_code, pm_case_id, contract_amount, ...}。

        重複時拋 `TenderCaseDuplicateError`（不 commit）。
        **本方法不 commit** —— 交易邊界交給呼叫端決定，
        AI 工具一次建多筆時才能一起成功或一起退回。
        """
        from app.extended.models.core import ContractProject, PartnerVendor
        from app.extended.models.erp import ERPQuotation
        from app.extended.models.pm import PMCase
        from app.services.contract import CaseCodeService

        # 標案識別碼（L1）：ezbid 來源無 job_number（全庫 37,980 筆皆 NULL），
        # 改以 ezbid:{unit_id} 作為識別，讓 ezbid 也能進入鏈路且查得了重。
        tender_ref = (job_number or "").strip() or f"ezbid:{unit_id}"

        await self._assert_not_duplicate(
            title=title, tender_ref=tender_ref, tender_id=tender_id,
            PMCase=PMCase, ContractProject=ContractProject,
        )

        budget_amount = parse_budget(budget)
        year = date.today().year
        case_code = await CaseCodeService(self.db).generate_case_code(
            "pm", year, category or "01",
        )
        client_vendor_id = await self._ensure_client_vendor(
            unit_name, tender_ref, PartnerVendor,
        )

        pm_case = PMCase(
            case_code=case_code,
            case_name=title[:200],
            year=year,
            status="bidding",
            contract_amount=budget_amount,
            client_vendor_id=client_vendor_id,
            # L3 回指：結構化記錄來源標案，讓案件頁看得到標案、標案頁看得到案件。
            source_tender_id=tender_id,
            created_by=created_by,
            notes=f"來源: {source_label} {tender_ref} ({unit_name})",
        )
        self.db.add(pm_case)
        await self.db.flush()

        # 2026-08-17 owner：「建構線上報價單機制，統整邀標報價程序」。
        #
        # **推翻 08-16 的「邀標階段不建立報價單」。**
        #
        # 那條規則的原意是「不要造出一堆 total_price=0 的空報價」，
        # 但實測揭露它造成更嚴重的後果：報價單只在 `promote_to_project`
        # （成案）時建立 → **有報價單的邀標案件 0 筆** →
        # 08-16 我建的線上報價明細掛在一個「要先得標才存在」的物件上，
        # 而報價是投標**前**的動作。
        #
        # 正確的解法不是延後報價單的出生，是**讓它一開始就有東西可填**。
        # `status='draft'` 的語意剛好對（78 張裡只有 2 張用過 draft）。
        quotation_no = await CaseCodeService(self.db).generate_quotation_no(year)
        self.db.add(ERPQuotation(
            case_code=case_code,
            case_name=title[:200],
            year=year,
            quotation_no=quotation_no,
            revision=1,
            # 刻意**不帶**標案預算作為報價金額 —— 那是機關的預算上限，
            # 不是我們要報的價。報價金額由明細加總得出（見 quotation_items）。
            total_price=None,
            status="draft",
            # 01 是投標報價、02 是承攬報價 —— 表上要寫明，不能只靠 case_code 段落
            quote_kind=("tender" if (category or "01") == "01" else "contract"),
            notes=f"由{source_label} {tender_ref} 建案時同時開立",
        ))
        await self.db.flush()

        if budget_amount is None:
            # 不擋，但要留下痕跡：金額缺失會一路帶到成案與財務，
            # 而成案時的守衛會擋下來 —— 屆時要查得到「當初就沒有」。
            logger.info(
                "[建案] %s 來源標案無金額（tender_ref=%s）—— 成案前需人工補填",
                case_code, tender_ref,
            )

        return {
            "case_code": case_code,
            "pm_case_id": pm_case.id,
            "contract_amount": budget_amount,
            "client_vendor_id": client_vendor_id,
            "tender_ref": tender_ref,
            "quotation_no": quotation_no,
        }

    # ------------------------------------------------------------------

    async def _assert_not_duplicate(
        self, *, title: str, tender_ref: str, tender_id: Optional[int],
        PMCase, ContractProject,
    ) -> None:
        """5 道查重，任一命中即擋。每一道都是踩過坑才加的，不要拿掉。"""
        # ①② source_tender_id 精確回指 + notes 內含標案識別碼（相容既有資料）
        # ③ 案名完全相同 —— 原本完全沒有這道，ezbid 因無 job_number 而查重整段
        #   被跳過，按幾次就建幾個案。
        conds = [PMCase.notes.ilike(f"%{tender_ref}%"), PMCase.case_name == title[:200]]
        if tender_id:
            conds.append(PMCase.source_tender_id == tender_id)
        existing = (await self.db.execute(select(PMCase).where(or_(*conds)))).scalars().first()
        if existing:
            raise TenderCaseDuplicateError(
                f"此標案已建案: {existing.case_code} ({(existing.case_name or '')[:30]})",
                existing.case_code,
            )

        # ④⑤ 承攬案件端也要查 —— 案件 187 即為「直接建立承攬案件、從未走過建案」
        #    的型態，只查 pm_cases 會漏掉，導致同一案在兩個模組各存一份。
        cp_conds = [ContractProject.project_name == title[:200]]
        if tender_id:
            cp_conds.append(ContractProject.source_tender_id == tender_id)
        existing_cp = (
            await self.db.execute(select(ContractProject).where(or_(*cp_conds)))
        ).scalars().first()
        if existing_cp:
            raise TenderCaseDuplicateError(
                f"已有同名承攬案件: {existing_cp.project_code} "
                f"({(existing_cp.project_name or '')[:30]})，"
                f"請改用「關聯到既有案件」避免重複",
                existing_cp.project_code or "",
            )

    async def _ensure_client_vendor(
        self, unit_name: str, tender_ref: str, PartnerVendor,
    ) -> Optional[int]:
        """招標機關 → 委託單位（查找或建立）。

        沒有這一步的話，案件建出來是沒有委託單位的，
        而委託單位是後續應收帳款的對象。
        """
        if not unit_name:
            return None
        existing = (
            await self.db.execute(
                select(PartnerVendor).where(
                    PartnerVendor.vendor_name == unit_name,
                    PartnerVendor.vendor_type == "client",
                )
            )
        ).scalars().first()
        if existing:
            return existing.id

        new_client = PartnerVendor(
            vendor_name=unit_name,
            vendor_type="client",
            notes=f"[標案自動建立] {tender_ref}",
        )
        self.db.add(new_client)
        await self.db.flush()
        return new_client.id
