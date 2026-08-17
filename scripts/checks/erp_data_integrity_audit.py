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
       -- 終態是 verified 不是 approved（見 _determine_next_approval）。
       -- 我第一版寫 approved/finance_approved 而把 finance_approved 當終態，
       -- 那是中間層 —— 命名讓人誤讀，連寫檢核的我也誤讀了。
       count(*) FILTER (WHERE status = 'verified'),
       COALESCE(max(EXTRACT(day FROM NOW()-created_at))::int, 0)
FROM expense_invoices
UNION ALL
SELECT '營運支出', count(*),
       count(*) FILTER (WHERE approval_status='approved' AND approved_at IS NOT NULL),
       COALESCE(max(EXTRACT(day FROM NOW()-created_at))::int, 0)
FROM operational_expenses;
"""

# §3 案號橋樑（NFKC：名稱在不同模組可能用 CJK 相容字，字形相同碼位不同）
# §3 案號橋樑 —— 2026-08-16 大幅收窄判準。
#
# 原本報「報價 27/77、承攬案件 38/88 指不到 pm_case」。查證後那是**三種東西
# 被算在一起**，其中 34 筆根本不是缺陷：
#
# | 類別 | 數量 | 是什麼 |
# |---|---|---|
# | 舊格式 `CK2023_01_01_001`（類別是數字） | 22 | PM 模組還不存在時的案號體系 |
# | 案號年度 ≤ 2024 | 13 | 歷史案件補登（全部 2026-03-18 一次匯入，107~113 年度）|
# | **現行年度卻無 pm_case** | **4** | ⭐ 真缺口：執行中、有報價、其中一筆已請款兩次 |
#
# **刻意不補建那 34 筆**：那會憑空造出 2020 年的「案件」紀錄，
# 而系統當時根本沒有這個概念 —— **歷史資料的正確狀態就是「沒有」，不是「補一個」**。
#
# 判準若不收窄，報出來的 27/38 裡有 34 筆是雜訊，而那種數字只會被略過
# （本專案反覆記過的告警疲勞）。收窄後是 4 筆，每一筆都該有人處理。
CURRENT_ERA = "2025"   # 案號年度 >= 此值才算現行流程；之前的是歷史補登

# ⚠️ 2026-08-18 再次收窄：判準由 `^CK\d{4}_[A-Z]+_` 改為 `^CK\d{4}_PM_`。
#
# `[A-Z]+` 把**所有**模組代碼都算進來，而只有 PM 式案號應該對得到 pm_cases：
#
#     PM = 從邀標建案來的      → 必須有 pm_cases 列
#     FN = ERP 產號器（erp）   → ERP 直接開的報價，本來就沒有 PM 階段
#     GN = general（手動建立）  → 直接建承攬案件，同上
#     DP = dispatch            → 派工
#
# 於是 `CK2026_FN_01_001` 被誤報成斷鏈 —— 它一點問題都沒有。
# 收窄後 4 筆 → **3 筆**，而那 3 筆是真的：`CK2025_PM_02_001`／
# `CK2026_PM_01_008`／`CK2026_PM_01_009`，全部執行中、全部有報價，
# 而 2026 的 pm_cases 只到 `_007`。
#
# 真因已根治（`contract/core.py` 手動建立改用 GN 不再產 PM 式案號）；
# 這 3 筆的改名屬 owner 決定 —— case_code 被 erp_quotations／
# finance_ledgers／expense_invoices 多處引用。

SQL_BRIDGE = """
SELECT '報價 → pm_cases' AS kind,
       (SELECT count(*) FROM erp_quotations
         WHERE case_code ~ '^CK[0-9]{4}_PM_'
           AND substring(case_code from 3 for 4) >= '%(era)s') AS total,
       (SELECT count(*) FROM erp_quotations q
         WHERE q.case_code ~ '^CK[0-9]{4}_PM_'
           AND substring(q.case_code from 3 for 4) >= '%(era)s'
           AND NOT EXISTS (SELECT 1 FROM pm_cases c WHERE c.case_code=q.case_code)) AS dangling
UNION ALL
SELECT '承攬案件 → pm_cases',
       (SELECT count(*) FROM contract_projects
         WHERE case_code ~ '^CK[0-9]{4}_PM_'
           AND substring(case_code from 3 for 4) >= '%(era)s'),
       (SELECT count(*) FROM contract_projects p
         WHERE p.case_code ~ '^CK[0-9]{4}_PM_'
           AND substring(p.case_code from 3 for 4) >= '%(era)s'
           AND NOT EXISTS (SELECT 1 FROM pm_cases c WHERE c.case_code=p.case_code));
""" % {"era": CURRENT_ERA}

# 真缺口要**列出來**，不能只給數字 —— 4 筆是可以逐一處理的量，
# 而「27 筆指不到」那種數字沒有人會去查是哪幾筆。
SQL_BRIDGE_DETAIL = """
SELECT p.case_code, left(COALESCE(p.project_name,''), 28), p.status
FROM contract_projects p
WHERE p.case_code ~ '^CK[0-9]{4}_PM_'
  AND substring(p.case_code from 3 for 4) >= '%(era)s'
  AND NOT EXISTS (SELECT 1 FROM pm_cases c WHERE c.case_code=p.case_code)
