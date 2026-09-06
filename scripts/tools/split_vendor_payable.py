#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把一筆「兩家併寫」的協力廠商應付拆成多筆（2026-09-06）。

## 為什麼需要它

匯入舊資料時，來源表把兩家廠商寫在同一格：
`銢欣有限公司乃耳企業社`（= 銢欣有限公司 80321095 ＋ 司乃耳企業社 82349892）、
`楊長燁加李雅倫`……。於是 414,750 全記在其中一家名下，另一家在系統裡查無支出。

**這支工具不猜比例。** 系統裡沒有任何憑證可以決定 414,750 怎麼分（沒有分列的報價工項、
沒有核銷發票、沒有指派金額、匯入來源檔也不在 repo 裡）。猜一個 50/50 會產生一個
看起來很像事實的數字，那比不拆更糟 —— 報表會用它算毛利、算廠商往來。
⇒ 金額由**執行的人**給，工具負責「拆得對」：總額不變、帳本跟著拆、留下可回溯的備份。

## 用法

    python scripts/tools/split_vendor_payable.py --payable 51 \\
        --to 76=300000 --to 86=114750 [--apply]

不帶 `--apply` 是試算（印出將要發生的變更，不寫入）。
`--to <vendor_id>=<金額>` 可給多筆；**各筆總和必須等於原應付金額**，否則拒絕執行。

## 它會做什麼

1. 把原應付改成第一筆的金額（保留 id、請款關聯、付款日與已付比例）
2. 為其餘每一家新增一筆應付（同報價單、同請款、同付款狀態）
3. 帳本 `finance_ledgers` 的對應支出分錄同步拆分（`source_type='erp_vendor_payable'`）
4. 備份原始列到 `wiki/memory/backups/payable_split_<id>_<時間>.json`

## 它不會做什麼

- 不動總額（拆的是歸屬，不是金額）
- 不建立廠商主檔（要拆給誰，那家必須已經在 `partner_vendors` 裡）
- 不碰發票：自動補建的發票對應的是「請款」不是「應付」
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checks"))
from lib.paths import repo_root  # noqa: E402

ROOT = repo_root()
CONTAINER = "ck_missive_backend"

