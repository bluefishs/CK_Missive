"""ERP 報價匯出/匯入服務

Version: 1.0.0
- v1.0.0: 從 quotation_service.py 拆分 (CSV/Excel export + import)
"""
import csv
import io
import logging
import re
import unicodedata
from typing import Optional, List
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.erp import ERPQuotationRepository
from app.services.erp.quotation_service import ERPQuotationService

logger = logging.getLogger(__name__)


class ERPQuotationIOService:
    """報價匯出/匯入服務 — CSV/Excel IO"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPQuotationRepository(db)

    # =========================================================================
    # CSV 匯出
    # =========================================================================

    async def export_csv(self, year: Optional[int] = None) -> str:
        """匯出報價為 CSV 字串 (含損益計算)"""
        items, _ = await self.repo.filter_quotations(
            year=year, skip=0, limit=9999,
        )

        output = io.StringIO()
        output.write("\ufeff")  # BOM for Excel
        writer = csv.writer(output)
        writer.writerow([
            "案號", "案名", "年度", "總價", "稅額",
            "外包費", "人事費", "管銷費", "其他成本",
            "毛利", "毛利率(%)", "狀態",
        ])

        for item in items:
            profit = ERPQuotationService.compute_profit(item)
            writer.writerow([
                item.case_code or "",
                item.case_name or "",
                item.year or "",
                item.total_price or "",
                item.tax_amount or "",
                item.outsourcing_fee or "",
                item.personnel_fee or "",
                item.overhead_fee or "",
                item.other_cost or "",
                profit["gross_profit"],
                profit["gross_margin"] or "",
                item.status or "",
            ])

        return output.getvalue()

    # =========================================================================
    # Excel 匯出
    # =========================================================================

    async def export_excel(self, year: Optional[int] = None) -> bytes:
        """匯出報價為 Excel (.xlsx)"""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        items, _ = await self.repo.filter_quotations(year=year, skip=0, limit=9999)

        wb = Workbook()
        ws = wb.active
        ws.title = "報價管理"

        headers = [
            "案號", "成案編號", "案名", "年度", "總價", "稅額",
            "外包費", "人事費", "管銷費", "其他成本",
            "毛利", "毛利率(%)", "狀態", "備註",
        ]
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        for row_idx, item in enumerate(items, 2):
            profit = ERPQuotationService.compute_profit(item)
            ws.cell(row=row_idx, column=1, value=item.case_code or "")
            ws.cell(row=row_idx, column=2, value=item.project_code or "")
            ws.cell(row=row_idx, column=3, value=item.case_name or "")
            ws.cell(row=row_idx, column=4, value=item.year or "")
            ws.cell(row=row_idx, column=5, value=float(item.total_price or 0))
            ws.cell(row=row_idx, column=6, value=float(item.tax_amount or 0))
            ws.cell(row=row_idx, column=7, value=float(item.outsourcing_fee or 0))
            ws.cell(row=row_idx, column=8, value=float(item.personnel_fee or 0))
            ws.cell(row=row_idx, column=9, value=float(item.overhead_fee or 0))
            ws.cell(row=row_idx, column=10, value=float(item.other_cost or 0))
            ws.cell(row=row_idx, column=11, value=float(profit["gross_profit"]))
            ws.cell(row=row_idx, column=12, value=float(profit["gross_margin"] or 0))
            ws.cell(row=row_idx, column=13, value=item.status or "")
            ws.cell(row=row_idx, column=14, value=item.notes or "")

        # 欄寬自動調整
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 15
        ws.column_dimensions["C"].width = 40  # 案名較長
        ws.freeze_panes = "A2"

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    # =========================================================================
    # 匯入範本
    # =========================================================================

    @staticmethod
    def generate_import_template() -> bytes:
        """產生匯入範本 Excel"""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = Workbook()
        ws = wb.active
        ws.title = "報價匯入範本"

        headers = ["案號", "案名", "年度(西元)", "總價", "稅額", "外包費", "人事費", "管銷費", "其他成本", "狀態", "備註"]
        fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        font = Font(bold=True, color="FFFFFF")

        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = fill
            cell.font = font
            cell.alignment = Alignment(horizontal="center")

        # 範例資料
        sample = ["B114-B999", "範例測量案件", 2025, 100000, 5000, 30000, 40000, 20000, 10000, "draft", "匯入測試"]
        for col, v in enumerate(sample, 1):
            ws.cell(row=2, column=col, value=v)

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 15
        ws.column_dimensions["B"].width = 30

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    # =========================================================================
    # Excel 匯入
    # =========================================================================

    async def import_from_excel(self, file_bytes: bytes, user_id: Optional[int] = None) -> dict:
        """匯入報價 Excel — 用 case_code 做 upsert"""
        from app.services.base.excel_reader import load_workbook_any

        wb = load_workbook_any(file_bytes)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))

        created = 0
        updated = 0
        errors: list = []

        def _num(v) -> Decimal:
            if v is None:
                return Decimal("0")
            if isinstance(v, (int, float)):
                return Decimal(str(v))
            s = re.sub(r'[NT$￥,\s]', '', str(v).strip())
            return Decimal(s) if s else Decimal("0")

        def _str(v) -> Optional[str]:
            if v is None:
                return None
            return unicodedata.normalize('NFKC', str(v).strip()) or None

        for idx, row in enumerate(rows, start=2):
            try:
                if not row or len(row) < 3:
                    continue
                case_code = _str(row[0])
                case_name = _str(row[1])
                if not case_code or not case_name:
                    continue

                year_val = row[2]
                if isinstance(year_val, (int, float)):
                    year = int(year_val)
                else:
                    year = int(str(year_val).strip()) if year_val else None
                # 民國年自動轉西元
                if year and year < 1911:
                    year = year + 1911

                data = {
                    "case_code": case_code,
                    "case_name": case_name,
                    "year": year,
                    "total_price": _num(row[3]) if len(row) > 3 else Decimal("0"),
                    "tax_amount": _num(row[4]) if len(row) > 4 else Decimal("0"),
                    "outsourcing_fee": _num(row[5]) if len(row) > 5 else Decimal("0"),
                    "personnel_fee": _num(row[6]) if len(row) > 6 else Decimal("0"),
                    "overhead_fee": _num(row[7]) if len(row) > 7 else Decimal("0"),
                    "other_cost": _num(row[8]) if len(row) > 8 else Decimal("0"),
                    "status": _str(row[9]) or "draft" if len(row) > 9 else "draft",
                    "notes": _str(row[10]) if len(row) > 10 else None,
                }

                # Upsert by case_code
                existing = await self.repo.get_by_case_code(case_code)
                if existing:
                    update_data = {k: v for k, v in data.items() if k != "case_code" and v is not None}
                    await self.repo.update(existing.id, update_data)
                    updated += 1
                else:
                    data["created_by"] = user_id
                    await self.repo.create(data)
                    created += 1

            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        if created > 0 or updated > 0:
            await self.db.commit()

        return {
            "total_rows": len(rows),
            "created": created,
            "updated": updated,
            "errors": errors,
        }
