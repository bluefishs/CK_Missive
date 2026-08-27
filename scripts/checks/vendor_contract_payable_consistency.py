#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""協力廠商「合約經費」與應付帳款「分期應付」對不對得起來。

## 為什麼有這支

owner 2026-08-27：
  「`/erp/quotations/168?tab=payable` 應付帳款 tab 需填列**經費付款期別**，
   與 `/contract-cases/187?tab=vendors` 協力廠商 tab 須填列**合約經費**，
   如何對應管控避免兩端不一致、等經費統整有所差異」

同一件事（「我要付這個廠商多少錢」）記在**兩個地方**：

| 畫面 | 資料 | 語意 |
|---|---|---|
| 協力廠商 tab | `project_vendor_association.contract_amount` | 與該廠商簽的**合約總額**（一次） |
| 應付帳款 tab | `erp_vendor_payables.payable_amount` ＋ `payable_period` | 依期別**分次應付**（多筆） |

⇒ **正確的關係是「分期加總 ＝ 合約總額」**，而那個等式先前沒有任何東西在看。

## 實測（2026-08-27，寫這支的當下）

    協力廠商登記            33 筆
    兩端都有                 3 筆   ├ 一致 2 └ **不一致 1**
    只有協力廠商、無應付      30 筆   └ 其中只有 1 筆填了合約經費
    只有應付、協力廠商未登記  33 組

**已經真實發生的不一致**：

    CK2026_PM_01_005  政威資訊顧問有限公司
      協力廠商 tab 填    $2,000,000
      應付帳款 tab 合計  $1,000,000（2 期，都有填期別）
      ⇒ 差 100 萬

⚠️ 而真正的狀況比「不一致」更基本：**兩端幾乎沒有交集**。
33 組應付完全沒有在協力廠商登記，33 筆協力廠商只有 1 筆填了合約經費。
⇒ 這支目前只判「兩端都有值卻對不上」為 RED，
   「只有一端」判 YELLOW —— 因為那多半是**還沒填**而不是填錯，
   而把 63 筆未填每天報成紅色，只會訓練人忽略它。

## 判準

⚠️ **2026-08-27 owner 決策，判準語意整個改了**：

> 「協力廠商 tab 須填列**合約經費為上位規範**，故應付帳款 tab
>   **應以合約經費為規範管控**」

⇒ 兩者**不是對等的兩份資料**，是**規範與執行**：
   合約經費是先談定的上限，應付分期是在它之下逐次執行。

    應付合計  >  合約經費   → **RED**   超出規範（超付風險）
    應付合計  <  合約經費   → GREEN     還沒建完分期，那是正常的
    有應付但**合約經費未填** → **RED**   沒有上位規範可管控，等於無限制
    只有合約經費、無應付     → YELLOW   還沒開始執行

**我原本寫的是「不相等即 RED」，那個語意是錯的** —— 它把「還沒建完分期」
也判成矛盾，而依 owner 的規範那是正常狀態。容差 1 元（避免進位假紅）。

退出碼：0 GREEN／1 YELLOW／2 RED。
"""
from __future__ import annotations

import subprocess
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONTAINER = "ck_missive_postgres"
DB_USER = "ck_user"
DB_NAME = "ck_documents"
TOLERANCE = 1  # 元

#: ⚠️ 三跳關聯：協力廠商掛在**專案**（project_id），應付掛在**報價單**
#: （erp_quotation_id）—— 兩邊沒有共同的外鍵，只能經 case_code 相接。
#: 漏掉這一跳的查詢會**回 0 筆而不是報錯**，看起來像「完全一致」。
_SQL = f"""
WITH pv AS (
    SELECT a.vendor_id, a.contract_amount, p.case_code,
           COALESCE(v.vendor_name, '(未命名廠商)') AS vendor_name
      FROM project_vendor_association a
      JOIN contract_projects p ON p.id = a.project_id
      LEFT JOIN partner_vendors v ON v.id = a.vendor_id
), pay AS (
    SELECT q.case_code, y.vendor_id,
           SUM(y.payable_amount)   AS amt,
           COUNT(*)                AS n,
           COUNT(y.payable_period) AS n_period,
           MAX(y.vendor_name)      AS vn
      FROM erp_vendor_payables y
      JOIN erp_quotations q ON q.id = y.erp_quotation_id
     WHERE y.vendor_id IS NOT NULL
     GROUP BY q.case_code, y.vendor_id
)
-- 超出上位規範（合約經費）—— owner 2026-08-27 的管控方向
SELECT 'OVER|' || pv.case_code || '|' || pv.vendor_name || '|'
       || COALESCE(pv.contract_amount::bigint::text, '0') || '|'
       || pay.amt::bigint::text || '|' || pay.n || '|' || pay.n_period
  FROM pv JOIN pay ON pay.case_code = pv.case_code AND pay.vendor_id = pv.vendor_id
 WHERE COALESCE(pv.contract_amount, 0) > 0
   AND pay.amt - COALESCE(pv.contract_amount, 0) > {TOLERANCE}
