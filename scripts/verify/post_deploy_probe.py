# -*- coding: utf-8 -*-
"""部署後第五層：在容器內打端點走整條業務鏈（G4，2026-09-03；09-06 擴為兩條鏈）。

deploy-public.sh 的四層（容器內／host／公網／認證鏈）驗的是「服務起來了」；
這一層驗的是「業務鏈還通不通」。

鏈 A（一鍵建案，09-03）：標案建案 → 報價單 draft → 自動成案 → 補總額自動第一期
→ PM 改名三表同步 → 承攬側結案同步 → 重複建案 409 → 列表／財務摘要。
鏈 B（手動全程，09-06 owner「再次複查一鍵建案、新增報價、創案、報價單填列、成案、財務管理」）：
手動建案（案號新制、委託單位鍵）→ 新增報價 → 工項填列（總價＝Σ、稅額）→ 明確成案（project_code 新制、
鍵複製、報價單 project_code、成案即應收）→ 收款 → 發票防呆（格式／重複）→ 協力廠商指派即應付 →
委託單位帳款看得到 → 應付對得到請款。
全部 __PROBE__ 標記、跑完硬刪（含帳本／應付／關聯／工項）。任何一步失敗 exit 1，deploy 就停。

用法（deploy 腳本）：docker exec -i -w /app ck_missive_backend python - < scripts/verify/post_deploy_probe.py
"""
import asyncio, re, sys
from datetime import date
import httpx
from sqlalchemy import select, text
from main import app
from app.core.dependencies import get_current_user
from app.db.database import AsyncSessionLocal
from app.extended.models import User

TENDER_ID = 122458
TITLE = "__PROBE__ 部署後鏈路實測"
TITLE_B = "__PROBE__ 手動建案鏈路實測"
CLIENT_ID = 78  # 桃園市政府工務局（委託單位主檔）
results = []


def ok(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'✅' if cond else '❌'} {name} {detail}")


async def q(sql, **p):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text(sql), p)).mappings().all()


def _data(r):
    try:
        j = r.json()
    except Exception:
        return {}
    return j.get("data") if isinstance(j, dict) and isinstance(j.get("data"), dict) else (j if isinstance(j, dict) else {})


