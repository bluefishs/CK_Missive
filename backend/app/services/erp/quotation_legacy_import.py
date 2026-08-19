"""既有報價單彙整 XLS 匯入（個人管理時期的資料統整進系統）。

owner 2026-08-19：
  ①「新統整匯入與比對更新，對之前提及個人管理導致公司無法統整，
     故舊有資料仍有保留『案號如 B114-B002』，而成案編號 CK2026_01_01_007
     為系統統一碼機制」
  ②「新增與更新整合為一個按鍵鈕」
  ③「若線上產出報價單未完全上線前，如何匯入與管理既有 XLS 為目前階段重點」

# 資料現況（2026-08-19 實測，不是估計）

    114報價單彙整.xlsx   208 列（跨 5 個工作表：原始／老闆／慶忠／元宏／其他）
    115報價單彙整.xlsx    69 列
    合計                277 列，其中「是否成立=v」274 筆
    系統既有 erp_quotations                77 張

以案名比對：可對上 90 筆、近似 8 筆、**系統裡沒有 179 筆**。
所以匯入必須支援新增，不能只更新 —— 既有的 `pm/cases/import-xlsx`
是「拿第一欄當 PM 案件 id 去更新」，找不到就報錯，不適用於這裡。

# 為什麼用 legacy_quotation_no 當比對鍵

它是 XLS、紙本、回簽 PDF 檔名三者**共同**的識別（回簽檔名長這樣：
`回簽報價單_B115-C013-0_朱冠綸_….pdf`）。案名會被改寫、客戶名有簡稱，
只有這組編號穩定。

比對鍵一旦選錯，「更新」就會變成「重複新增」——所以刻意不用案名。

# 一個入口，不分新增/更新

依 `legacy_quotation_no` 決定 upsert：有就更新、沒有就新增。
使用者不需要先知道哪些是新的（他也無從知道 277 筆裡哪些已在系統）。

# 預覽先於寫入

`dry_run=True` 時只算不寫。**第一次匯入 277 筆業務資料**，
沒有預覽就按下去，錯了要靠備份還原 —— 而預覽的成本只是多一次點擊。
"""
from __future__ import annotations

import io
import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPQuotation
from app.services.contract.case_code import CaseCodeService

logger = logging.getLogger(__name__)

#: 表頭對應。XLS 的「報價金額 」尾端有空白 —— 表頭一律去空白後比對，
#: 不要求人去改檔案。
#:
#: ⚠️ 同一個概念在兩份檔案裡叫不同名字：115 是「發票日期」、114 是「發票日」。
#: 兩個都收 —— 要求人先統一表頭才能匯入，等於把工作推回去給填表的人。
HEADER_MAP = {
    "報價單編號": "legacy_no",
    "是否成立": "established",
    "報價日期": "quoted_date",
    "客戶名稱": "client_name",
    "案名": "case_name",
    "工作地點": "location",
    "報價金額": "total_price",
    "稅內含": "tax_included",
    "稅額": "tax_amount",
    "總價": "grand_total",
    # 以下是財務對帳的關鍵，第一版漏收了 ——
    # 匯入了卻少這些欄位，等於還是得回去翻 Excel。
    "實收金額": "received_amount",
    "收款日期": "received_date",
    "配合廠商": "partner_vendor",
    "支出金額": "expense_amount",
    "聯絡人": "contact_person",
    "電話": "contact_phone",
    "行動電話": "contact_mobile",
    "傳真": "contact_fax",
    "統一編號": "client_tax_id",
    "E-mail": "contact_email",
    "地址": "client_address",
    "備註": "remark",
    "發票日期": "invoice_date",
    "發票日": "invoice_date",      # 114 年度五張工作表用的是這個名字
    "印花": "stamp_duty",
}

