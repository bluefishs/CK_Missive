"""報價單正式文件輸出 —— 取料層（版面待 owner 提供範本）。

owner 2026-08-17：
  ① 「新增報價單要可輸出正式文件，非僅資料列表用途」
  ② 「明日提供報價單範本與格式再行評估設計，**先完成整體流程與規劃**」
  ③ 「目前報價單採用 **xls** 格式」

# 為什麼這個檔只有取料、沒有版面

我第一版把版面寫成 docx（自己編了抬頭、欄位順序、簽署欄）。
在 owner 說出 ②③ 之後那份版面必然要丟掉 —— 而丟掉的不只是排版，
是「我以為報價單長什麼樣」的一整套假設（我連公司名都是猜的）。

所以拆成兩層，只做現在做得準的那一層：

    _gather()   取料 —— 與範本完全無關，範本換了它不用改
    render_*()  版面 —— 待範本，明日補

這樣明天拿到那份 xls 時要做的是「把值填進既有格子」，
而不是「把我編的版面改成你們的版面」。

# 格式：xls（openpyxl）不是 docx

owner 明講目前用 xls。`openpyxl` 專案已在 5 處使用（asset／expense／
finance 匯出），沿用同一套；`python-docx` 目前只用來**讀**附件、
從未用來產生文件，導入寫入用法會多一條沒有既有實踐的路。

⚠️ 若那份範本是 **.xls（BIFF，Excel 97-2003）** 而非 .xlsx，
openpyxl **讀不了也寫不了** —— 需先確認副檔名實際格式，
別假設「xls」是口語泛稱。這件事明天拿到檔案第一步就要驗，
因為它決定用 openpyxl 還是得另找套件（而後者要加依賴）。

# 取料的取捨（這些與範本無關，已定）

* 委託單位／工作地點／類別**沿用 `quotation_service` 同一條取法**
  （承攬案件 `client_agency` 優先、其次 PM `client_name`）——
  不另寫一份，否則文件上的委託單位會與畫面上的各自演化。
* 明細小計與報價總價**不強制相等**：議價後可能只調總價而未逐項回改，
  兩個數字都給出去，讓落差在版面上看得見，而不是挑一個顯示。
* 金額 None 與 0 分開回傳：「沒填」印成 0 會被讀成免費。
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# ⚠️ `ERPQuotation` 在 `models.erp` 不在 `models.invoice`（我第一版寫錯了）。
# 這個錯誤的形狀正是 v6.56 記錄的病灶家族「模組匯入即失敗，而沒有人在匯入它」：
# py_compile 過、型別檢查過、測試不碰它，要等真的有人打匯出端點才會爆。
# 抓到它的是 daily step 12 `module_import_sweep`（真的把每個模組匯入一次）
# —— 本次是我自己手動 import 時撞到，比等到明天早一天。
from app.extended.models.erp import ERPQuotation
from app.services.contract.case_code import CaseCodeService

ZERO = Decimal("0")

# 報價有效期限（天）。業界慣例 30 天；先寫死是因為目前沒有任何地方在存它，
# 憑空開一個設定欄位只會多一個沒人維護的數字。範本若有這一格再對齊。
VALID_DAYS = 30


def roc_date(d: Optional[date | datetime]) -> str:
    """民國年月日 —— 客戶手上其他文件都是這樣寫的。"""
    if not d:
        return ""
    dd = d.date() if isinstance(d, datetime) else d
    return f"{dd.year - 1911}年{dd.month:02d}月{dd.day:02d}日"


class QuotationDocumentService:
    """把一張報價整理成「可填入範本」的資料包。

    刻意回 dict 而不是直接回檔案 bytes：
    範本還沒到，而取料是現在就能定案並被測試的部分。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def gather(self, quotation_id: int) -> dict[str, Any]:
        """收齊一張報價單所需的全部欄位。

        Returns 的 key 皆為業務語意名（`display_no`／`client_name`／`items`…），
        **不含任何版面概念**（沒有 row/col、沒有字型）——
        版面在 renderer 那一層，換範本不動這裡。
        """
        q = (await self.db.execute(
            select(ERPQuotation).where(
                ERPQuotation.id == quotation_id,
                ERPQuotation.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if not q:
            raise ValueError(f"找不到報價 {quotation_id}")

        row = (await self.db.execute(text("""
            SELECT COALESCE(cp.client_agency, pm.client_name) AS client_name,
                   cp.location,
                   cp.agency_contact_person,
                   COALESCE(cp.category, pm.category)         AS category
              FROM (SELECT :cc AS cc) x
              -- ⚠️ contract_projects 與 pm_cases **都沒有 deleted_at**
              -- （只有 erp_quotations 有）。第一版我照著習慣加了
              -- `AND cp.deleted_at IS NULL`，實跑當場 UndefinedColumn ——
              -- 而那條 SQL 走的是文件輸出這條偶爾才跑的路徑，
              -- 若沒有實跑就交付，症狀會是「按匯出就 500」而測試全綠。
              LEFT JOIN contract_projects cp ON cp.case_code = x.cc
              LEFT JOIN pm_cases pm          ON pm.case_code = x.cc
             LIMIT 1
        """), {"cc": q.case_code})).mappings().first() or {}

        items = (await self.db.execute(text("""
            SELECT item_name, spec, unit, qty, unit_price, amount, notes
              FROM erp_quotation_items
             WHERE quotation_id = :qid
             ORDER BY sort_order, id
        """), {"qid": quotation_id})).mappings().all()

        subtotal = sum((Decimal(str(r["amount"] or 0)) for r in items), ZERO)
        total = Decimal(str(q.total_price)) if q.total_price is not None else None
        tax = Decimal(str(q.tax_amount or 0))
        quoted = q.quoted_at or q.created_at

        return {
            "quotation_id": q.id,
            # 含版次後綴的對外單號（QT2026_018-2）；未編號時回「未編號」，
            # 不回空字串 —— 正式文件上留白會被當成漏印。
            "display_no": CaseCodeService.format_quotation_no(
                q.quotation_no, q.revision or 1
            ),
            "quotation_no": q.quotation_no,
            "revision": q.revision or 1,
            "case_code": q.case_code,
            "case_name": q.case_name,
            "year": q.year,
            "quoted_date_roc": roc_date(quoted),
            "quoted_date": quoted,
            "valid_days": VALID_DAYS,
            "client_name": row.get("client_name"),
            "location": row.get("location"),
            "contact_person": row.get("agency_contact_person"),
            # '01' 委辦招標（標案，無明細）／'02' 承攬報價（逐項單價）
            "category": row.get("category") or "",
            "items": [dict(r) for r in items],
            "items_subtotal": subtotal,
            "tax_amount": tax,
            "total_price": total,
            # 兩者不一致時 renderer 應在文件上標出，不得只挑一個顯示
            "amount_mismatch": (
                total is not None and abs(subtotal - total) > Decimal("0.01")
                and len(items) > 0
            ),
            "notes": q.notes,
            "has_items": len(items) > 0,
        }

    def suggest_filename(self, data: dict[str, Any], ext: str = "xlsx") -> str:
        """建議下載檔名。ext 待範本確認（.xls 與 .xlsx 是兩種格式）。"""
        name = (data.get("case_name") or data.get("case_code") or "報價單").strip()
        for ch in '\\/:*?"<>|\r\n\t':
            name = name.replace(ch, "_")
        return f"報價單_{data['display_no']}_{name[:40]}.{ext}"

    # ── 版面層（待 owner 明日提供範本）─────────────────────────────────
    #
    # 明天拿到範本的執行順序：
    #   1. 驗副檔名實際格式 —— .xls(BIFF) 還是 .xlsx？openpyxl 只吃後者
    #   2. 逐格對出「哪一格填什麼」，明細列的起始列與可擴充列數
    #   3. render_xlsx(data) -> bytes，走既有 StreamingResponse 形狀
    #      （參照 `api/endpoints/erp/assets.py:151` 的匯出端點）
    #   4. 中文檔名要 RFC 5987 `filename*=UTF-8''…`：既有匯出全用 ASCII
    #      檔名所以沒踩到，這裡的檔名含案名必然是中文
    #
    # 刻意不先寫一個「暫時版面」：那會變成第二份範本，
    # 而真範本到了之後沒有人會記得回來刪掉暫時那份。