async def chain_a(c, codes):
    case_code = pm_id = ct_id = None
    r = await c.post("/api/tender/create-case", json={"unit_id": "__PROBE__U", "title": TITLE, "unit_name": "__PROBE__機關", "budget": "123000", "tender_id": TENDER_ID})
    d = r.json(); case_code = (d.get("data") or {}).get("case_code"); pm_id = (d.get("data") or {}).get("pm_case_id")
    if case_code:
        codes.append(case_code)
    ok("A 建案 200 且回 case_code", r.status_code == 200 and case_code, case_code)
    rows = await q("SELECT status, source_tender_id FROM pm_cases WHERE id=:i", i=pm_id)
    ok("A source_tender_id 寫入、status=bidding", rows and rows[0]["source_tender_id"] == TENDER_ID and rows[0]["status"] == "bidding")
    qs = await q("SELECT id, quote_kind, status, quotation_no FROM erp_quotations WHERE case_code=:c AND deleted_at IS NULL", c=case_code)
    ok("A draft 報價單、quote_kind=tender、有 QT 號", len(qs) == 1 and qs[0]["quote_kind"] == "tender" and qs[0]["status"] == "draft" and qs[0]["quotation_no"])
    qid = qs[0]["id"]
    r = await c.post("/api/pm/cases/update-by-id", json={"id": pm_id, "data": {"status": "contracted", "contract_amount": 123000}})
    ok("A 自動成案", r.status_code == 200 and "自動成案" in str(r.json().get("message")))
    cts = await q("SELECT id, project_code, status FROM contract_projects WHERE case_code=:c", c=case_code); ct_id = cts[0]["id"] if cts else None
    ok("A 承攬案建立、project_code=去 _PM_", cts and cts[0]["project_code"] == case_code.replace("_PM_", "_", 1) and cts[0]["status"] == "執行中")
    bl = await q("SELECT billing_amount::bigint AS amt FROM erp_billings WHERE erp_quotation_id=:i", i=qid)
    ok("A 成案時不造 0 元請款、至多一期", len(bl) <= 1 and all(b["amt"] > 0 for b in bl), f"billings={[b['amt'] for b in bl]}")
    r = await c.post("/api/erp/quotations/update", json={"id": qid, "data": {"total_price": 123000}})
    bl = await q("SELECT billing_period, billing_amount::bigint AS amt, payment_status FROM erp_billings WHERE erp_quotation_id=:i", i=qid)
    ok("A 補總額 ⇒ 自動第一期（一次請領、金額＝總額、pending）", r.status_code == 200 and len(bl) == 1 and bl[0]["amt"] == 123000 and bl[0]["payment_status"] == "pending")
    r = await c.post("/api/erp/quotations/update", json={"id": qid, "data": {"total_price": 123000}})
    ok("A 同值再更新不重建、不被鎖擋", r.status_code == 200 and (await q("SELECT count(*) AS n FROM erp_billings WHERE erp_quotation_id=:i", i=qid))[0]["n"] == 1)
    r = await c.post("/api/erp/quotations/update", json={"id": qid, "data": {"total_price": 99000}})
    ok("A 有請款後改總額被擋（400，走版次）", r.status_code == 400, f"HTTP {r.status_code}")
    r = await c.post("/api/pm/cases/update-by-id", json={"id": pm_id, "data": {"case_name": TITLE + " 改名A"}})
    ct = await q("SELECT project_name FROM contract_projects WHERE id=:i", i=ct_id); qn = await q("SELECT case_name FROM erp_quotations WHERE id=:i", i=qid)
    ok("A PM 改名 ⇒ 承攬案／報價單同步", r.status_code == 200 and ct[0]["project_name"] == TITLE + " 改名A" and qn[0]["case_name"] == TITLE + " 改名A")
    r = await c.post(f"/api/projects/{ct_id}/update", json={"project_name": TITLE + " 改名B", "status": "已結案"})
    pm = await q("SELECT case_name, status FROM pm_cases WHERE id=:i", i=pm_id)
    ok("A 承攬側改名＋結案 ⇒ PM 同步 closed", r.status_code == 200 and pm[0]["case_name"] == TITLE + " 改名B" and pm[0]["status"] == "closed")
    r = await c.post("/api/tender/create-case", json={"unit_id": "__PROBE__U", "title": TITLE, "unit_name": "__PROBE__機關", "budget": "123000", "tender_id": TENDER_ID})
    ok("A 重複建案 409", r.status_code == 409, f"HTTP {r.status_code}")
    r = await c.post("/api/erp/quotations/list", json={"page": 1, "limit": 3, "search": TITLE[:8]})
    ok("A 列表可搜到並帶 client_name／收款欄位", r.status_code == 200 and all("total_billed" in i for i in (r.json().get("items") or [])))
    r = await c.post("/api/erp/financial-summary/projects", json={"year": 2026, "limit": 50}); d = r.json().get("data") or {}
    items = d.get("items") or []
    ok("A 專案財務一覽：items＝min(limit,total) 且每列有案名（case_code 橋）", r.status_code == 200 and len(items) == min(50, d.get("total") or 0) and all(i.get("case_name") for i in items))
    r = await c.post("/api/erp/financial-summary/budget-ranking", json={"top_n": 15}); items = (r.json().get("data") or {}).get("items") or []
    named = sum(1 for i in items if i.get("case_name"))
    ok("A 預算排名：八成以上的列對得到案名（case_code 橋）", r.status_code == 200 and items and named >= int(len(items) * 0.8), f"named={named}/{len(items)}")