ORDER BY p.case_code;
""" % {"era": CURRENT_ERA}

# 名稱相容字污染（影響所有以名稱比對的管控，含承攬案件防重）
SQL_NFKC = """
-- ⚠️ 2026-08-16 更正判準。原本用 `x <> normalize(x,NFKC)`，那**過寬 26 倍**：
-- 全域 NFKC 會把全形逗號（U+FF0C）轉半形，而中文語境的全形標點是正常的 ——
-- 於是 documents.subject 被報成 1560/2009（78%），實際帶相容漢字的只有 **59 筆**。
-- 真正會壞比對的是**康熙部首（U+2F00-2FDF）與 CJK 相容漢字（U+F900-FAFF）**：
-- 那些字形與標準漢字一模一樣、長度一樣、md5 不同。
-- 判準與 `app/scripts/normalize_unicode.py` 一致（它一直是對的，是我算錯）。
-- PostgreSQL 的字元範圍比對受 collation 影響不可靠，故用碼位逐字元判定。
SELECT 'erp_quotations.case_name',
       count(*) FILTER (WHERE case_name IS NOT NULL AND _has_cjk_compat(case_name)),
       count(*)
FROM erp_quotations
UNION ALL
SELECT 'contract_projects.project_name',
       count(*) FILTER (WHERE project_name IS NOT NULL AND _has_cjk_compat(project_name)),
       count(*)
FROM contract_projects
UNION ALL
SELECT 'documents.subject',
       count(*) FILTER (WHERE subject IS NOT NULL AND _has_cjk_compat(subject)),
       count(*)
FROM documents;
"""

# PostgreSQL 沒有現成的「含相容漢字」判斷；用一次性 SQL 函式定義，
# 避免在三個地方各寫一份 range 條件（而 range 比對本身受 collation 影響不可靠）。
SQL_HELPER = """
CREATE OR REPLACE FUNCTION _has_cjk_compat(s text) RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM regexp_split_to_table(s, '') AS ch
    WHERE ascii(ch) BETWEEN 12032 AND 12255      -- U+2F00-2FDF 康熙部首
       OR ascii(ch) BETWEEN 63744 AND 64255      -- U+F900-FAFF CJK 相容漢字
  );
$$ LANGUAGE sql IMMUTABLE;
"""


# §5 估列 vs 已建應付的落差（2026-08-16）
# 實測 35 筆有應付的報價，**32 筆的外包費已經等於應付合計** —— 有人在手動抄。
# 剩下的沒抄，於是估列成本是 0 而應付已建百萬級，毛利率顯示 100%。
# 只報「應付 > 0 而外包費 = 0」這一種：那是明確的漏估。
# **不報「兩者不等」**：估列與實際本來就會有差，報它會產出每週都紅的噪音。
SQL_ESTIMATE_GAP = """
SELECT count(*) AS gap
FROM erp_quotations q
WHERE COALESCE(q.outsourcing_fee,0) = 0
  AND EXISTS (SELECT 1 FROM erp_vendor_payables p
              WHERE p.erp_quotation_id = q.id AND COALESCE(p.payable_amount,0) > 0);
