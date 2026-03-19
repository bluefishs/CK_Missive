"""
匯入 114年度慶忠零星案件委託一覽表.xlsx → PM + ERP 表格

Excel 欄位對照:
  編號, 案號, 作業類型, 是否承作, 案名, 委託單位, 報價日期,
  金額(未稅), 營業稅, 總價(含稅),
  外包單位, 金額.1(外包金額), 稅(外包稅), 費用(外包含稅),
  其他管銷, 毛利, 毛利率, 稅後營業淨利, 淨利率,
  發票日期, 小包請款日期, 發票追蹤時間

匯入策略:
  - PM 案件: 所有 70 筆 (含未承作) → pm_cases
  - ERP 報價: 所有 70 筆 → erp_quotations (case_code 軟連結)
  - 外包付款: 有外包單位的案件 → erp_vendor_payables

用法:
  cd backend && python scripts/fixes/import_114_cases.py
  cd backend && python scripts/fixes/import_114_cases.py --dry-run
"""
import asyncio
import sys
import os
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

import pandas as pd

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.chdir(str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv("../.env")

from sqlalchemy import text, create_engine


EXCEL_PATH = Path(__file__).resolve().parents[3] / "#BUG" / "114年度慶忠零星案件委託一覽表.xlsx"

# 作業類型 → PM category 對照
CATEGORY_MAP = {
    "透地雷達": "01",
    "UAV空拍": "02",
    "現況地形測量": "03",
    "堆料驗證計算": "04",
    "UAV-LiDAR": "02",
    "建築線測量": "03",
    "3D掃描": "05",
    "協助報價類型": "99",
    "協議價購": "06",
    "集水區界線檢核": "03",
    "煤倉傾斜檢測": "07",
    "徵收市價查估": "06",
    "輸水隧道檢測": "07",
    "水庫安全評估": "07",
    "工程測量": "03",
}


def parse_roc_date(val) -> date | None:
    """Parse ROC date format (114/02/03 or 114.07.02) to date"""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if not s:
        return None
    # Try 114/02/03 or 114.02.03 format
    for sep in ["/", "."]:
        parts = s.split(sep)
        if len(parts) == 3:
            try:
                y = int(parts[0]) + 1911
                m = int(parts[1])
                d = int(parts[2])
                return date(y, m, d)
            except (ValueError, TypeError):
                continue
    return None


def safe_decimal(val, default="0") -> Decimal:
    """Convert to Decimal, return default if NaN"""
    if pd.isna(val):
        return Decimal(default)
    try:
        return Decimal(str(float(val))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (ValueError, TypeError):
        return Decimal(default)


def main():
    dry_run = "--dry-run" in sys.argv

    # Read Excel
    df = pd.read_excel(str(EXCEL_PATH), engine="openpyxl")
    # Filter valid rows (有編號)
    df = df[df["編號"].notna()].copy()
    print(f"讀取 {len(df)} 筆案件資料")

    # Database connection
    db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5434/ck_missive"
    engine = create_engine(db_url)

    pm_rows = []
    erp_rows = []
    vendor_payable_rows = []

    # Handle duplicate case_codes by appending suffix
    seen_codes: dict[str, int] = {}

    for _, row in df.iterrows():
        raw_code = str(row["案號"]).strip()
        # Deduplicate case codes
        if raw_code in seen_codes:
            seen_codes[raw_code] += 1
            case_code = f"{raw_code}-{seen_codes[raw_code]}"
        else:
            seen_codes[raw_code] = 1
            case_code = raw_code
        case_name = str(row["案名"]).strip() if pd.notna(row["案名"]) else ""
        work_type = str(row["作業類型"]).strip() if pd.notna(row["作業類型"]) else ""
        is_accepted = str(row["是否承作"]).strip() == "是"
        client = str(row["委託單位"]).strip() if pd.notna(row["委託單位"]) else None
        quote_date = parse_roc_date(row.get("報價日期"))

        amount = safe_decimal(row["金額"])            # 未稅金額
        tax = safe_decimal(row["營業稅"])             # 營業稅
        total = safe_decimal(row["總價"])              # 含稅總價
        outsource_vendor = str(row["外包單位"]).strip() if pd.notna(row["外包單位"]) else None
        outsource_amount = safe_decimal(row.get("金額.1", 0))    # 外包金額
        outsource_tax = safe_decimal(row.get("稅", 0))           # 外包稅
        outsource_total = safe_decimal(row.get("費用", 0))       # 外包含稅
        overhead = safe_decimal(row.get("其他管銷", 0))           # 管銷費
        invoice_date = parse_roc_date(row.get("發票日期"))
        vendor_pay_date = parse_roc_date(row.get("小包請款日期"))

        category = CATEGORY_MAP.get(work_type, "99")

        # 如果案名含「同B114-Bxxx」，跳過（合併案件只建報價不建PM）
        if case_name.startswith("同B114") or case_name.startswith("合併"):
            # 這些還是要建 ERP 報價 (金額=0)
            pass

        # --- PM Case ---
        if is_accepted:
            pm_status = "completed" if invoice_date else "in_progress"
        else:
            pm_status = "closed"

        pm_rows.append({
            "case_code": case_code,
            "case_name": case_name if case_name else f"({work_type})",
            "year": 114,
            "category": category,
            "client_name": client,
            "contract_amount": total,
            "status": pm_status,
            "start_date": quote_date,
            "description": work_type,
            "notes": f"是否承作: {'是' if is_accepted else '否'}",
        })

        # --- ERP Quotation ---
        erp_status = "confirmed" if is_accepted and invoice_date else ("confirmed" if is_accepted else "draft")
        erp_rows.append({
            "case_code": case_code,
            "case_name": case_name if case_name else f"({work_type})",
            "year": 114,
            "total_price": total,
            "tax_amount": tax,
            "outsourcing_fee": outsource_total,  # 外包含稅總額
            "personnel_fee": Decimal("0"),
            "overhead_fee": overhead,
            "other_cost": Decimal("0"),
            "status": erp_status,
            "notes": f"作業類型: {work_type}" + (f" | 外包: {outsource_vendor}" if outsource_vendor and outsource_vendor != "無" else ""),
        })

        # --- Vendor Payable ---
        if outsource_vendor and outsource_vendor != "無" and outsource_total > 0:
            vendor_payable_rows.append({
                "case_code": case_code,
                "vendor_name": outsource_vendor,
                "payable_amount": outsource_total,
                "description": f"{case_name} 外包費用",
                "payment_status": "paid" if vendor_pay_date else "unpaid",
                "paid_date": vendor_pay_date,
                "paid_amount": outsource_total if vendor_pay_date else Decimal("0"),
            })

    print(f"\n準備匯入:")
    print(f"  PM Cases: {len(pm_rows)} 筆")
    print(f"  ERP Quotations: {len(erp_rows)} 筆")
    print(f"  Vendor Payables: {len(vendor_payable_rows)} 筆")

    if dry_run:
        print("\n[DRY RUN] 不寫入資料庫")
        for i, r in enumerate(pm_rows[:3]):
            print(f"  PM[{i}]: {r['case_code']} | {r['case_name'][:30]} | {r['status']} | {r['contract_amount']}")
        for i, r in enumerate(erp_rows[:3]):
            print(f"  ERP[{i}]: {r['case_code']} | total={r['total_price']} | tax={r['tax_amount']} | outsource={r['outsourcing_fee']} | overhead={r['overhead_fee']}")
        return

    with engine.begin() as conn:
        # Check for existing data
        existing = conn.execute(text("SELECT COUNT(*) FROM pm_cases WHERE year = 114")).scalar()
        if existing > 0:
            print(f"\n[WARN]  pm_cases 已有 {existing} 筆 114 年度資料，先清除...")
            conn.execute(text("DELETE FROM pm_case_staff WHERE pm_case_id IN (SELECT id FROM pm_cases WHERE year = 114)"))
            conn.execute(text("DELETE FROM pm_milestones WHERE pm_case_id IN (SELECT id FROM pm_cases WHERE year = 114)"))
            conn.execute(text("DELETE FROM pm_cases WHERE year = 114"))

        existing_erp = conn.execute(text("SELECT COUNT(*) FROM erp_quotations WHERE year = 114")).scalar()
        if existing_erp > 0:
            print(f"[WARN]  erp_quotations 已有 {existing_erp} 筆 114 年度資料，先清除...")
            conn.execute(text("DELETE FROM erp_vendor_payables WHERE erp_quotation_id IN (SELECT id FROM erp_quotations WHERE year = 114)"))
            conn.execute(text("DELETE FROM erp_invoices WHERE erp_quotation_id IN (SELECT id FROM erp_quotations WHERE year = 114)"))
            conn.execute(text("DELETE FROM erp_billings WHERE erp_quotation_id IN (SELECT id FROM erp_quotations WHERE year = 114)"))
            conn.execute(text("DELETE FROM erp_quotations WHERE year = 114"))

        # Insert PM Cases
        for r in pm_rows:
            conn.execute(text("""
                INSERT INTO pm_cases (case_code, case_name, year, category, client_name,
                    contract_amount, status, start_date, description, notes, progress)
                VALUES (:case_code, :case_name, :year, :category, :client_name,
                    :contract_amount, :status, :start_date, :description, :notes, 0)
            """), r)
        print(f"[OK] PM Cases: {len(pm_rows)} 筆已匯入")

        # Insert ERP Quotations
        for r in erp_rows:
            conn.execute(text("""
                INSERT INTO erp_quotations (case_code, case_name, year, total_price, tax_amount,
                    outsourcing_fee, personnel_fee, overhead_fee, other_cost, status, notes)
                VALUES (:case_code, :case_name, :year, :total_price, :tax_amount,
                    :outsourcing_fee, :personnel_fee, :overhead_fee, :other_cost, :status, :notes)
            """), r)
        print(f"[OK] ERP Quotations: {len(erp_rows)} 筆已匯入")

        # Insert Vendor Payables (需要先查 ERP quotation ID)
        vp_count = 0
        for vp in vendor_payable_rows:
            qid = conn.execute(
                text("SELECT id FROM erp_quotations WHERE case_code = :cc AND year = 114"),
                {"cc": vp["case_code"]}
            ).scalar()
            if qid:
                conn.execute(text("""
                    INSERT INTO erp_vendor_payables (erp_quotation_id, vendor_name, payable_amount,
                        description, payment_status, paid_date, paid_amount)
                    VALUES (:qid, :vendor_name, :payable_amount, :description,
                        :payment_status, :paid_date, :paid_amount)
                """), {**{k: v for k, v in vp.items() if k != "case_code"}, "qid": qid})
                vp_count += 1
        print(f"[OK] Vendor Payables: {vp_count} 筆已匯入")

        # Verify
        pm_count = conn.execute(text("SELECT COUNT(*) FROM pm_cases WHERE year = 114")).scalar()
        erp_count = conn.execute(text("SELECT COUNT(*) FROM erp_quotations WHERE year = 114")).scalar()
        vp_total = conn.execute(text("""
            SELECT COUNT(*) FROM erp_vendor_payables vp
            JOIN erp_quotations eq ON vp.erp_quotation_id = eq.id
            WHERE eq.year = 114
        """)).scalar()
        print(f"\n驗證結果:")
        print(f"  pm_cases (114): {pm_count} 筆")
        print(f"  erp_quotations (114): {erp_count} 筆")
        print(f"  erp_vendor_payables (114): {vp_total} 筆")


if __name__ == "__main__":
    main()
