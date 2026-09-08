# -*- coding: utf-8 -*-
"""案號的金流足跡 —— 「刪掉這個成案，會有多少東西變成孤兒？」

## 為什麼有這一支（owner 2026-09-09）

> 「複查整體報價、創案成案、金流管控與成案註銷刪除整個流程與防呆機制，
>  包含刪除誤植已成案對應相關財務紀錄清理或註記下架機制」

實查結果：**承攬案刪除完全沒有金流防呆，而且是物理刪除。**

`ProjectService.delete` 做的是解除公文／桃園／派工關聯、刪承辦與廠商關聯、
然後 `DELETE` 專案本身。它靠 `IntegrityError` 當最後一道防線 ——
而**那道防線在金流這一側根本不存在**：

| 有外鍵保護（刪不掉會擋） | 沒有外鍵（刪了就變孤兒） |
|---|---|
| documents／project_vendor_association／project_user_assignments／project_agency_contacts／taoyuan_projects／taoyuan_dispatch_orders | erp_quotations／erp_billings／erp_invoices／erp_vendor_payables／finance_ledgers／expense_invoices／assets |

金流那一側是用**字串 `case_code` 橋接**的（跨模組橋樑，見 `ContractProject.case_code`
的欄位註解），資料庫不會、也不該替它把關。所以刪一個成案：
**報價單、請款、發票、應付、帳本分錄、費用核銷、資產全部留在原地，
指向一個已經不存在的案號，沒有任何錯誤、沒有任何提示。**

對照組就在隔壁：`ERPQuotationService.delete` 是**軟刪**（`deleted_at`）
而且會擋已收款／已付款。兩個相鄰的實體，兩種完全不同的嚴謹度 ——
而承攬案是上位概念，刪它的破壞力更大。

⚠️ **現況資料是乾淨的**（2026-09-09 實查：軟刪的 44 張報價單底下請款／應付／
發票皆 0；金流指向不存在報價單的孤兒 0），但那是因為還沒有人刪過帶金流的成案，
**是運氣不是保護**。292 個成案裡 262 個有金流。

## 這一支不做什麼

它**不刪任何東西**，只回答「有多少」。要不要擋、擋了給什麼訊息，由呼叫端決定；
真的要清理或註記下架是**產品決策**（見下方），不在這裡做。

⇒ 「刪除誤植的成案」正確的流程是：先處理金流（作廢請款／發票、撤銷應付、
沖銷帳本），金流歸零之後成案自然刪得掉。**先擋下來、把數字說清楚，
比替使用者猜他想刪什麼安全。**
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FootprintItem:
    key: str
    label: str
    count: int
    #: 這一類要怎麼處理掉（給使用者看的下一步，不是給程式用的）
    howto: str


@dataclass
class CaseFootprint:
    case_code: Optional[str]
    project_code: Optional[str]
    items: list[FootprintItem] = field(default_factory=list)
    #: 查詢失敗的類別（例如資料表不存在）——**不當成 0**，見下方 blocking 的說明
    errors: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> list[FootprintItem]:
        return [i for i in self.items if i.count > 0]

    @property
    def total(self) -> int:
        return sum(i.count for i in self.items)

    def message(self) -> str:
        """擋下來時給使用者的訊息 —— 說出有幾筆、各是什麼、下一步做什麼。"""
        head = f"此承攬案（{self.case_code or self.project_code or '未編號'}）底下還有金流紀錄，不能直接刪除。"
        lines = [f"　· {i.label} {i.count} 筆 —— {i.howto}" for i in self.blocking]
        tail = ("請先把上列紀錄處理完（作廢或轉移到正確的案），金流歸零之後就刪得掉。"
                "若這個案是誤植而金流是對的，代表金流應該轉掛到別的案，"
                "**不要用刪除達成**——刪除會讓那些紀錄變成沒有主檔的孤兒。")
        return "\n".join([head, *lines, tail])


#: 每一類的 SQL 只查 count。刻意逐類分開而不是一句 UNION：
#: 某一張表不存在（例如日後改名）時，只有那一類會失敗而其餘照常回答 ——
#: 一句 UNION 會讓整個足跡查詢掛掉，而失敗方向會變成「查不到 ⇒ 看起來是 0 ⇒ 放行」。
_QUERIES: list[tuple[str, str, str, str]] = [
    ("quotations", "報價單",
     "select count(*) from erp_quotations where deleted_at is null and (case_code = :cc or project_code = :pc)",
     "在報價單詳情頁刪除（未收款的才刪得掉）"),
    ("billings", "請款紀錄",
     "select count(*) from erp_billings b join erp_quotations q on q.id = b.erp_quotation_id"
     " where q.deleted_at is null and (q.case_code = :cc or q.project_code = :pc)",
     "在報價單的應收帳款分頁作廢"),
    ("invoices", "發票",
     "select count(*) from erp_invoices i join erp_billings b on b.id = i.billing_id"
     " join erp_quotations q on q.id = b.erp_quotation_id"
     " where i.status <> 'voided' and q.deleted_at is null and (q.case_code = :cc or q.project_code = :pc)",
     "在發票管理作廢（作廢不是刪除，發票號碼要留下）"),
    ("payables", "廠商應付",
     "select count(*) from erp_vendor_payables v join erp_quotations q on q.id = v.erp_quotation_id"
     " where q.deleted_at is null and (q.case_code = :cc or q.project_code = :pc)",
     "在應付帳款分頁撤銷或轉掛"),
    ("ledgers", "帳本分錄",
     "select count(*) from finance_ledgers where case_code = :cc",
     "在統一帳本沖銷"),
    ("expenses", "費用核銷",
     "select count(*) from expense_invoices where case_code = :cc",
     "在費用核銷退回或改掛其他案"),
    ("assets", "資產",
     "select count(*) from assets where case_code = :cc",
     "在資產管理改掛其他案"),
]


async def collect(db: AsyncSession, case_code: Optional[str],
                  project_code: Optional[str] = None) -> CaseFootprint:
    """算出這個案號底下各類金流紀錄的筆數。不修改任何資料。"""
    fp = CaseFootprint(case_code=case_code, project_code=project_code)
    if not case_code and not project_code:
        # 兩個編號都沒有 ⇒ 沒有東西橋得過來，足跡必然是空的
        return fp
    params = {"cc": case_code or "\x00", "pc": project_code or "\x00"}
    for key, label, sql, howto in _QUERIES:
        try:
            n = int((await db.execute(text(sql), params)).scalar() or 0)
        except Exception as e:  # noqa: BLE001
            # 查不到不等於沒有 —— 記成 error 讓呼叫端知道這一類「未驗」
            await db.rollback()
            fp.errors.append(f"{label}：查詢失敗（{e.__class__.__name__}）")
            logger.error("案號足跡查詢失敗 key=%s case_code=%s: %s", key, case_code, e, exc_info=True)
            continue
        fp.items.append(FootprintItem(key=key, label=label, count=n, howto=howto))
    return fp


def assert_deletable(fp: CaseFootprint) -> None:
    """有金流就擋。查詢失敗也擋 —— 失敗方向必須是「不刪」而不是「放行」。"""
    if fp.errors:
        raise ValueError(
            "無法確認此承攬案底下有沒有金流紀錄，為安全起見不執行刪除：\n"
            + "\n".join(f"　· {e}" for e in fp.errors)
        )
    if fp.blocking:
        raise ValueError(fp.message())