"""


def _psql(sql: str) -> list[list[str]] | None:
    """host 走這條：.env 的 DATABASE_URL 指向容器網路（postgres:5432），host 連不到。

    2026-08-16：第一版只寫了直連，於是這支在 **weekly 實際執行的 host 環境跑不起來**
    （`fe_sendauth: no password supplied`），而 exit 2 看起來像「資料庫有事」。
    這是 2026-08-11 記過的同一條：**檢核跑在哪個環境，和它判得對不對一樣重要**。
    作法與 `work_record_chain_semantics_audit` 一致，不自創第二種。
    """
    import subprocess
    try:
        out = subprocess.run(
            ["docker", "exec", "ck_missive_postgres", "psql", "-U", "ck_user",
             "-d", "ck_documents", "-tAF", "|", "-c", sql],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if out.returncode != 0:
        return None
    return [ln.split("|") for ln in out.stdout.splitlines() if ln.strip()]


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
    # 兩條路徑，**都不是靜默跳過**：host 的 .env DATABASE_URL 指向容器網路連不到，
    # 借道 docker exec。兩條都不通才 exit 2。
    conn = None
    try:
        conn = psycopg2.connect(_dsn())
    except Exception:
        if _psql("SELECT 1") is None:
            print(chr(10) + "✗ 直連與 docker exec 都不通 —— 無法判定（不視為通過）")
            return 2

    red, yellow = [], []

    def q(sql, expect_rows: bool = True):
        """conn 可用就直連，否則借道 docker exec —— 兩條路徑同一個出口。

        `expect_rows=False` 給 DDL 用（`CREATE OR REPLACE FUNCTION`）。

        ⚠️ 2026-08-18：原本沒有這個參數，於是 `q(SQL_HELPER)`（建輔助函式）
        在**直連路徑**會 `fetchall()` 一個沒有結果集的敘述 →
        `no results to fetch` → 整支落到 except → 印「查詢失敗，無法判定」exit 2。

        **只在直連路徑壞**：psql 路徑執行 DDL 完全正常。這支註冊在
        weekly（host，走 psql）所以生產上一直是好的 ——
        但在容器裡跑會拿到一個指向錯誤原因的訊息（真因是 DDL，
        訊息卻讓人以為 SQL 寫錯或資料有問題）。
        又一次「檢核跑在哪個環境，和它判得對不對一樣重要」。
        """
        if conn is not None:
            with conn.cursor() as cur:
                cur.execute(sql)
                # DDL 沒有結果集 —— 回 [] 而不是讓 fetchall 拋錯。
                # 刻意用參數明示而非「攔到 ProgrammingError 就回 []」：
                # 後者會把「SELECT 真的失敗」也吞成空清單，
                # 而空清單在下游是「沒有問題」的意思。
                return cur.fetchall() if expect_rows else []
        # ⚠️ psql 回傳的是**字串** —— 直接用 `if missing:` 判斷會把 "0" 當成真
        #（Python 裡非空字串一律 truthy），於是「缺 0」也印紅。
        # 這是**只在 host 路徑才會出現**的錯：容器直連回傳的是整數。
        # 兩條路徑必須交出同型的東西，否則判斷邏輯得寫兩套 —— 那就是漂移的起點。
        def _num(v):
            s = (v or "").strip()
            try:
                return int(s)
            except ValueError:
                return s
        rows = _psql(sql)
        return [tuple(_num(c) for c in r) for r in (rows or [])]

    try:
        if True:
            print("\n§1 帳本覆蓋（入帳條件已成立卻沒有帳本記錄＝真的漏帳）")
            for src, due, missing in q(SQL_COVERAGE):
                if missing:
                    red.append(f"{src} 有 {missing} 筆已達入帳條件卻不在帳本")
                    print(f"  🔴 {src:<22} 應入帳 {due:>4}｜缺 {missing}")
                else:
                    print(f"  🟢 {src:<22} 應入帳 {due:>4}｜缺 0")

            print("\n§2 填報推進（機制沒壞，是沒有人走到那個狀態）")
            for kind, total, advanced, oldest in q(SQL_STAGNANT):
                if total and advanced == 0:
                    yellow.append(f"{kind} {total} 筆從未推進到終態（最舊 {oldest} 天）")
                    print(f"  🟡 {kind:<10} {total:>3} 筆｜推進 0｜最舊 {oldest} 天"
                          f" —— 帳本因此缺了這一整面")
                else:
                    print(f"  🟢 {kind:<10} {total:>3} 筆｜推進 {advanced}｜最舊 {oldest} 天")

            print("\n§3 案號橋樑（case_code 指不到 pm_cases）")
            for kind, total, dangling in q(SQL_BRIDGE):
                if dangling:
                    pct = dangling / total * 100 if total else 0
                    yellow.append(f"{kind} 有 {dangling}/{total} 筆 case_code 指不到")
                    print(f"  🟡 {kind:<22} {dangling}/{total}（{pct:.0f}%）指不到 pm_case")
                else:
                    print(f"  🟢 {kind:<22} 全數可解析")

            # 4 筆是可以逐一處理的量 —— 列出來才有人會動它
            for _cc, _nm, _st in q(SQL_BRIDGE_DETAIL):
                print(f"       · {_cc}  {_nm}（{_st}）")

            _g = q(SQL_ESTIMATE_GAP)
            gap = _g[0][0] if _g else 0
            print(chr(10) + "§5 估列漏填（已建應付卻沒有估列外包費）")
            if gap:
                yellow.append(f"{gap} 筆報價已建應付但外包費仍是 0")
                print(f"  🟡 {gap} 筆 —— 應付已經建了，估列外包費卻還是 0，")
                print("       毛利率會顯示 100%。估列與實際是兩件事，不自動帶入，")
                print("       但這種漏估要看得見（詳情頁的外包費欄位也會提示）。")
            else:
                print("  🟢 沒有「已建應付卻沒估列」的報價")

            print("\n§4 名稱相容字（影響所有以名稱比對的管控，含承攬案件防重）")
            q(SQL_HELPER, expect_rows=False)
            for col, bad, total in q(SQL_NFKC):
                pct = bad / total * 100 if total else 0
                flag = "🟡" if pct >= 5 else "🟢"
                if pct >= 5:
                    yellow.append(f"{col} 有 {bad}/{total} 筆帶 CJK 相容字")
                print(f"  {flag} {col:<32} {bad:>5}/{total:<5}（{pct:.0f}%）")
    except Exception as e:
        print(f"\n✗ 查詢失敗：{e} —— 無法判定（不視為通過）")
        return 2
    finally:
        if conn is not None:
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
