#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""廠商身分的源頭是不是同一個 —— 委託單位與協力廠商。

## 為什麼有這支

owner 2026-08-27：「`/erp/client-accounts` 避免委託與協力帳款不一致，
以及統一源頭數據」。

查證後發現**兩端用的是兩套完全不同的關聯機制**：

| 對象 | 廠商從哪來 | 掛在哪 | 覆蓋 |
|---|---|---|---|
| 委託單位（應收） | `PMCase.client_vendor_id` | **邀標案件** | 102/253（40%） |
| 協力廠商（應付）① | `erp_vendor_payables.vendor_id` | **應付單本身** | 34/39 |
| 協力廠商（應付）② | `project_vendor_association.vendor_id` | **承攬專案** | 33 筆 |

⇒ 三套機制、三個掛點，而**應付單還多存了一份 `vendor_name` 文字**。

## 已經真實發生的矛盾（2026-08-27 實測）

同一張應付單，FK 指向的廠商名與自己存的文字名**不同**：

    應付#47  自存「竣吉不動產估價師」        vs FK「竣吉不動產估價師事務所」
    應付#39  自存「林晉廷」                  vs FK「林宥廷測量技師事務所」
    應付#51  自存「銢欣有限公司乃耳企業社」   vs FK「銢欣有限公司」

⚠️ **第二筆最嚴重：林晉廷與林宥廷是不同的人**，
   而 FK 指到了錯的廠商 ⇒ **那筆錢會算到別人頭上**。

## 這支只問一件事：**同一個廠商身分，兩個來源說的是不是同一件事**

它不管金額（那是 `vendor_contract_payable_consistency.py` 的事），
也不管覆蓋率高低（那是業務推進）—— **只管矛盾**。

判準：
* 應付單的 `vendor_name` 與 FK 指向的 `partner_vendors.vendor_name` 不同 → **RED**
* 應付單有 `vendor_name` 但沒有 `vendor_id`（只有文字沒有身分）→ **YELLOW**
* 委託單位覆蓋率 → 只報數字**不判級**（那是填報進度不是矛盾）

⚠️ 為什麼「不同」是 RED 而不是 YELLOW：那不是「還沒填」，
是**兩個地方對同一件事給出不同答案**，而系統無法自己決定誰對。

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

_SQL = """
SELECT 'MISMATCH|' || y.id || '|' || y.vendor_name || '|' || pv.vendor_name
       || '|' || y.vendor_id
  FROM erp_vendor_payables y
  JOIN partner_vendors pv ON pv.id = y.vendor_id
 WHERE y.vendor_name IS NOT NULL
   AND btrim(y.vendor_name) <> btrim(pv.vendor_name)
UNION ALL
SELECT 'TEXT_ONLY|' || COUNT(*)::text || '|||'
  FROM erp_vendor_payables
 WHERE vendor_name IS NOT NULL AND vendor_id IS NULL
UNION ALL
SELECT 'CLIENT_COVERAGE|' || COUNT(client_vendor_id)::text || '|'
       || COUNT(*)::text || '||'
  FROM pm_cases
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
    if r.returncode != 0:
        print(f"[RED] 查詢失敗：{(r.stderr or b'').decode('utf-8', 'replace')[:200]}",
              file=sys.stderr)
        return None
    return [ln for ln in (r.stdout or b"").decode("utf-8", "replace").splitlines()
            if ln.strip()]


def main() -> int:
    rows = query()
    if rows is None:
        return 2

    mismatches, text_only, cov_have, cov_total = [], 0, 0, 0
    for ln in rows:
        p = ln.split("|")
        if p[0] == "MISMATCH":
            mismatches.append(p[1:5])
        elif p[0] == "TEXT_ONLY":
            text_only = int(p[1] or 0)
        elif p[0] == "CLIENT_COVERAGE":
            cov_have, cov_total = int(p[1] or 0), int(p[2] or 0)

    print("=" * 70)
    print("廠商身分的源頭是不是同一個")
    print("=" * 70)
    pct = (100 * cov_have // cov_total) if cov_total else 0
    print(f"  委託單位關聯覆蓋 : {cov_have}/{cov_total}（{pct}%）"
          f" —— 只報數字不判級（那是填報進度不是矛盾）")
    print(f"  應付只有文字沒身分: {text_only}")
    print(f"  FK 與文字名矛盾   : {len(mismatches)}")

    if mismatches:
        print(f"\n  [RED] {len(mismatches)} 筆**同一張單、兩個名字**：")
        for pid, text_name, fk_name, vid in mismatches:
            print(f"      應付#{pid}  自存「{text_name}」")
            print(f"                vs FK「{fk_name}」(vendor_id={vid})")
        print("\n  這不是「還沒填」，是**兩個地方對同一件事給出不同答案**，")
        print("  而系統無法自己決定誰對 —— 尤其當兩個名字是不同的人時，")
        print("  那筆錢會算到別人頭上。")
        print("  修法方向見 docs/architecture/VENDOR_FUND_CONTROL_PLAN.md。")
        return 2

    if text_only:
        print(f"\n  [YELLOW] {text_only} 筆應付只有廠商文字、沒有 vendor_id")
        print("     ⇒ 那些款項無法跨案件彙總到廠商身上（/erp/vendor-accounts 看不到）")
        return 1

    print("\n  [GREEN] 沒有身分矛盾")
    return 0


if __name__ == "__main__":
    sys.exit(main())
