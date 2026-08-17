#!/usr/bin/env python
"""八條生命跡象 —— 問「這個模組今天活著嗎」，不問「機制有沒有動」。

## 為什麼需要這一支（2026-08-16 owner：「每週都重複檢修…還是修補不完」）

當天量出來的數字說明了原因：

| 事實 | 數字 |
|---|---|
| 檢核腳本總數 | 150 |
| 其中**只看機制**（腳本／註冊／檔案／程序是否存在或跑過） | **131** |
| 其中會碰業務資料的 | 19 |
| 七月至今新增／刪除 | **+47／0** |

而系統存在的目的不是讓機制動，是讓**公文被處理、派工被交付、
款被收到、帳被記下**。同一天有四個「機制綠、業務停」的實證：

- `ezbid_cache_refresh` 記 success **1737 次**，而 job 近 48 小時沒跑
- 核銷四層審批完整運作，**控制效果為 0**（同權限、不記錄、不擋自核）
- 統一帳本機制正確，而**應付 37 筆停在 unpaid 最舊 151 天**
- 報價毛利算得出來，而 **37 筆的成本是 0**

131 支機制檢核沒有一支問得到這些，因為它們問的不是這個。

**機制的組合數是無窮的**（每個 job × 每種豁免 × 每個環境 × 每次重構），
**而業務結果只有幾條** —— 追著機制修，永遠有下一個。
這就是「修補不完」的機制原因。

## 設計原則

1. **一支腳本、八條判準**，不是八支腳本 —— 本專案已有 150 支，
   增生本身就是成本。
2. 每條判準**直接查業務資料**，不查 job 有沒有跑、不查檔案新不新。
3. 每個豁免**必須寫理由**，且理由要能被檢驗（例如「政府週末不發標」
   有 announce_date 分布為證）。
4. **人的問題判 YELLOW，系統的問題判 RED** —— 應付沒推進不是系統壞了，
   判紅只會製造每天都紅的噪音，但它必須看得見。
5. ⚠️ **首月只觀測不告警**：新機制上線當下最不該被信任
   （§3 可信度規則 #15–#17、#19 全是「我自己新加的檢核造成的假訊號」）。
   `--enforce` 才會回非 0。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

IS_WEEKEND = date.today().weekday() >= 5

# ---------------------------------------------------------------------------
# 八條生命跡象。
# sql 一律回單一數字；judge(n) 回 None（活著）或問題字串。
# level: RED = 系統壞了；YELLOW = 人沒推進（不是系統的錯，但要看得見）。
# ---------------------------------------------------------------------------
VITALS = [
    {
        "module": "公文",
        "what": "今日有新公文或有公文被更新",
        "sql": "SELECT count(*) FROM documents WHERE created_at::date = CURRENT_DATE "
               "OR updated_at::date = CURRENT_DATE",
        "level": "YELLOW",
        "weekend_ok": True,
        "why_exempt": "假日不辦公，沒有新公文是正常的",
    },
    {
        "module": "派工",
        "what": "逾期未交付的派工沒有累積到失控",
        # 2026-08-16：`deadline` 原本是**民國年字串**且同時裝著業務條件
        # （「115年02月08日前函覆(發文日起25日歷天内檢送成果)」），
        # 直接比較會型別錯誤，而在檢核裡自己寫一套民國年解析就是異質同工的起點。
        # 遷移 20260816a002 加了 `deadline_date`（原文保留），41/43 解析成功；
        # 解析不出的 2 筆本來就不是日期（「查估日期之次日起25日曆天內」「暫緩」）。
        "sql": "SELECT count(*) FROM taoyuan_dispatch_orders d "
               "WHERE d.deadline_date < CURRENT_DATE "
               "AND NOT EXISTS (SELECT 1 FROM taoyuan_work_records w "
               "WHERE w.dispatch_order_id = d.id AND w.work_category = 'delivery')",
        "level": "YELLOW",
        "max": 40,
        "why_exempt": "逾期是業務現實不是系統故障；設上限只為偵測失控成長",
    },
    {
        "module": "標案",
        "what": "標案庫有在長大",
        "sql": "SELECT COALESCE(EXTRACT(day FROM NOW() - MAX(announce_date))::int, 9999) "
               "FROM tender_records WHERE source = 'ezbid'",
        "level": "RED",
        "max": 5,
        "why_exempt": "政府週末不發標（實測 announce_date：週一至五 480–910 筆／"
                      "週六日 0 筆）。5 天＝跨過一個完整週末仍無新增",
    },
    {
        "module": "請款收款",
        "what": "已收款的請款都進了統一帳本",
        "sql": "SELECT count(*) FROM erp_billings b WHERE b.payment_status='paid' "
               "AND COALESCE(b.payment_amount,0) > 0 "
               "AND NOT EXISTS (SELECT 1 FROM finance_ledgers l "
               "WHERE l.source_type IN ('erp_billing','billing') AND l.source_id=b.id)",
        "level": "RED",
        "max": 0,
        "why_exempt": None,   # 沒有豁免：已收款卻沒入帳就是漏帳
    },
    {
        "module": "應付付款",
        "what": "應付有在推進到已付",
        "sql": "SELECT count(*) FROM erp_vendor_payables WHERE payment_status = 'paid'",
        "level": "YELLOW",
        "why_exempt": "沒有人標記已付是流程問題不是系統問題 —— "
                      "但它讓帳本缺了一整面（實測 37 筆停在 unpaid、最舊 151 天）",
    },
    {
        "module": "核銷",
        "what": "有核銷單走完審核",
        "sql": "SELECT count(*) FROM expense_invoices WHERE status = 'verified'",
        "level": "YELLOW",
        "why_exempt": "同上，是人的推進不是系統故障",
    },
    {
        # 2026-08-17：owner 的核心目標是「毛利、核銷、報帳便利性」，
        # 而八條生命跡象裡**沒有一條在問毛利**。
        #
        # 這一條問的不是「毛利多少」（那是業務數字不是生命跡象），
        # 是「**執行中的案子有幾個算得出毛利**」——
        # 算不出來的原因永遠是同一個：沒有總價、或沒有估列成本。
        #
        # ⚠️ 只看**執行中**：實測 78 張報價裡 40 張算得出毛利（51%），
        # 但那 38 張算不出來的多數是已結案的歷史補登。
        # 把歷史案件算進分母，這個數字永遠不會變好，而它變不好就沒有人會看。
        "module": "毛利可算",
        "what": "執行中的**承攬報價**案件算得出毛利（標案類不適用，見 SQL 註解）",
        "sql": """
            SELECT CASE WHEN count(*) = 0 THEN 100
                   ELSE (100 * count(*) FILTER (
                       WHERE q.total_price > 0
                         AND COALESCE(q.outsourcing_fee,0) + COALESCE(q.personnel_fee,0)
                           + COALESCE(q.overhead_fee,0) + COALESCE(q.other_cost,0) > 0
                   ) / count(*))::int END
            FROM erp_quotations q
            JOIN contract_projects p ON p.case_code = q.case_code
            WHERE p.status <> '已結案'
              -- ⭐ 2026-08-17 owner：「專案包含報價與標案兩類 —— 報價可明列
              -- 作業單價統計成本，而標案涉及多項程序**不易填列成本**」。
              -- category 01=委辦招標（標案類）／02=承攬報價。
              -- 實測執行中 14 張報價裡 **11 張是 01**，只有 1 張 02 ——
              -- 把兩類混在一個分母裡，這個指標**永遠不會變好**，
              -- 而永遠不會變好的指標沒有人會看。
              AND p.category = '02'
        """,
        "level": "YELLOW",
        # 門檻刻意訂低（50%）：這是要看**趨勢往哪走**，不是要今天就達標。
        # 訂高會讓它一上線就紅，而一上線就紅的檢核活不過兩週。
        "min": 50,
        "unit": "%",
        "why_exempt": "填報缺口不是系統故障 —— 誰該補由 filing_gap 分派到人，"
                      "這裡只看整體有沒有在往好的方向走",
    },
    {
        "module": "知識圖譜",
        "what": "**關係**有在長大（不是實體）",
        "sql": "SELECT COALESCE(EXTRACT(day FROM NOW() - MAX(extracted_at))::int, 9999) "
               "FROM entity_relations",
        "level": "YELLOW",
        "max": 7,
        "why_exempt": "實體 49,688 一直長而關係近 7 日只新增 18 —— "
                      "看實體會以為圖譜很健康，實際它正在退化成一張清單",
    },
    {
        "module": "學習閉環",
        "what": "有新的 pattern 進來（後段 proposal/crystal 由 owner 人審）",
        "sql": None,   # 檔案型，見 _count_recent_files
        "path": "wiki/memory/patterns",
        "days": 14,
        "level": "YELLOW",
        "why_exempt": "proposal/crystal 需 owner 核准，掛零不必然是故障；"
                      "但 pattern 若也停了，代表輸入端斷了",
    },
]


def _psql(sql: str) -> str | None:
    """host 借道 docker exec；容器內走直連。兩條都不通回 None（不猜）。"""
    import subprocess
    try:
        out = subprocess.run(
            ["docker", "exec", "ck_missive_postgres", "psql", "-U", "ck_user",
             "-d", "ck_documents", "-tA", "-c", sql],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _dsn() -> str:
    return (f"host={os.getenv('POSTGRES_HOST') or os.getenv('PGHOST') or 'localhost'} "
            f"port={os.getenv('POSTGRES_PORT') or os.getenv('PGPORT') or '5434'} "
            f"dbname={os.getenv('POSTGRES_DB') or 'ck_documents'} "
            f"user={os.getenv('POSTGRES_USER') or 'ck_user'} "
            f"password={os.getenv('POSTGRES_PASSWORD') or os.getenv('PGPASSWORD') or ''}")


def _count_recent_files(path: str, days: int) -> int | None:
    from pathlib import Path
    import time
    for base in (Path(__file__).resolve().parents[2], Path("/app")):
        d = base / path
        if d.is_dir():
            cutoff = time.time() - days * 86400
            return sum(1 for f in d.glob("*.md") if f.stat().st_mtime > cutoff)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--enforce", action="store_true",
                    help="依判定回非 0（首月刻意不開：新機制上線當下最不該被信任）")
    args = ap.parse_args()

    print("=" * 74)
    print("八條生命跡象 —— 這個模組今天活著嗎")
    print("=" * 74)

    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(_dsn())
    except Exception:
        if _psql("SELECT 1") is None:
            print("\n✗ 直連與 docker exec 都不通 —— 無法判定（不視為通過）")
            return 2

    def num(sql: str) -> int | None:
        try:
            if conn is not None:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    return int(cur.fetchone()[0])
            v = _psql(sql)
            return int(v) if v not in (None, "") else None
        except Exception:
            return None

    red, yellow, unknown = [], [], []
    print()
    for v in VITALS:
        n = (_count_recent_files(v["path"], v["days"])
             if v["sql"] is None else num(v["sql"]))
        mod, level = v["module"], v["level"]

        if n is None:
            unknown.append(mod)
            print(f"  ⚪ {mod:<8} 查不到 —— 不當成通過（{v['what']}）")
            continue

        # 判定：有 max 比上限、有 min 比下限，其餘要求 > 0
        #
        # ⚠️ 2026-08-17：`min` 是這天才加的。在此之前我寫了一條帶 `min` 的
        # 生命跡象，而**腳本根本不認得它** —— 那條會靜靜退化成
        # 「只要不是 0 就通過」，等於一條永遠綠的檢核。
        # 這正是本輪反覆記錄的「寫了等於沒寫」：設定裡多一個鍵不會有人報錯。
        unit = v.get("unit", "")
        if "max" in v:
            bad = n > v["max"]
            shown = f"{n}{unit}（上限 {v['max']}{unit}）"
        elif "min" in v:
            bad = n < v["min"]
            shown = f"{n}{unit}（下限 {v['min']}{unit}）"
        else:
            bad = n == 0
            shown = f"{n}{unit}"

        if bad and v.get("weekend_ok") and IS_WEEKEND:
            print(f"  🟢 {mod:<8} {shown} —— 週末合理（{v['why_exempt']}）")
            continue

        if bad:
            (red if level == "RED" else yellow).append(f"{mod}：{v['what']}（實測 {shown}）")
            print(f"  {'🔴' if level == 'RED' else '🟡'} {mod:<8} {shown} —— {v['what']}")
            if v.get("why_exempt"):
                print(f"       └ {v['why_exempt']}")
        else:
            print(f"  🟢 {mod:<8} {shown} —— {v['what']}")

    if conn is not None:
        conn.close()

    print()
    if unknown:
        print(f"⚪ 查不到 {len(unknown)} 條：{'、'.join(unknown)}")
        print("   查不到不是通過 —— 判準本身可能寫錯了表名或欄位。")
    if red:
        print(f"\nStatus: [RED] {len(red)} 個模組的業務結果停了")
        for r in red:
            print(f"  · {r}")
    elif yellow:
        print(f"\nStatus: [YELLOW] {len(yellow)} 個模組需要人推進")
        for y in yellow:
            print(f"  · {y}")
        print("\n  這些不是系統故障，是流程沒有走完 —— 判 YELLOW 不判 RED。")
    else:
        print("Status: [GREEN] 八個模組今天都活著")

    if not args.enforce:
        print("\n（觀測模式：首月不告警。新機制上線當下最不該被信任 ——")
        print("  §3 可信度表 #15–#17、#19、#21 全是我自己新加的檢核造成的假訊號。）")
        return 0
    return 2 if red or unknown else (1 if yellow else 0)


if __name__ == "__main__":
    sys.exit(main())