#: 這些欄位系統目前**沒有對應的結構化位置**，先原樣保進 notes。
#:
#: 為什麼不現在就開欄位：實收金額／收款日期屬應收、支出金額／配合廠商屬應付，
#: 它們各自該落在 `erp_billings`／`erp_vendor_payables` 而不是報價單上；
#: 而要建那些關聯，得先確定每一列對應到哪一張應收單 —— 那是下一階段的事。
#: **現在最重要的是資料不要遺失**，先原樣帶進來，結構化之後再從 notes 抽。
_NOTES_FIELDS = [
    ("工作地點", "location"), ("客戶", "client_name"), ("統編", "client_tax_id"),
    ("聯絡人", "contact_person"), ("電話", "contact_phone"), ("行動", "contact_mobile"),
    ("傳真", "contact_fax"), ("E-mail", "contact_email"), ("地址", "client_address"),
    ("總價", "grand_total"), ("實收金額", "received_amount"), ("收款日期", "received_date"),
    ("配合廠商", "partner_vendor"), ("支出金額", "expense_amount"),
    ("發票日", "invoice_date"), ("印花", "stamp_duty"), ("原始備註", "remark"),
]


def _clean_header(v: Any) -> str:
    return "".join(str(v or "").split())


def _to_decimal(v: Any) -> Optional[Decimal]:
    """金額：吃得下 45000 / '45,000' / '45000元' / None。"""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    s = re.sub(r"[^\d.\-]", "", str(v))
    if not s or s in ("-", "."):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _roc_to_date(v: Any) -> Optional[date]:
    """報價日期是民國格式 `114.02.03`；也吃 Excel 原生日期。

    ⚠️ 不要用 `int(y) + 1911` 之前先判斷位數 —— `114` 是民國、
    `2025` 是西元，兩者都可能出現在同一欄（不同人填的）。
    """
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip().replace("/", ".").replace("-", ".")
    m = re.match(r"^(\d{2,4})\.(\d{1,2})\.(\d{1,2})$", s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 1911:  # 民國
        y += 1911
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _year_from_legacy(legacy_no: str, quoted: Optional[date]) -> Optional[int]:
    """年度優先從舊案號取（`B115-C013-0` → 民國 115 → 2026）。

    用編號而不是報價日期：跨年度的案子（12 月報價、1 月成立）
    在編號上仍屬原年度，而那才是彙整表分年的依據。
    """
    m = re.match(r"^[A-Za-z]?(\d{3})[-_]", str(legacy_no or "").strip())
    if m:
        return int(m.group(1)) + 1911
    return quoted.year if quoted else None


#: 「是否成立」的肯定值。空白／其他一律視為未成立（不猜）。
_ESTABLISHED = {"v", "V", "y", "Y", "yes", "是", "✓", "○", "1", 1, True}


def parse_workbook(content: bytes) -> list[dict[str, Any]]:
    """解析彙整檔；**全部工作表**都讀（114 年度分成 5 個表）。"""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    try:
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            it = ws.iter_rows(values_only=True)
            try:
                header = [_clean_header(c) for c in next(it)]
            except StopIteration:
                continue
            idx = {HEADER_MAP[h]: i for i, h in enumerate(header) if h in HEADER_MAP}
            if "legacy_no" not in idx:
                continue  # 這張表不是報價彙整（例如統計表）
            for raw in it:
                if not raw:
                    continue
                legacy = str(raw[idx["legacy_no"]] or "").strip()
                if not legacy:
                    continue
                def g(k):
                    return raw[idx[k]] if k in idx and idx[k] < len(raw) else None
                quoted = _roc_to_date(g("quoted_date"))
                rec = {
                    "sheet": sheet,
                    "legacy_no": legacy,
                    "established": g("established") in _ESTABLISHED,
                    "quoted_date": quoted,
                    "client_name": str(g("client_name") or "").strip() or None,
                    "case_name": str(g("case_name") or "").strip() or None,
                    "location": str(g("location") or "").strip() or None,
                    "total_price": _to_decimal(g("total_price")),
                    "tax_amount": _to_decimal(g("tax_amount")),
                    "year": _year_from_legacy(legacy, quoted),
                }
                # 其餘欄位原樣帶出（金額類轉 Decimal、日期類轉 date），
                # 目前沒有結構化位置的會進 notes —— 見 _NOTES_FIELDS。
                for key in ("grand_total", "received_amount", "expense_amount", "stamp_duty"):
                    rec[key] = _to_decimal(g(key))
                for key in ("received_date", "invoice_date"):
                    rec[key] = _roc_to_date(g(key))
                for key in ("partner_vendor", "contact_person", "contact_phone",
                            "contact_mobile", "contact_fax", "client_tax_id",
                            "contact_email", "client_address", "remark", "tax_included"):
                    v = g(key)
                    rec[key] = str(v).strip() if v not in (None, "") else None
                rows.append(rec)
    finally:
        wb.close()
    return rows


def _build_notes(r: dict[str, Any]) -> str:
    """把還沒有結構化位置的欄位原樣保進備註。

    **不丟棄任何有值的欄位** —— 匯入的目的就是讓資料離開 Excel，
    落地時少一欄，使用者就還是得回去翻檔案。
    """
    parts = [f"由「{r.get('sheet')}」工作表匯入（舊案號 {r.get('legacy_no')}）"]
    for label, key in _NOTES_FIELDS:
        v = r.get(key)
        if v not in (None, ""):
            parts.append(f"{label}：{v}")
    return "；".join(parts)


class QuotationLegacyImportService:
    """一個入口做 upsert：有就更新、沒有就新增。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.code_service = CaseCodeService(db)

    async def run(self, content: bytes, *, dry_run: bool = True,
                  user_id: Optional[int] = None) -> dict[str, Any]:
        rows = parse_workbook(content)
        if not rows:
            return {"success": False, "error": "檔案裡找不到『報價單編號』欄，請確認是報價單彙整表"}

        legacy_nos = [r["legacy_no"] for r in rows]
        existing = {
            q.legacy_quotation_no: q
            for q in (await self.db.execute(
                select(ERPQuotation).where(
                    ERPQuotation.legacy_quotation_no.in_(legacy_nos),
                    ERPQuotation.deleted_at.is_(None),
                )
            )).scalars().all()
        }

        to_create, to_update, skipped = [], [], []
        seen: set[str] = set()
        for r in rows:
            ln = r["legacy_no"]
            if ln in seen:
                # 同一份檔案裡重複的編號：只處理第一筆，其餘列出來讓人看
                skipped.append({"legacy_no": ln, "reason": "檔案內重複"})
                continue
            seen.add(ln)
            if not r["case_name"]:
                skipped.append({"legacy_no": ln, "reason": "缺案名"})
                continue
            (to_update if ln in existing else to_create).append(r)

        preview = {
            "success": True,
            "dry_run": dry_run,
            "total_rows": len(rows),
            "will_create": len(to_create),
            "will_update": len(to_update),
            "skipped": len(skipped),
            "skipped_detail": skipped[:20],
            "sample_create": [
                {"legacy_no": r["legacy_no"], "case_name": r["case_name"],
                 "client_name": r["client_name"], "total_price": str(r["total_price"] or ""),
                 "year": r["year"], "established": r["established"]}
                for r in to_create[:10]
            ],
        }
        if dry_run:
            return preview

        created = updated = 0
        for r in to_update:
            q = existing[r["legacy_no"]]
            for field, val in (
                ("case_name", r["case_name"]), ("total_price", r["total_price"]),
                ("tax_amount", r["tax_amount"]), ("year", r["year"]),
            ):
                if val is not None:
                    setattr(q, field, val)
            if r["quoted_date"] and not q.quoted_at:
                q.quoted_at = datetime.combine(r["quoted_date"], datetime.min.time())
            updated += 1

        for r in to_create:
            # case_code 走既有產號器 —— 不自己拼一組編號規則
            # （2026-08-18 已有「手動建案用了 PM 產號器卻不建 pm_cases」的前例）
            case_code = await self.code_service.generate_case_code(
                "erp", r["year"] or date.today().year, "02",
            )
            q = ERPQuotation(
                case_code=case_code,
                case_name=r["case_name"],
                year=r["year"] or date.today().year,
                total_price=r["total_price"],
                tax_amount=r["tax_amount"],
                # 「是否成立=v」＝這張報價客戶接受了 ⇒ confirmed；其餘留 draft。
                # 不寫成 contracted —— 那是承攬案件的狀態，不是報價單的。
                status="confirmed" if r["established"] else "draft",
                legacy_quotation_no=r["legacy_no"],
                quoted_at=(datetime.combine(r["quoted_date"], datetime.min.time())
                           if r["quoted_date"] else None),
                created_by=user_id,
                notes=_build_notes(r),
            )
            self.db.add(q)
            created += 1

        await self.db.commit()
        logger.info("報價單彙整匯入：新增 %d／更新 %d／略過 %d", created, updated, len(skipped))
        return {**preview, "dry_run": False, "created": created, "updated": updated}
