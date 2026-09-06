"""報價明細（線上報價單）—— 2026-08-16

owner：「線上報價單機制」。

## 設計要點

**`total_price` 由明細加總得出，不再獨立維護。**
在此之前它是一個人手填的數字，而 78 張報價裡 23 張是空的 ——
因為人手上有的是逐項內容，系統卻只給一個空格叫他填總數。

**沒有明細時不動 `total_price`** —— 既有 55 張有總價、無明細的報價
不得因為「明細是空的」就被歸零。空明細代表「還沒逐項拆」，
不代表「這張報價是 0 元」，兩者意義完全不同。
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPQuotation, ERPQuotationItem

logger = logging.getLogger(__name__)


def _money(v: Any) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    return Decimal(str(v))


class QuotationItemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_items(self, quotation_id: int) -> list[ERPQuotationItem]:
        rows = await self.db.execute(
            select(ERPQuotationItem)
            .where(ERPQuotationItem.quotation_id == quotation_id)
            .order_by(ERPQuotationItem.sort_order, ERPQuotationItem.id)
        )
        return list(rows.scalars().all())

    async def replace_items(
        self, quotation_id: int, items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """整批取代明細並回寫總價。

        用「整批取代」而不是逐筆 CRUD：報價明細是一份表格，
        使用者的心智模型是「改完這張表按儲存」，不是「刪第 3 列」。
        逐筆 API 會讓前端得自己算差異，而那個差異算錯不會有人發現。
        """
        quotation = (await self.db.execute(
            select(ERPQuotation).where(ERPQuotation.id == quotation_id)
        )).scalar_one_or_none()
        if not quotation:
            raise ValueError(f"報價 {quotation_id} 不存在")

        for old in await self.list_items(quotation_id):
            await self.db.delete(old)
        await self.db.flush()

        total = Decimal("0")
        for idx, raw in enumerate(items):
            name = (raw.get("item_name") or "").strip()
            if not name:
                # 空白列直接跳過 —— 表格編輯常留下空列，
                # 存成一筆沒有名稱的明細只會讓報價單多一行空白。
                continue
            qty = _money(raw.get("qty", 1))
            price = _money(raw.get("unit_price", 0))
            # 複價可覆寫（2026-09-04）：給了就用給的，否則數量×單價
            amount = (_money(raw["amount"]) if raw.get("amount") is not None
                      else (qty * price)).quantize(Decimal("0.01"))
            total += amount
            self.db.add(ERPQuotationItem(
                quotation_id=quotation_id,
                item_no=((raw.get("item_no") or "").strip()[:20] or None),
                item_name=name[:200],
                spec=(raw.get("spec") or None),
                unit=(raw.get("unit") or None),
                qty=qty,
                unit_price=price,
                amount=amount,
                sort_order=raw.get("sort_order", idx),
                notes=(raw.get("notes") or None),
            ))

        count = sum(1 for r in items if (r.get("item_name") or "").strip())
        if count:
            # 2026-09-06 部署探針鏈 B 抓到兩個斷點：
            #  ① 這裡把**未稅小計**寫進 total_price，而 FIELD_SEMANTICS 自 09-02 起定義 total_price＝**含稅總價**
            #    （請款、發票、承攬金額都對著它）⇒ 填了工項的報價單會比別張少 5%。改寫含稅：小計×1.05，稅＝小計×5%。
            #  ② 總價只回寫報價單，PM 的合約金額沒跟著動 ⇒ 使用者填完工項按「成案」被擋「尚未填寫合約金額」，
            #    得手抄同一個數字——「每張表單獨看都正常，鏈才是斷的」（L140）。同步到 PM／承攬案的 contract_amount。
            #  ③ 已有請款的報價單不得經由工項改總價（與 quotation_service.update 同一把鎖）。
            from app.extended.models.erp import ERPBilling
            from app.extended.models.pm import PMCase
            from app.extended.models.core import ContractProject
            from sqlalchemy import func as _fn
            gross = (total * Decimal("1.05")).quantize(Decimal("1"))
            if quotation.total_price is not None and Decimal(str(quotation.total_price)) != gross:
                n_bill = (await self.db.execute(select(_fn.count(ERPBilling.id)).where(ERPBilling.erp_quotation_id == quotation_id))).scalar()
                n_bill = n_bill if isinstance(n_bill, int) else 0
                if n_bill:
                    raise ValueError(
                        f"此報價單已有 {n_bill} 筆請款，不可經由工項改總價（請款額與發票額都對著它）；"
                        f"要調整請以新版次送出並同步調整請款。"
                    )
            quotation.total_price = gross
            if quotation.case_code:
                pm = (await self.db.execute(select(PMCase).where(PMCase.case_code == quotation.case_code))).scalar_one_or_none()
                if pm is not None:
                    pm.contract_amount = float(gross)
                cp = (await self.db.execute(select(ContractProject).where(ContractProject.case_code == quotation.case_code))).scalar_one_or_none()
                if cp is not None:
                    cp.contract_amount = float(gross)
            # ⚠️ 2026-08-26：稅額必須跟著小計重算，否則 `detail` 會回
            # **新小計 ＋ 舊稅額**，那在算術上就是錯的。
            # 端到端實測抓到：小計改成 8,000 之後，稅額仍是舊的 12,656
            # （原總價 253,120 的 5%），total 算出 20,656。
            #
            # 這個 bug 一直沒有真實發生，因為 `erp_quotation_items`
            # **0 筆 / 256 張** —— 沒有人用過線上明細。接通之後就會發生。
            #
            # ⚠️ 順帶查出 `total_price` 這個欄位**混了兩種語意**：
            #     147 張  tax = total × 5.00%      ⇒ total 是**未稅**
            #      66 張  tax = total × 4.76%      ⇒ 4.76% = 5/105，
            #                                        ⇒ total 是**含稅**
            # 明細小計依定義必然是**未稅**（單價 × 數量），所以這裡按未稅算。
            # 使用者一旦改用明細填報，那張的語意就統一到未稅 —— 這是收斂
            # 不是破壞，但**只在他真的填了明細時才發生**，不動沒有明細的。
            #
            # 5% 是法定營業稅率，此處寫死；若日後要可設定，
            # 照既有的 `site_configurations.erp_company_profit_rate` 形態加一個 key。
            quotation.tax_amount = (total * Decimal("0.05")).quantize(Decimal("1"))
            # 成案即應收：已成案且尚無請款者，總價一到位就建第一期（與 quotation_service.update 同掛點）
            try:
                from app.services.erp.billing_service import ERPBillingService
                await self.db.flush()
                await ERPBillingService(self.db).ensure_first_period(quotation_id, reason="工項填列")
            except Exception as e:  # noqa: BLE001
                logger.error("成案即應收掛點失敗（不阻擋工項儲存）quotation=%s: %s", quotation_id, e, exc_info=True)
        else:
            logger.info(
                "報價 %s 明細清空，**不動 total_price（維持 %s）**"
                " —— 空明細代表尚未逐項拆，不是 0 元",
                quotation_id, quotation.total_price,
            )

        await self.db.flush()
        return {
            "quotation_id": quotation_id,
            "item_count": count,
            "total_price": float(quotation.total_price or 0),
            "items_total": float(total),
            "total_price_updated": bool(count),
            "gross_total": float(quotation.total_price or 0),
        }

    async def summary(self, quotation_id: int) -> dict[str, Any]:
        """給對外報價單檢視用。"""
        quotation = (await self.db.execute(
            select(ERPQuotation).where(ERPQuotation.id == quotation_id)
        )).scalar_one_or_none()
        if not quotation:
            raise ValueError(f"報價 {quotation_id} 不存在")

        items = await self.list_items(quotation_id)
        subtotal = sum((_money(i.amount) for i in items), Decimal("0"))
        tax = _money(quotation.tax_amount)
        return {
            "id": quotation.id,
            "case_code": quotation.case_code,
            "case_name": quotation.case_name,
            "project_code": quotation.project_code,
            "year": quotation.year,
            "status": quotation.status,
            "notes": quotation.notes,
            "items": [
                {
                    "id": i.id, "item_no": i.item_no, "item_name": i.item_name, "spec": i.spec,
                    "unit": i.unit, "qty": float(i.qty or 0),
                    "unit_price": float(i.unit_price or 0),
                    "amount": float(i.amount or 0),
                    "sort_order": i.sort_order, "notes": i.notes,
                }
                for i in items
            ],
            "subtotal": float(subtotal),
            "tax_amount": float(tax),
            "total": float(subtotal + tax) if items else float(_money(quotation.total_price)),
            # 沒有明細時對外報價單不該呈現逐項區塊 —— 讓前端知道要顯示什麼
            "has_items": bool(items),
        }
