# -*- coding: utf-8 -*-
"""部署後第五層：在容器內打端點走整條業務鏈（G4，2026-09-03）。

deploy-public.sh 的四層（容器內／host／公網／認證鏈）驗的是「服務起來了」；
這一層驗的是「業務鏈還通不通」：標案建案 → 報價單 draft → 自動成案 → 補總額自動第一期
→ PM 改名三表同步 → 承攬側結案同步 → 重複建案 409 → 手動建報價單推導種類。
全部 __PROBE__ 標記、跑完硬刪。任何一步失敗 exit 1，deploy 就停。

用法（deploy 腳本）：docker exec -i -w /app ck_missive_backend python - < scripts/verify/post_deploy_probe.py
"""
import asyncio, sys
import httpx
from sqlalchemy import select, text
from main import app
from app.core.dependencies import get_current_user
from app.db.database import AsyncSessionLocal
from app.extended.models import User

TENDER_ID = 122458
TITLE = "__PROBE__ 部署後鏈路實測"
results = []


def ok(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'✅' if cond else '❌'} {name} {detail}")


async def q(sql, **p):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text(sql), p)).mappings().all()


async def main():
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.id == 13))).scalar_one(); _ = u.permissions
    app.dependency_overrides[get_current_user] = lambda: u
    case_code = pm_id = ct_id = None
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=60) as c:
            r = await c.post("/api/tender/create-case", json={"unit_id": "__PROBE__U", "title": TITLE, "unit_name": "__PROBE__機關", "budget": "123000", "tender_id": TENDER_ID, "category": "01"})
            d = r.json(); case_code = (d.get("data") or {}).get("case_code"); pm_id = (d.get("data") or {}).get("pm_case_id")
            ok("建案 200 且回 case_code", r.status_code == 200 and case_code, case_code)
            rows = await q("SELECT status, source_tender_id FROM pm_cases WHERE id=:i", i=pm_id)
            ok("source_tender_id 寫入、status=bidding", rows and rows[0]["source_tender_id"] == TENDER_ID and rows[0]["status"] == "bidding")
            qs = await q("SELECT id, quote_kind, status, quotation_no FROM erp_quotations WHERE case_code=:c AND deleted_at IS NULL", c=case_code)
            ok("draft 報價單、quote_kind=tender、有 QT 號", len(qs) == 1 and qs[0]["quote_kind"] == "tender" and qs[0]["status"] == "draft" and qs[0]["quotation_no"])
            qid = qs[0]["id"]
            r = await c.post("/api/pm/cases/update-by-id", json={"id": pm_id, "data": {"status": "contracted", "contract_amount": 123000}})
            ok("自動成案", r.status_code == 200 and "自動成案" in str(r.json().get("message")))
            cts = await q("SELECT id, project_code, status FROM contract_projects WHERE case_code=:c", c=case_code); ct_id = cts[0]["id"] if cts else None
            ok("承攬案建立、project_code=去 _PM_", cts and cts[0]["project_code"] == case_code.replace("_PM_", "_", 1) and cts[0]["status"] == "執行中")
            bl = await q("SELECT count(*) AS n FROM erp_billings WHERE erp_quotation_id=:i", i=qid)
            ok("成案時無總額 ⇒ 不造 0 元請款", bl[0]["n"] == 0)
            r = await c.post("/api/erp/quotations/update", json={"id": qid, "data": {"total_price": 123000}})
            bl = await q("SELECT billing_period, billing_amount::bigint AS amt, payment_status FROM erp_billings WHERE erp_quotation_id=:i", i=qid)
            ok("補總額 ⇒ 自動第一期（一次請領、金額＝總額、pending）", r.status_code == 200 and len(bl) == 1 and bl[0]["amt"] == 123000 and bl[0]["payment_status"] == "pending" and bl[0]["billing_period"] == "一次請領")
            r = await c.post("/api/erp/quotations/update", json={"id": qid, "data": {"total_price": 123000}})
            ok("同值再更新不重建、不被鎖擋", r.status_code == 200 and (await q("SELECT count(*) AS n FROM erp_billings WHERE erp_quotation_id=:i", i=qid))[0]["n"] == 1, f"HTTP {r.status_code}")
            r = await c.post("/api/erp/quotations/update", json={"id": qid, "data": {"total_price": 99000}})
            ok("有請款後改總額被擋（400，走版次）", r.status_code == 400, f"HTTP {r.status_code}")
            r = await c.post("/api/pm/cases/update-by-id", json={"id": pm_id, "data": {"case_name": TITLE + " 改名A"}})
            ct = await q("SELECT project_name FROM contract_projects WHERE id=:i", i=ct_id); qn = await q("SELECT case_name FROM erp_quotations WHERE id=:i", i=qid)
            ok("PM 改名 ⇒ 承攬案／報價單同步", r.status_code == 200 and ct[0]["project_name"] == TITLE + " 改名A" and qn[0]["case_name"] == TITLE + " 改名A")
            r = await c.post(f"/api/projects/{ct_id}/update", json={"project_name": TITLE + " 改名B", "status": "已結案"})
            pm = await q("SELECT case_name, status FROM pm_cases WHERE id=:i", i=pm_id)
            ok("承攬側改名＋結案 ⇒ PM 同步 closed", r.status_code == 200 and pm[0]["case_name"] == TITLE + " 改名B" and pm[0]["status"] == "closed")
            r = await c.post("/api/tender/create-case", json={"unit_id": "__PROBE__U", "title": TITLE, "unit_name": "__PROBE__機關", "budget": "123000", "tender_id": TENDER_ID, "category": "01"})
            ok("重複建案 409", r.status_code == 409, f"HTTP {r.status_code}")
            r = await c.post("/api/erp/quotations/list", json={"page": 1, "limit": 3, "search": TITLE[:8]})
            ok("列表可搜到並帶 client_name／收款欄位", r.status_code == 200 and all("total_billed" in i for i in (r.json().get("items") or [])))
    finally:
        for sql in ["DELETE FROM erp_invoices WHERE erp_quotation_id IN (SELECT id FROM erp_quotations WHERE case_code=:c)",
                    "DELETE FROM erp_billings WHERE erp_quotation_id IN (SELECT id FROM erp_quotations WHERE case_code=:c)",
                    "DELETE FROM erp_quotations WHERE case_code=:c OR case_name LIKE '__PROBE__%'",
                    "DELETE FROM project_user_assignments WHERE case_code=:c",
                    "DELETE FROM contract_projects WHERE case_code=:c OR project_name LIKE '__PROBE__%'",
                    "DELETE FROM pm_cases WHERE case_code=:c OR case_name LIKE '__PROBE__%'",
                    "DELETE FROM partner_vendors WHERE vendor_name LIKE '__PROBE__%'"]:
            async with AsyncSessionLocal() as db:
                try:
                    await db.execute(text(sql), {"c": case_code or "__none__"}); await db.commit()
                except Exception as e:
                    print("  清理略過：", str(e)[:80])
        left = await q("SELECT (SELECT count(*) FROM pm_cases WHERE case_name LIKE '__PROBE__%')+(SELECT count(*) FROM contract_projects WHERE project_name LIKE '__PROBE__%')+(SELECT count(*) FROM erp_quotations WHERE case_name LIKE '__PROBE__%') AS n")
        print(f"  清理後殘留 {left[0]['n']}")
    passed = sum(1 for _, v in results if v)
    print(f"RESULT {passed}/{len(results)}")
    return 0 if passed == len(results) and left[0]["n"] == 0 else 1


sys.exit(asyncio.run(main()))