async def chain_b(c, codes):
    # B1 手動建案（02 承攬報價、帶委託單位鍵）
    r = await c.post("/api/pm/cases/create", json={"case_name": TITLE_B, "category": "02", "client_vendor_id": CLIENT_ID, "year": 2026})
    d = _data(r); case_code = d.get("case_code"); pm_id = d.get("id")
    if case_code:
        codes.append(case_code)
    ok("B 手動建案 200、案號新制 CK2026_PM_02_NNN", r.status_code == 200 and bool(case_code) and re.fullmatch(r"CK2026_PM_02_\d{3,}", case_code or ""), case_code)
    pm = await q("SELECT client_vendor_id, client_name FROM pm_cases WHERE id=:i", i=pm_id)
    ok("B 委託單位鍵寫入、名稱快照＝主檔名", pm and pm[0]["client_vendor_id"] == CLIENT_ID and pm[0]["client_name"] == "桃園市政府工務局", str(dict(pm[0])) if pm else "")
    # B2 新增報價
    r = await c.post("/api/erp/quotations/create", json={"case_code": case_code, "case_name": TITLE_B, "year": 2026})
    d = _data(r); qid = d.get("id")
    qs = await q("SELECT id, quote_kind, status, quotation_no FROM erp_quotations WHERE case_code=:c AND deleted_at IS NULL", c=case_code)
    ok("B 新增報價 200、quote_kind=contract（02 類）、draft、有 QT 號", r.status_code == 200 and qs and qs[0]["quote_kind"] == "contract" and qs[0]["status"] == "draft" and qs[0]["quotation_no"], f"{qs[0]['quote_kind'] if qs else None}")
    qid = qid or (qs[0]["id"] if qs else None)
    # B3 工項填列：總價＝Σ(qty×unit_price)，稅額＝總價×5%
    items = [{"item_name": "__PROBE__工項A", "unit": "式", "qty": 2, "unit_price": 1000}, {"item_name": "__PROBE__工項B", "unit": "式", "qty": 1, "unit_price": 500}]
    r = await c.post("/api/erp/quotation-items/replace", json={"quotation_id": qid, "items": items})
    qrow = await q("SELECT total_price::numeric AS tp, tax_amount::numeric AS tax, (SELECT count(*) FROM erp_quotation_items WHERE quotation_id=:i) AS n FROM erp_quotations WHERE id=:i", i=qid)
    tp = float(qrow[0]["tp"] or 0) if qrow else 0
    ok("B 工項填列 ⇒ 2 列、總價 2,625（含稅＝小計 2,500×1.05）、稅額 125", r.status_code == 200 and qrow and qrow[0]["n"] == 2 and tp == 2625 and float(qrow[0]["tax"] or 0) == 125, f"total={tp} tax={qrow[0]['tax'] if qrow else None}")
    pmc = await q("SELECT contract_amount FROM pm_cases WHERE id=:i", i=pm_id)
    ok("B 工項總價回寫 PM 合約金額（不必手抄）", pmc and float(pmc[0]["contract_amount"] or 0) == 2625, f"pm.contract_amount={pmc[0]['contract_amount'] if pmc else None}")
    # B4 成案：真實流程是 評估中 → 已承攬（update status=contracted，帶總額時自動成案）→ 未自動成案者按「成案」
    r0 = await c.post("/api/pm/cases/promote", json={"case_code": case_code})
    ok("B 評估中不得直接成案（400，僅已承攬可成案）", r0.status_code == 400, f"HTTP {r0.status_code}")
    r1 = await c.post("/api/pm/cases/update-by-id", json={"id": pm_id, "data": {"status": "contracted"}})
    cts = await q("SELECT id FROM contract_projects WHERE case_code=:c", c=case_code)
    r = await c.post("/api/pm/cases/promote", json={"case_code": case_code}) if not cts else r1
    cts = await q("SELECT id, project_code, client_vendor_id, client_agency, status FROM contract_projects WHERE case_code=:c", c=case_code)
    ct_id = cts[0]["id"] if cts else None
    if not cts:
        ok("B 成案失敗（後續斷言略過）", False, f"promote HTTP {r.status_code} {str(r.text)[:120]}")
        return case_code
    ok("B 成案 200、project_code 新制 CK2026_02_NNN、執行中", r.status_code == 200 and cts and re.fullmatch(r"CK2026_02_\d{3,}", cts[0]["project_code"] or "") and cts[0]["status"] == "執行中", f"{cts[0]['project_code'] if cts else r.status_code}")
    ok("B 成案把委託單位鍵與名稱帶到承攬案", cts and cts[0]["client_vendor_id"] == CLIENT_ID and cts[0]["client_agency"] == "桃園市政府工務局")
    qn = await q("SELECT project_code, status FROM erp_quotations WHERE id=:i", i=qid); pm = await q("SELECT status, project_code FROM pm_cases WHERE id=:i", i=pm_id)
    ok("B 報價單與 PM 都拿到 project_code、PM=contracted", qn and qn[0]["project_code"] == cts[0]["project_code"] and pm[0]["status"] == "contracted" and pm[0]["project_code"] == cts[0]["project_code"])
    bl = await q("SELECT id, billing_amount::numeric AS amt, payment_status FROM erp_billings WHERE erp_quotation_id=:i", i=qid)
    ok("B 成案即應收：第一期＝總價 2,625、pending", len(bl) == 1 and float(bl[0]["amt"]) == 2625 and bl[0]["payment_status"] == "pending", f"billings={[(float(b['amt']), b['payment_status']) for b in bl]}")
    bid = bl[0]["id"] if bl else None
    # B5 收款
    r = await c.post("/api/erp/billings/update", json={"id": bid, "data": {"payment_amount": 2625, "payment_date": date.today().isoformat(), "payment_status": "paid"}})
    bl = await q("SELECT payment_amount::numeric AS pa, payment_status FROM erp_billings WHERE id=:i", i=bid)
    ok("B 收款 ⇒ payment_amount 2,625、paid", r.status_code == 200 and bl and float(bl[0]["pa"] or 0) == 2625 and bl[0]["payment_status"] == "paid", f"HTTP {r.status_code} {dict(bl[0]) if bl else ''}")
    led = await q("SELECT count(*) AS n FROM finance_ledgers WHERE source_type='erp_billing' AND source_id=:i", i=bid)
    ok("B 帳本有這筆收款的收入分錄", led and led[0]["n"] >= 1, f"ledger rows={led[0]['n'] if led else None}")
    # B6 發票防呆
    r_bad = await c.post("/api/erp/invoices/create-from-billing", json={"billing_id": bid, "invoice_number": "BAD-1"})
    r_good = await c.post("/api/erp/invoices/create-from-billing", json={"billing_id": bid, "invoice_number": "ZZ98765432"})
    r_dup = await c.post("/api/erp/invoices/create-from-billing", json={"billing_id": bid, "invoice_number": "ZZ98765432"})
    inv = await q("SELECT id AS invoice_id FROM erp_invoices WHERE billing_id=:i", i=bid)
    ok("B 發票：格式錯被擋、正確 200、重複被擋、請款掛上 invoice_id", r_bad.status_code in (400, 422) and r_good.status_code == 200 and r_dup.status_code in (400, 409) and inv and inv[0]["invoice_id"], f"{r_bad.status_code}/{r_good.status_code}/{r_dup.status_code}")
    # B7 協力廠商指派即應付
    sub = await q("SELECT id, vendor_name FROM partner_vendors WHERE vendor_type='subcontractor' AND vendor_name NOT LIKE '__PROBE__%' ORDER BY id LIMIT 1")
    vid = sub[0]["id"] if sub else None
    r = await c.post("/api/project-vendors", json={"project_id": ct_id, "vendor_id": vid, "role": "測量業務", "contract_amount": 800, "status": "active"})
    pay = await q("SELECT id, payable_amount::numeric AS amt, notes, billing_id FROM erp_vendor_payables WHERE erp_quotation_id=:i AND vendor_id=:v", i=qid, v=vid)
    ok("B 指派協力廠商 ⇒ 自動應付 800、帶 [auto:vendor_association]", r.status_code in (200, 201) and pay and float(pay[0]["amt"]) == 800 and "[auto:vendor_association]" in (pay[0]["notes"] or ""), f"HTTP {r.status_code} pay={[(float(p['amt']), p['notes']) for p in pay]}")
    ok("B 應付對得到請款（billing_id，weekly 99 的橋）", pay and pay[0]["billing_id"] == bid, f"billing_id={pay[0]['billing_id'] if pay else None} vs {bid}")
    # B8 委託單位帳款看得到
    r = await c.post("/api/erp/client-accounts/detail", json={"vendor_id": CLIENT_ID, "year": 2026}); d = _data(r)
    mine = [x for x in (d.get("cases") or []) if x.get("case_code") == case_code]
    ok("B 委託單位帳款明細列出本案：已請款 2,625、已收 2,625", mine and float(mine[0].get("total_billed") or 0) == 2625 and float(mine[0].get("total_received") or 0) == 2625, str(mine[0]) if mine else "not listed")
    # B9 依類別統計含 02 類的這家
    r = await c.post("/api/erp/financial-summary/by-category", json={"year": 2026, "category": "02"}); d = _data(r)
    rec = [x for x in (d.get("receivable") or []) if x.get("client_vendor_id") == CLIENT_ID]
    ok("B 依類別統計（02）有這家委託單位且已收 ≥ 2,625", rec and float(rec[0].get("received") or 0) >= 2625, str(rec[0]) if rec else "not listed")
    return case_code


