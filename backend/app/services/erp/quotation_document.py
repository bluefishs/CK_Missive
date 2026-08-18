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

import io
from datetime import date, datetime
from pathlib import Path
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
                   ga.tax_id          AS client_tax_id,
                   ga.phone           AS client_phone,
                   ga.address         AS client_address,
                   pc.contact_name    AS contact_name,
                   pc.phone           AS contact_phone,
                   pc.mobile          AS contact_mobile,
                   pc.email           AS contact_email,
                   su.staff_name      AS staff_name,
                   su.staff_email     AS staff_email,
                   COALESCE(cp.category, pm.category)         AS category
              FROM (SELECT :cc AS cc) x
              -- ⚠️ contract_projects 與 pm_cases **都沒有 deleted_at**
              -- （只有 erp_quotations 有）。第一版我照著習慣加了
              -- `AND cp.deleted_at IS NULL`，實跑當場 UndefinedColumn ——
              -- 而那條 SQL 走的是文件輸出這條偶爾才跑的路徑，
              -- 若沒有實跑就交付，症狀會是「按匯出就 500」而測試全綠。
              LEFT JOIN contract_projects cp ON cp.case_code = x.cc
              LEFT JOIN pm_cases pm          ON pm.case_code = x.cc
              -- 2026-08-18：範本（`app/templates/quotation_template.xlsx`）
              -- 要的欄位比原本多，逐一接上真實來源，不留空格：
              --   統一編號／聯絡電話／傳真／地址 → 機關主檔
              --   聯絡人手機／E-mail              → 該案的機關承辦
              --   服務人員姓名／E-mail            → 專案負責人（is_primary 優先）
              LEFT JOIN government_agencies ga ON ga.id = cp.client_agency_id
              LEFT JOIN LATERAL (
                  SELECT pc.contact_name, pc.phone, pc.mobile, pc.email
                    FROM project_agency_contacts pc
                   WHERE pc.project_id = cp.id
                   ORDER BY pc.is_primary DESC NULLS LAST, pc.id
                   LIMIT 1
              ) pc ON TRUE
              LEFT JOIN LATERAL (
                  SELECT COALESCE(u.full_name, u.username) AS staff_name, u.email AS staff_email
                    FROM project_user_assignments pa
                    LEFT JOIN users au ON au.id = pa.user_id
                    -- ADR-0025：以 canonical 人為準，分身帳號不得顯示成另一個人
                    LEFT JOIN users u ON u.id = COALESCE(au.canonical_user_id, au.id)
                   WHERE pa.project_id = cp.id
                   ORDER BY pa.is_primary DESC NULLS LAST, pa.id
                   LIMIT 1
              ) su ON TRUE
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
            "contact_person": row.get("contact_name") or row.get("agency_contact_person"),
            # 以下 2026-08-18 新增 —— 範本上有格子的欄位一律給值，
            # 取不到就給 None，由 renderer 決定留白還是印「—」。
            "client_tax_id": row.get("client_tax_id"),
            "client_phone": row.get("client_phone"),
            # 範本有「傳真號碼」格子，但 `government_agencies` **沒有 fax 欄位**。
            # 不為了填滿版面而發明資料來源 —— 留白比印一個錯的號碼好。
            "client_fax": None,
            "client_address": row.get("client_address"),
            "contact_phone": row.get("contact_phone"),
            "contact_mobile": row.get("contact_mobile"),
            "contact_email": row.get("contact_email"),
            "staff_name": row.get("staff_name"),
            "staff_email": row.get("staff_email"),
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

    # ── 版面層（2026-08-18 owner 提供範本後實作）──────────────────────
    #
    # 範本＝`app/templates/quotation_template.xlsx`，取自
    # `Z:\03.專案管控專區\01.報價單紀錄\報價單_B115-D004-0_….xlsx`。
    #
    # **以範本為底填值，不用程式重畫版面。** 理由：
    #   · 範本內含 2 張圖片（公司抬頭）、21 組合併儲存格、框線與字型
    #   · 合計公式已寫在裡面（`E26=SUM(F16:F25)`、稅額 5%、總計）
    #   · 日後版面要改，是換一個檔案，不是改程式
    #
    # 動手前實測過 openpyxl 讀寫的往返保真：
    # 圖片 2→2、合併格 21→21、公式保留、字型/框線/欄寬/列印範圍皆存活。
    # （若沒驗就寫，最可能的失敗是「檔案產生了、打開發現 logo 不見了」。）

    #: 範本各欄位的位置。**寫在同一處**，範本改版時只改這張表。
    #:
    #: 版面規律（實測範本得出，不是猜的）：
    #:   **標籤在 A 欄與 C:D 合併格；值在 B 欄與 E 欄。**
    #:
    #: ⚠️ 我第一版把統編／工程編號／手機／E-mail 的值放在 D 欄 ——
    #: 而 `C7:D7` 是合併格且裡面裝的是**標籤**（「統一編號：」），
    #: openpyxl 直接 `AttributeError: MergedCell ... read-only`。
    #: 實跑當場擋下；若只讀程式碼不跑，這會變成「按匯出就 500」。
    #: 對照 `E12=賴柏霖`／`E13=email` 才確認值欄位在 E。
    CELLS = {
        "quotation_no": "F4",       # 報價單編號
        "quoted_date": "F5",        # 報價日期（民國）
        "client_name": "B7",        # 客戶名稱
        "client_tax_id": "E7",      # 統一編號（C7:D7 是標籤）
        "contact_person": "B8",     # 聯絡人
        "case_code": "E8",          # 工程編號 ← 用內部案號
        "contact_phone": "B9",      # 聯絡電話
        "contact_mobile": "E9",     # 手機號碼
        "client_fax": "B10",        # 傳真號碼（無資料來源，留白）
        "contact_email": "E10",     # E-mail
        "client_address": "B11",    # 聯絡地址
        "case_name": "B12",         # 計畫名稱
        "staff_name": "E12",        # 服務人員
        "location": "B13",          # 工作地點
        "staff_email": "E13",       # 服務人員 E-mail
        "notes": "B21",             # 備註
    }

    #: 明細列範圍（範本的 `SUM(F16:F25)` 就是這 10 列）
    ITEM_FIRST_ROW = 16
    ITEM_LAST_ROW = 25

    #: 項次的中文數字（範本用「一、二、三、」）
    _CN = "一二三四五六七八九十"

    def render_xlsx(self, data: dict[str, Any]) -> bytes:
        """把取料結果填進範本，回傳 xlsx bytes。"""
        from openpyxl import load_workbook

        tpl = Path(__file__).resolve().parents[2] / "templates" / "quotation_template.xlsx"
        if not tpl.exists():
            # 明確失敗而不是產生一個沒有版面的檔案 ——
            # 「檔案下載成功但長得不對」比下載失敗更難查。
            raise FileNotFoundError(f"找不到報價單範本：{tpl}")

        wb = load_workbook(tpl)
        ws = wb["報價單"]

        # ── 表頭與客戶資訊 ──
        for key, cell in self.CELLS.items():
            if key in ("case_code", "quoted_date", "quotation_no"):
                continue
            ws[cell] = data.get(key) or None

        ws[self.CELLS["quotation_no"]] = data["display_no"]
        ws[self.CELLS["quoted_date"]] = data.get("quoted_date_roc") or None
        # 工程編號用內部案號：客戶收到的單子上有它，回頭對帳才對得起來
        ws[self.CELLS["case_code"]] = data.get("case_code") or None

        # ── 明細 ──
        items = data.get("items") or []
        if len(items) > (self.ITEM_LAST_ROW - self.ITEM_FIRST_ROW + 1):
            # 不靜靜截斷 —— 少印幾項的報價單會被當成完整報價送出去。
            raise ValueError(
                f"報價明細 {len(items)} 項超過範本可容納的 "
                f"{self.ITEM_LAST_ROW - self.ITEM_FIRST_ROW + 1} 列。"
                "請調整範本（擴充列數並同步 SUM 範圍）或拆分報價。"
            )

        for i, it in enumerate(items):
            r = self.ITEM_FIRST_ROW + i
            ws[f"A{r}"] = f"{self._CN[i]}、" if i < len(self._CN) else f"{i + 1}、"
            ws[f"B{r}"] = it.get("item_name") or ""
            ws[f"C{r}"] = float(it.get("qty") or 0)
            ws[f"D{r}"] = it.get("unit") or ""
            ws[f"E{r}"] = float(it.get("unit_price") or 0)
            # F 欄寫**公式**不是數值 —— 客戶改數量時金額自己跟著動。
            #
            # ⚠️ 必須每列都寫：範本只在 16/17/18 有公式（樣本剛好 3 項），
            # 第 4 項以後若不補，複價欄會是空白而合計卻少算 ——
            # 那種錯不會報錯，只會讓總價比明細少。
            ws[f"F{r}"] = f"=E{r}*C{r}"
            ws[f"G{r}"] = it.get("notes") or ""

        # 清掉範本殘留的範例資料（範本本身是一份填好的真實報價單）
        #
        # ⚠️ **F 欄也要清**。第一版把 F 排除在外（想保留公式），
        # 實際開檔驗證才發現：範本樣本有 3 項，於是 F16~F18 的
        # `=E*C` 公式留在沒有明細的列上 → 那三格顯示 0，
        # 而 F16 那一列還同時印著「本案為委辦招標案」的說明文字。
        #
        # 這是「只看 bytes 不開檔」會漏掉的一類 —— 檔案產生了、
        # 大小正常、不報錯，打開才看得出版面不對。
        for r in range(self.ITEM_FIRST_ROW + len(items), self.ITEM_LAST_ROW + 1):
            for col in ("A", "B", "C", "D", "E", "F", "G"):
                ws[f"{col}{r}"] = None

        # ── 沒有明細時（標案類）──
        #
        # 合計三格是公式（SUM/稅額/總計），沒有明細時它們會算出 0 ——
        # 而「總計 0 元」印在報價單上是錯的。改為寫入實際總價，
        # **覆蓋公式**：這一類本來就沒有逐項可加總。
        if not items:
            total = data.get("total_price")
            tax = data.get("tax_amount") or ZERO
            if total is not None:
                ws["E26"] = float(total - tax)
                ws["E27"] = float(tax)
                ws["E28"] = float(total)
            else:
                ws["E26"] = ws["E27"] = ws["E28"] = None
            if data.get("category") == "01":
                ws["B16"] = "本案為委辦招標案，依招標文件所列項目辦理"

        # 明細小計與報價總價不一致時**標在文件上**，不是挑一個顯示
        if data.get("amount_mismatch"):
            cur = ws["B21"].value or ""
            ws["B21"] = (
                f"{cur}\n※ 系統提醒：明細小計與報價總額不一致，請確認後再對外發出。"
            ).strip()

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
