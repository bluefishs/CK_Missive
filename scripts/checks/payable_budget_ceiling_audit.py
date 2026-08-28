#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""應付帳款有沒有「上限」在管 —— 報價單委外經費 vs 應付合計。

## 為什麼有這支

owner 2026-08-29（財務域複查 P1-4 後裁示「防呆預警」）：
實測 5 張報價單 `outsourcing_fee = 0`（或未填）但應付 > 0 ——
最大一筆 CK2026_FN_01_001 應付 350 萬、CK2025_01_03_001（金粟，A36）320 萬。
依 owner 2026-08-27 規範「合約經費是上位，應付在它之下執行」，
這些應付**沒有任何上限在管**。

與 weekly 69（協力廠商 tab 合約經費 vs 應付分期）是同一族的第三對：
那支看的是「per 廠商」的上位，本支看的是「per 報價單」的委外總預算。

## 判準（與 weekly 69 同哲學）

  RED    委外經費**有填**（>0）而應付合計超過它 110%（矛盾——上限被突破；
         10% 容差與收入端 billing 守衛同一條）
  YELLOW 委外經費未填（0/NULL）而應付 > 0（還沒填，不是填錯 ——
         把存量 5 筆天天報紅只會訓練人忽略）

## 誰跑它

weekly step 72（`run_fitness_weekly.sh`）。
"""
import subprocess
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SQL = """
SELECT q.id, COALESCE(q.quotation_no, q.legacy_quotation_no, q.case_code) AS qno,
       COALESCE(q.outsourcing_fee, 0) AS budget,
       sum(p.payable_amount) AS payable_sum
FROM erp_quotations q
JOIN erp_vendor_payables p ON p.erp_quotation_id = q.id
WHERE q.deleted_at IS NULL
GROUP BY q.id
HAVING sum(p.payable_amount) > 0
   AND (COALESCE(q.outsourcing_fee, 0) = 0
        OR sum(p.payable_amount) > COALESCE(q.outsourcing_fee, 0) * 1.10)
ORDER BY sum(p.payable_amount) DESC
"""


def main() -> int:
    r = subprocess.run(
        ["docker", "exec", "ck_missive_postgres", "psql", "-U", "ck_user",
         "-d", "ck_documents", "-tA", "-F", "|", "-c", SQL],
        capture_output=True, timeout=120,
    )
    if r.returncode != 0:
        print("[RED] 查詢失敗（不下結論）：",
              (r.stderr or b"").decode("utf-8", "replace")[:300], file=sys.stderr)
        return 2

    reds, yellows = [], []
    for line in (r.stdout or b"").decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        qid, qno, budget, paysum = line.split("|")
        if float(budget) > 0:
            reds.append(f"  [RED] {qno}: 委外經費 {float(budget):,.0f} "
                        f"但應付合計 {float(paysum):,.0f}（上限被突破）")
        else:
            yellows.append(f"  [YELLOW] {qno}: 應付合計 {float(paysum):,.0f} "
                           f"而委外經費未填 —— 沒有上限在管")

    print("=" * 70)
    print("應付上限稽核：報價單委外經費 vs 應付合計（weekly 72）")
    print("=" * 70)
    for m in reds + yellows:
        print(m)
    if reds:
        print(f"\nStatus: [RED] {len(reds)} 張報價的應付突破已填的委外經費上限")
        return 1
    if yellows:
        print(f"\nStatus: [YELLOW] {len(yellows)} 張報價的應付沒有委外經費上限在管"
              "（補填 outsourcing_fee 即納管）")
        return 0
    print("\nStatus: [GREEN] 所有應付都有上限且未突破")
    return 0


if __name__ == "__main__":
    sys.exit(main())