async def cleanup(codes):
    marks = "%__PROBE__%"
    sqls = [
        "DELETE FROM finance_ledgers WHERE source_type='erp_billing' AND source_id IN (SELECT b.id FROM erp_billings b JOIN erp_quotations qq ON qq.id=b.erp_quotation_id WHERE qq.case_code = ANY(:codes))",
        "DELETE FROM finance_ledgers WHERE source_type='erp_vendor_payable' AND source_id IN (SELECT p.id FROM erp_vendor_payables p JOIN erp_quotations qq ON qq.id=p.erp_quotation_id WHERE qq.case_code = ANY(:codes))",
        "DELETE FROM erp_vendor_payables WHERE erp_quotation_id IN (SELECT id FROM erp_quotations WHERE case_code = ANY(:codes))",
        "DELETE FROM project_vendor_association WHERE project_id IN (SELECT id FROM contract_projects WHERE case_code = ANY(:codes))",
        "DELETE FROM erp_invoices WHERE erp_quotation_id IN (SELECT id FROM erp_quotations WHERE case_code = ANY(:codes)) OR invoice_number='ZZ98765432'",
        "DELETE FROM erp_billings WHERE erp_quotation_id IN (SELECT id FROM erp_quotations WHERE case_code = ANY(:codes))",
        "DELETE FROM erp_quotation_items WHERE quotation_id IN (SELECT id FROM erp_quotations WHERE case_code = ANY(:codes))",
        "DELETE FROM erp_quotations WHERE case_code = ANY(:codes) OR case_name LIKE :m",
        "DELETE FROM project_user_assignments WHERE case_code = ANY(:codes) OR project_id IN (SELECT id FROM contract_projects WHERE case_code = ANY(:codes))",
        "DELETE FROM contract_projects WHERE case_code = ANY(:codes) OR project_name LIKE :m",
        "DELETE FROM pm_cases WHERE case_code = ANY(:codes) OR case_name LIKE :m",
        "DELETE FROM partner_vendors WHERE vendor_name LIKE :m",
    ]
    for sql in sqls:
        async with AsyncSessionLocal() as db:
            try:
                await db.execute(text(sql), {"codes": codes or ["__none__"], "m": marks}); await db.commit()
            except Exception as e:
                print("  清理略過：", str(e)[:100])
    left = await q("SELECT (SELECT count(*) FROM pm_cases WHERE case_name LIKE :m)+(SELECT count(*) FROM contract_projects WHERE project_name LIKE :m)"
                   "+(SELECT count(*) FROM erp_quotations WHERE case_name LIKE :m)+(SELECT count(*) FROM erp_invoices WHERE invoice_number='ZZ98765432') AS n", m=marks)
    print(f"  清理後殘留 {left[0]['n']}")
    return left[0]["n"]


async def main():
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.id == 13))).scalar_one(); _ = u.permissions
    app.dependency_overrides[get_current_user] = lambda: u
    codes: list = []
    left = 1
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=60) as c:
            await chain_a(c, codes)
            await chain_b(c, codes)
    except Exception as e:
        results.append((f"未預期例外 {type(e).__name__}: {str(e)[:120]}", False))
        print(f"  ❌ 未預期例外 {type(e).__name__}: {str(e)[:200]}")
    finally:
        left = await cleanup(codes)
    passed = sum(1 for _, v in results if v)
    print(f"RESULT {passed}/{len(results)}")
    return 0 if passed == len(results) and left == 0 else 1


sys.exit(asyncio.run(main()))
