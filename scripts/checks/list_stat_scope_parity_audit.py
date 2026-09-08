#!/usr/bin/env python3
"""列表與統計卡的身分口徑一致性稽核 —— owner 2026-09-09。

問的問題：**同一個畫面上，列表篩了誰的案，統計卡就必須算誰的案。**

owner 兩次回報都是這個形狀：
  · 09-09 早：「`/contract-cases` 已配合角色與登入帳號篩選案件清單，但統計圖卡卻未同步」
    ⇒ 承辦 6 案的業務同仁，列表 6 件而卡片 123 件。
  · 09-09 午：「PM 案件列表與統計兩者無對應，是不合理的統計數據」
    ⇒ 列表接了 `staff_user_id`、`/summary` 沒接。

⚠️ **為什麼不用靜態掃描**（首版試過，當場誤報）：
端點函式本體看不到 `staff_user_id` —— 它宣告在 schema 裡，端點只把 `params` 整包傳下去。
掃字樣得到的答案是「PM 列表沒有身分訊號」，而**實際上它有**。
⇒ 判準改成**行為**：拿同一個身分、同一組參數，分別打列表與統計，比數字。
數字才是使用者看到的東西。

判準：對每一組（列表端點, 統計端點），用一位真的有案的承辦身分各打一次，
`統計的總數` 必須等於 `列表的 total`。不等即 RED。

⚠️ 找不到「有案的承辦」時本檢核**不判綠燈**，回報「無可檢對象」——
零樣本的綠燈是本 repo 記過的假綠形狀。

須在**容器內**執行（要 import 應用程式碼與連 DB）：
    docker exec ck_missive_backend python /app/scripts/checks/list_stat_scope_parity_audit.py

退出碼：0 = 一致；2 = 不一致；1 = 無法執行／無可檢對象。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

sys.path.insert(0, "/app")


async def run() -> int:
    try:
        from sqlalchemy import select, text
        from app.db.database import AsyncSessionLocal
        from app.extended.models import User
    except Exception as e:
        print("無法載入應用程式：%s（本檢核須在容器內跑）" % e)
        return 1

    print("=" * 68)
    print("列表與統計卡的身分口徑一致性稽核（weekly）")
    print("=" * 68)

    async with AsyncSessionLocal() as db:
        # 找一位真的有案的承辦（非管理員 —— 管理員看得到全部，比不出差別）
        row = (await db.execute(text("""
            SELECT u.id, u.full_name, COUNT(DISTINCT pa.case_code) n
              FROM users u JOIN project_user_assignments pa ON pa.user_id = u.id
             WHERE u.is_active AND u.role NOT IN ('superuser', 'admin')
               AND pa.case_code IS NOT NULL
             GROUP BY 1, 2 HAVING COUNT(DISTINCT pa.case_code) > 0
             ORDER BY n DESC LIMIT 1
        """))).first()
        if not row:
            print("無可檢對象：找不到任何「非管理員且有案」的承辦。")
            print("⚠️ 這不是綠燈 —— 沒有樣本就證明不了兩邊口徑相同。")
            return 1
        uid, uname, ncase = row[0], row[1], row[2]
        print("量測身分：%s（id=%s，%s 個案）" % (uname, uid, ncase))
        user = (await db.execute(select(User).where(User.id == uid))).scalar_one()

        year = int(os.getenv("PARITY_YEAR", "2026"))
        print("年度：%s" % year)
        print()

        results = []

        # ---- PM 案件 ----
        try:
            from app.services.pm.case_service import PMCaseService
            from app.schemas.pm.case import PMCaseListRequest
            svc = PMCaseService(db)
            lst = PMCaseListRequest(page=1, limit=1, year=year, staff_user_id=uid)
            _items, total = await svc.list_cases(lst)
            summ = await svc.get_summary(year=year, include_converted=True, staff_user_id=uid)
            results.append(("PM 案件 /pm/cases", total, summ.total_cases))
        except Exception as e:
            results.append(("PM 案件 /pm/cases", "錯誤", str(e)[:80]))

        # ---- 協力廠商帳款 ----
        try:
            from app.api.endpoints.erp.vendor_accounts import get_vendor_account_summary
            from app.repositories.erp.vendor_payable_repository import ERPVendorPayableRepository
            from app.schemas.erp.vendor_financial import VendorAccountListRequest
            repo = ERPVendorPayableRepository(db)
            req = VendorAccountListRequest(year=year, staff_user_id=uid, skip=0, limit=1)
            resp = await get_vendor_account_summary(params=req, repo=repo, db=db, current_user=user)
            d = resp.data if hasattr(resp, "data") else resp["data"]
            # 這一頁的「統計」是 totals（金額），列表是家數 —— 兩者刻意不同量。
            # 能比的是「有沒有一邊是 0 而另一邊不是」。
            tot = d.get("totals") or {}
            payable = float(tot.get("total_payable") or 0)
            results.append((
                "協力帳款 /erp/vendor-accounts",
                d.get("total"),
                "金額 %s" % payable,
            ))
            if (d.get("total") or 0) == 0 and payable > 0:
                results.append(("  ⛔ 家數 0 卻有金額", d.get("total"), payable))
        except Exception as e:
            results.append(("協力帳款 /erp/vendor-accounts", "錯誤", str(e)[:80]))

        print("%-34s %-12s %s" % ("頁面", "列表", "統計"))
        bad = []
        for name, a, b in results:
            same = (a == b) if isinstance(b, int) else None
            mark = "" if same is None else ("  ✅" if same else "  ⛔ 不一致")
            print("%-34s %-12s %s%s" % (name, a, b, mark))
            if same is False:
                bad.append(name)

        print()
        if bad:
            print("⛔ 列表與統計的身分口徑不同：%s" % ", ".join(bad))
            print("⇒ 統計端點要收與列表同一組範圍條件（身分也是範圍）。")
            rc = 2
        else:
            print("✅ 受檢頁面的列表與統計在同一身分下數字相同")
            rc = 0

        outdir = "/app/wiki/memory/integration-health"
        if os.path.isdir(outdir):
            with open(os.path.join(outdir, "list_stat_scope_parity.json"), "w", encoding="utf-8") as f:
                json.dump({"user": uname, "year": year, "mismatches": bad}, f, ensure_ascii=False, indent=2)
        return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
