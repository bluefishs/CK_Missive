#!/usr/bin/env python
"""ERP 財務資料完整性：帳本收攏了嗎、填報推進了嗎、案號指得到嗎。

## 為什麼需要這一支（2026-08-15 盤查實據）

既有 `ledger_reconciliation` 只比「已付請款總額 vs 帳本總額」的**差額**。
那個問題問得太窄 —— 它只看得到「有入帳但金額不符」，
看不到「**整類來源從來沒有進過帳本**」。

盤查當天量到的：

| 發現 | 數字 | 既有機制看得到嗎 |
|---|---|---|
| 應付 36 筆全部停在 `unpaid`、已付金額 0 | 帳本 AP 來源 **0 筆** | ✗ 差額是 0-0=0，全綠 |
| 營運支出 8 筆 approved | 帳本 `operational_expense` **0 筆** | ✗ 不在對帳範圍 |
| 報價 case_code 指不到 pm_case | **27 / 77** | ✗ 沒有人在問 |
| 承攬案件 case_code 指不到 pm_case | **38 / 88** | ✗ 同上 |

`case_code` 覆蓋率是 **100%** —— 自癒機制把欄位填滿了，
所以每一個「完整性」檢查都是綠的，**但值不解析**。
這是本專案反覆出現的形狀：欄位有值 ≠ 值有意義。

## 三段各自問不同的問題

- **§1 帳本覆蓋（機制）**：入帳條件已成立卻沒有帳本記錄 → **RED**。
  那是真的漏帳，金額會在財務彙總裡少掉。
- **§2 填報停滯（人）**：整類單據的狀態從來沒有推進過 → **YELLOW**。
  機制沒壞，是沒有人走到那個狀態轉換；判紅沒有意義（不是系統的錯），
  但必須看得見 —— 因為它讓帳本缺了一整面。
- **§3 案號橋樑**：case_code 指不到 pm_case → **YELLOW**。
  已知存量、待 owner 決定怎麼收，每週判紅只會被略過。

⚠️ **刻意不把「未達入帳條件」算成漏帳**：請款 48 筆裡 12 筆是 `pending`
（還沒收到款），不入帳是**正確的**。把它算成缺口會產出一份每週都紅、
而且紅得沒道理的清單。
"""
from __future__ import annotations

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------
# §1 帳本覆蓋：入帳條件成立卻沒有帳本記錄
# 條件取自實際程式碼（不另立第二份事實）：
#   erp_billing        → billing_service：payment_status='paid'
#   erp_vendor_payable → vendor_payable_service:74：轉為 paid 且有 paid_amount
#   operational_expense→ operational_service.approve_expense：核准時
# ---------------------------------------------------------------------------
SQL_COVERAGE = """
SELECT 'erp_billing' AS src,
       (SELECT count(*) FROM erp_billings WHERE payment_status='paid') AS due,
       (SELECT count(*) FROM erp_billings b WHERE b.payment_status='paid'
          AND NOT EXISTS (SELECT 1 FROM finance_ledgers l
                          WHERE l.source_type IN ('erp_billing','billing') AND l.source_id=b.id)) AS missing
UNION ALL
SELECT 'erp_vendor_payable',
       (SELECT count(*) FROM erp_vendor_payables WHERE payment_status='paid' AND COALESCE(paid_amount,0)>0),
       (SELECT count(*) FROM erp_vendor_payables p WHERE p.payment_status='paid' AND COALESCE(p.paid_amount,0)>0
          AND NOT EXISTS (SELECT 1 FROM finance_ledgers l
                          WHERE l.source_type='erp_vendor_payable' AND l.source_id=p.id))
UNION ALL
SELECT 'operational_expense',
       (SELECT count(*) FROM operational_expenses WHERE approval_status='approved' AND approved_at IS NOT NULL),
       (SELECT count(*) FROM operational_expenses e WHERE e.approval_status='approved' AND e.approved_at IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM finance_ledgers l
                          WHERE l.source_type='operational_expense' AND l.source_id=e.id));
"""

# §2 填報停滯：整類單據狀態從未推進
SQL_STAGNANT = """
SELECT '應付帳款' AS kind, count(*) AS total,
       count(*) FILTER (WHERE payment_status='paid') AS advanced,
       COALESCE(max(EXTRACT(day FROM NOW()-created_at))::int, 0) AS oldest_days
FROM erp_vendor_payables
UNION ALL
SELECT '費用核銷', count(*),
       count(*) FILTER (WHERE status IN ('approved','finance_approved')),
       COALESCE(max(EXTRACT(day FROM NOW()-created_at))::int, 0)
FROM expense_invoices
UNION ALL
SELECT '營運支出', count(*),
       count(*) FILTER (WHERE approval_status='approved' AND approved_at IS NOT NULL),
       COALESCE(max(EXTRACT(day FROM NOW()-created_at))::int, 0)
FROM operational_expenses;
"""

# §3 案號橋樑（NFKC：名稱在不同模組可能用 CJK 相容字，字形相同碼位不同）
SQL_BRIDGE = """
SELECT '報價 → pm_cases' AS kind,
       (SELECT count(*) FROM erp_quotations WHERE COALESCE(case_code,'')<>'') AS total,
       (SELECT count(*) FROM erp_quotations q WHERE COALESCE(q.case_code,'')<>''
          AND NOT EXISTS (SELECT 1 FROM pm_cases c WHERE c.case_code=q.case_code)) AS dangling
UNION ALL
SELECT '承攬案件 → pm_cases',
       (SELECT count(*) FROM contract_projects WHERE COALESCE(case_code,'')<>''),
       (SELECT count(*) FROM contract_projects p WHERE COALESCE(p.case_code,'')<>''
          AND NOT EXISTS (SELECT 1 FROM pm_cases c WHERE c.case_code=p.case_code));
"""