UNION ALL
-- 有應付卻沒有上位規範可管 —— 等於無限制
SELECT 'NO_CONTRACT|' || pv.case_code || '|' || pv.vendor_name || '|0|'
       || pay.amt::bigint::text || '|' || pay.n || '|' || pay.n_period
  FROM pv JOIN pay ON pay.case_code = pv.case_code AND pay.vendor_id = pv.vendor_id
 WHERE COALESCE(pv.contract_amount, 0) = 0
UNION ALL
SELECT 'ONLY_VENDOR|' || COUNT(*)::text || '|' || '' || '|' || '' || '|' || '' || '|' || ''
  FROM pv WHERE COALESCE(pv.contract_amount, 0) > 0
   AND NOT EXISTS (SELECT 1 FROM pay
                    WHERE pay.case_code = pv.case_code AND pay.vendor_id = pv.vendor_id)
UNION ALL
SELECT 'ONLY_PAYABLE|' || COUNT(*)::text || '|' || '' || '|' || '' || '|' || '' || '|' || ''
  FROM pay WHERE NOT EXISTS (SELECT 1 FROM pv
                    WHERE pv.case_code = pay.case_code AND pv.vendor_id = pay.vendor_id)
"""


def query() -> list[str] | None:
    try:
        r = subprocess.run(
            ["docker", "exec", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME,
             "-tA", "-c", _SQL],
            capture_output=True, timeout=120,
        )
    except FileNotFoundError:
        print("[RED] 找不到 docker CLI —— 無法取得資料，不下結論", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[RED] 查詢逾時", file=sys.stderr)
        return None
    out = (r.stdout or b"").decode("utf-8", "replace")
    if r.returncode != 0:
        print(f"[RED] 查詢失敗：{(r.stderr or b'').decode('utf-8', 'replace')[:200]}",
              file=sys.stderr)
        return None
    return [ln for ln in out.splitlines() if ln.strip()]


def main() -> int:
    rows = query()
    if rows is None:
        return 2

    over, no_contract, only_vendor, only_payable = [], [], 0, 0
    #: ⚠️ 未知的 kind 必須出聲。2026-08-27 改判準時 SQL 已回 `OVER`／
    #: `NO_CONTRACT`，而這裡還在找舊的 `MISMATCH` —— 資料回來了卻被
    #: 靜靜丟掉，畫面顯示「0 組」⇒ **假綠**。同一種失敗不能再發生一次。
    unknown: list[str] = []
    for ln in rows:
        parts = ln.split("|")
        kind = parts[0]
        if kind == "OVER":
            over.append(parts[1:])
        elif kind == "NO_CONTRACT":
            no_contract.append(parts[1:])
        elif kind == "ONLY_VENDOR":
            only_vendor = int(parts[1] or 0)
        elif kind == "ONLY_PAYABLE":
            only_payable = int(parts[1] or 0)
        else:
            unknown.append(kind)

    if unknown:
        print(f"[RED] 查詢回了 {len(unknown)} 種未知類型：{sorted(set(unknown))}",
              file=sys.stderr)
        print("      SQL 與判讀不同步 —— 不下結論。", file=sys.stderr)
        return 2

    print("=" * 70)
    print("應付分期有沒有超出上位規範（合約經費）")
    print("=" * 70)
    print(f"  應付**超出**合約經費 : {len(over)}")
    print(f"  有應付但合約經費未填 : {len(no_contract)}")
    print(f"  只有合約經費、無應付 : {only_vendor}")
    print(f"  只有應付、未登記廠商 : {only_payable}")

    if over or no_contract:
        if over:
            print(f"\n  [RED] {len(over)} 組**超出合約經費**：")
            for case_code, vendor, contract, paid, n, _np in over:
                print(f"      {case_code} | {vendor}")
                print(f"        合約經費 ${int(contract):,} < 應付合計 ${int(paid):,}"
                      f"（{n} 期）→ **超出 ${int(paid) - int(contract):,}**")
        if no_contract:
            print(f"\n  [RED] {len(no_contract)} 組**有應付卻沒有合約經費** ——"
                  f" 沒有上位規範可管控，等於無限制：")
            for case_code, vendor, _c, paid, n, _np in no_contract:
                print(f"      {case_code} | {vendor} | 應付 ${int(paid):,}（{n} 期）")
        print("\n  依 owner 2026-08-27 的規範：**合約經費是上位，應付在它之下執行**。")
        print("  ⇒ 超出要嘛是應付填錯、要嘛是合約經費該調高（追加）——")
        print("     兩者都需要人決定，系統不自行判斷。")
        return 2

    if only_vendor or only_payable:
        print(f"\n  [YELLOW] 尚未對應：有合約經費但無應付 {only_vendor} 筆／"
              f"有應付但未登記廠商 {only_payable} 組")
        print("     判 YELLOW 不判 RED —— 那是**還沒建**而不是超支。")
        return 1

    print("\n  [GREEN] 沒有超出合約經費的應付")
    return 0


if __name__ == "__main__":
    sys.exit(main())