SCRIPT = r'''
import asyncio, json, sys
from decimal import Decimal
from sqlalchemy import text
from app.db.database import async_session_maker

PAYABLE_ID = {pid}
SHARES = {shares}          # [(vendor_id, amount), ...]
APPLY = {apply}

async def main():
    async with async_session_maker() as db:
        row = (await db.execute(text(
            "SELECT id, erp_quotation_id, vendor_id, vendor_name, payable_amount, paid_amount, "
            "payment_status, paid_date, billing_id, description, notes "
            "FROM erp_vendor_payables WHERE id=:i"), {{"i": PAYABLE_ID}})).first()
        if not row:
            print("PAYABLE_NOT_FOUND"); return
        total = Decimal(str(row[4]))
        want = sum(Decimal(str(a)) for _, a in SHARES)
        if want != total:
            print(f"REFUSE 各筆總和 {{want}} != 原應付 {{total}} —— 拆帳不得改變總額"); return
        vendors = {{}}
        for vid, _ in SHARES:
            v = (await db.execute(text("SELECT id, vendor_name FROM partner_vendors WHERE id=:i"), {{"i": vid}})).first()
            if not v:
                print(f"REFUSE 廠商主檔沒有 id={{vid}}"); return
            vendors[vid] = v[1]
        ledger = (await db.execute(text(
            "SELECT id, amount FROM finance_ledgers WHERE source_type='erp_vendor_payable' AND source_id=:i"),
            {{"i": PAYABLE_ID}})).all()
        plan = {{"payable": dict(zip(
                    ["id","quotation","vendor_id","vendor_name","amount","paid","status","paid_date","billing_id"],
                    [row[0], row[1], row[2], row[3], str(row[4]), str(row[5]), row[6], str(row[7]), row[8]])),
                "ledger": [[l[0], str(l[1])] for l in ledger],
                "shares": [[vid, str(amt), vendors[vid]] for vid, amt in SHARES]}}
        print("PLAN " + json.dumps(plan, ensure_ascii=False))
        if not APPLY:
            print("DRY_RUN 未寫入"); return

        first_vid, first_amt = SHARES[0]
        ratio_paid = (Decimal(str(row[5] or 0)) / total) if total else Decimal(0)
        await db.execute(text(
            "UPDATE erp_vendor_payables SET vendor_id=:v, vendor_name=:n, payable_amount=:a, paid_amount=:p, "
            "notes=COALESCE(notes||' | ','')||:note, updated_at=now() WHERE id=:i"),
            {{"v": first_vid, "n": vendors[first_vid], "a": first_amt,
              "p": (Decimal(str(first_amt)) * ratio_paid).quantize(Decimal("0.01")),
              "note": f"拆帳自原始併寫列（原 {{row[3]}} 共 {{total}}）", "i": PAYABLE_ID}})
        new_ids = []
        for vid, amt in SHARES[1:]:
            r = (await db.execute(text(
                "INSERT INTO erp_vendor_payables (erp_quotation_id, vendor_id, vendor_name, payable_amount, "
                "paid_amount, payment_status, paid_date, billing_id, description, notes, created_at, updated_at) "
                "VALUES (:q,:v,:n,:a,:p,:s,:d,:b,:desc,:note, now(), now()) RETURNING id"),
                {{"q": row[1], "v": vid, "n": vendors[vid], "a": amt,
                  "p": (Decimal(str(amt)) * ratio_paid).quantize(Decimal("0.01")), "s": row[6], "d": row[7],
                  "b": row[8], "desc": row[9], "note": f"拆帳自應付 #{{PAYABLE_ID}}（原 {{row[3]}} 共 {{total}}）"}})).first()
            new_ids.append(r[0])
        if ledger:
            lid, lamt = ledger[0][0], Decimal(str(ledger[0][1]))
            await db.execute(text("UPDATE finance_ledgers SET amount=:a, vendor_id=:v, updated_at=now() WHERE id=:i"),
                             {{"a": first_amt, "v": first_vid, "i": lid}})
            for (vid, amt), nid in zip(SHARES[1:], new_ids):
                await db.execute(text(
                    "INSERT INTO finance_ledgers (case_code, entry_type, amount, description, vendor_id, "
                    "source_type, source_id, transaction_date, created_at, updated_at) "
                    "SELECT case_code, entry_type, :a, description || ' [拆帳]', :v, source_type, :sid, "
                    "transaction_date, now(), now() FROM finance_ledgers WHERE id=:lid"),
                    {{"a": amt, "v": vid, "sid": nid, "lid": lid}})
        await db.commit()
        print("APPLIED " + json.dumps({{"payable": PAYABLE_ID, "new_payables": new_ids}}, ensure_ascii=False))

asyncio.run(main())
'''


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--payable", type=int, required=True, help="要拆的應付 id")
    ap.add_argument("--to", action="append", required=True, metavar="VENDOR_ID=金額",
                    help="拆給誰、各多少（可多次）；總和必須等於原金額")
    ap.add_argument("--apply", action="store_true", help="真的寫入（不帶＝試算）")
    args = ap.parse_args()

    shares = []
    for spec in args.to:
        vid, _, amt = spec.partition("=")
        shares.append((int(vid), amt))

    code = SCRIPT.format(pid=args.payable, shares=repr(shares), apply=bool(args.apply))
    r = subprocess.run(
        ["docker", "exec", "-i", "-w", "/app", "-e", "PYTHONIOENCODING=utf-8", CONTAINER, "python", "-"],
        input=code, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
        env={"MSYS_NO_PATHCONV": "1", **dict(__import__("os").environ)},
    )
    out = [l for l in (r.stdout or "").splitlines() if not l.startswith("{\"event\"")]
    for line in out:
        print(line)
    plan = next((l[5:] for l in out if l.startswith("PLAN ")), None)
    if plan and args.apply:
        d = ROOT / "wiki" / "memory" / "backups"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"payable_split_{args.payable}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
        p.write_text(plan + "\n", encoding="utf-8")
        print(f"備份 → {p.relative_to(ROOT)}")
    if any(l.startswith("REFUSE") for l in out):
        return 2
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