# 名稱相容字污染（影響所有以名稱比對的管控，含承攬案件防重）
SQL_NFKC = """
SELECT 'erp_quotations.case_name',
       count(*) FILTER (WHERE case_name IS NOT NULL AND case_name<>normalize(case_name,NFKC)),
       count(*)
FROM erp_quotations
UNION ALL
SELECT 'contract_projects.project_name',
       count(*) FILTER (WHERE project_name IS NOT NULL AND project_name<>normalize(project_name,NFKC)),
       count(*)
FROM contract_projects
UNION ALL
SELECT 'documents.subject',
       count(*) FILTER (WHERE subject IS NOT NULL AND subject<>normalize(subject,NFKC)),
       count(*)
FROM documents;
"""


def _dsn() -> str:
    host = os.getenv("POSTGRES_HOST") or os.getenv("PGHOST") or "localhost"
    port = os.getenv("POSTGRES_PORT") or os.getenv("PGPORT") or "5434"
    db = os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE") or "ck_documents"
    user = os.getenv("POSTGRES_USER") or os.getenv("PGUSER") or "ck_user"
    pw = os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD") or ""
    return f"host={host} port={port} dbname={db} user={user} password={pw}"


def main() -> int:
    print("=" * 74)
    print("ERP 財務資料完整性（帳本收攏／填報推進／案號橋樑）")
    print("=" * 74)

    try:
        import psycopg2
    except ImportError:
        print("\n✗ 沒有 psycopg2 —— 無法判定（不視為通過）")
        return 2
    try:
        conn = psycopg2.connect(_dsn())
    except Exception as e:
        print(f"\n✗ 連不上資料庫：{e} —— 無法判定（不視為通過）")
        return 2

    red, yellow = [], []
    try:
        with conn.cursor() as cur:
            print("\n§1 帳本覆蓋（入帳條件已成立卻沒有帳本記錄＝真的漏帳）")
            cur.execute(SQL_COVERAGE)
            for src, due, missing in cur.fetchall():
                if missing:
                    red.append(f"{src} 有 {missing} 筆已達入帳條件卻不在帳本")
                    print(f"  🔴 {src:<22} 應入帳 {due:>4}｜缺 {missing}")
                else:
                    print(f"  🟢 {src:<22} 應入帳 {due:>4}｜缺 0")

            print("\n§2 填報推進（機制沒壞，是沒有人走到那個狀態）")
            cur.execute(SQL_STAGNANT)
            for kind, total, advanced, oldest in cur.fetchall():
                if total and advanced == 0:
                    yellow.append(f"{kind} {total} 筆從未推進到終態（最舊 {oldest} 天）")
                    print(f"  🟡 {kind:<10} {total:>3} 筆｜推進 0｜最舊 {oldest} 天"
                          f" —— 帳本因此缺了這一整面")
                else:
                    print(f"  🟢 {kind:<10} {total:>3} 筆｜推進 {advanced}｜最舊 {oldest} 天")

            print("\n§3 案號橋樑（case_code 指不到 pm_cases）")
            cur.execute(SQL_BRIDGE)
            for kind, total, dangling in cur.fetchall():
                if dangling:
                    pct = dangling / total * 100 if total else 0
                    yellow.append(f"{kind} 有 {dangling}/{total} 筆 case_code 指不到")
                    print(f"  🟡 {kind:<22} {dangling}/{total}（{pct:.0f}%）指不到 pm_case")
                else:
                    print(f"  🟢 {kind:<22} 全數可解析")

            print("\n§4 名稱相容字（影響所有以名稱比對的管控，含承攬案件防重）")
            cur.execute(SQL_NFKC)
            for col, bad, total in cur.fetchall():
                pct = bad / total * 100 if total else 0
                flag = "🟡" if pct >= 5 else "🟢"
                if pct >= 5:
                    yellow.append(f"{col} 有 {bad}/{total} 筆帶 CJK 相容字")
                print(f"  {flag} {col:<32} {bad:>5}/{total:<5}（{pct:.0f}%）")
    except Exception as e:
        print(f"\n✗ 查詢失敗：{e} —— 無法判定（不視為通過）")
        return 2
    finally:
        conn.close()

    print()
    if red:
        print("Status: [RED] 帳本有真的漏帳")
        for r in red:
            print(f"  · {r}")
        print("  入帳條件寫在 vendor_payable_service.py:74 / operational_service.approve_expense，")
        print("  條件成立卻沒有記錄，代表拋轉那一段沒有執行或被吞掉了。")
        return 2
    if yellow:
        print("Status: [YELLOW] 帳本機制正常，但有東西沒有被推進或指不到")
        for y in yellow:
            print(f"  · {y}")
        print("\n  這一段刻意不判 RED —— 它們不是系統壞了：")
        print("  填報停滯是「沒有人走到那個狀態」，案號斷鏈與相容字是既有存量。")
        print("  但它們讓財務彙總少掉一整面、讓名稱比對靜默失效，所以必須看得見。")
        return 1
    print("Status: [GREEN] 帳本收攏、填報推進、案號可解析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
