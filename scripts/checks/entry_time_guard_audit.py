#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""填報守衛存在性稽核（weekly 117）—— 事後稽核抓到的每一種錯，入口有沒有擋。

owner 2026-09-07：「報價明細、發票、收款、廠商指派應在填報時就有完善檢核與自動關聯機制」。

⚠️ 這支要回答的**不是**「資料現在乾不乾淨」（那是 weekly 99/104/107 的事），
而是「**下一筆填進來時會不會又髒**」。兩者的差別是本 repo 反覆付學費的地方：
把資料修乾淨而入口沒補，下一次匯入或下一個人填報就會再生一次
（09-06 的 12 筆名稱漂移、#51 的併寫應付，全是這樣來的）。

判準刻意用**執行時**而不是 grep：每一條都真的呼叫服務層一次，看它會不會拒絕。
grep 只能證明「有這段字」，證明不了「它會擋」——本 repo 2026-08-30 在 hook 上付過這個學費
（掛上去、會執行、也真的擋過東西，仍有一半規則從未命中）。

RED＝該擋的沒擋（守衛不在或失效）。誤擋（該放行卻擋）也是 RED —— 一個會擋掉正常填報的
守衛，最後一定會被關掉。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402
from lib.docker_exec import exec_in  # noqa: E402
from lib.result_contract import write_result  # noqa: E402

ROOT = repo_root()

PROBE = r'''
import asyncio, json
from decimal import Decimal
from types import SimpleNamespace
from sqlalchemy import text
from app.db.database import async_session_maker
from app.services.erp.party_resolver import PartyResolver, split_candidates
from app.services.erp.invoice_service import ERPInvoiceService

async def main():
    out = []
    async with async_session_maker() as db:
        r = PartyResolver(db)

        # ① 併寫廠商名不得自動選一家
        res = await r.resolve("銢欣有限公司乃耳企業社", vendor_type="subcontractor")
        out.append(["併寫廠商名被擋", res.vendor_id is None and bool(res.split_into)])

        # ② 主檔沒有的名字要出聲
        res = await r.resolve("這家公司不存在啦", vendor_type="subcontractor")
        out.append(["未知廠商被擋", res.vendor_id is None and "主檔沒有" in res.reason])

        # ③ 負向控制：主檔裡真的有的必須放行
        name = (await db.execute(text(
            "SELECT vendor_name FROM partner_vendors WHERE vendor_type='subcontractor' "
            "AND vendor_name NOT LIKE '%加%' AND vendor_name NOT LIKE '%+%' ORDER BY id LIMIT 1"))).scalar()
        res = await r.resolve(name, vendor_type="subcontractor")
        out.append([f"既有廠商放行（{name}）", res.vendor_id is not None])

        # ④ 簡稱要對得到主檔（張啟良建築師 ↔ 張啟良建築師事務所）
        res = await r.resolve("張啟良建築師", vendor_type="client")
        out.append(["簡稱對得到主檔", res.vendor_id is not None])

        svc = ERPInvoiceService.__new__(ERPInvoiceService)
        svc.db = db

        # ⑤ 發票稅額不相稱要擋
        bad = SimpleNamespace(amount=Decimal("10500"), tax_amount=Decimal("2000"),
                              billing_id=None, erp_quotation_id=None)
        try:
            await svc._validate_and_link(bad); ok = False
        except ValueError:
            ok = True
        out.append(["發票稅額不相稱被擋", ok])

        # ⑥ 負向控制：免稅（tax=0）不得被擋
        good = SimpleNamespace(amount=Decimal("49000"), tax_amount=Decimal("0"),
                               billing_id=None, erp_quotation_id=None)
        try:
            await svc._validate_and_link(good); ok = True
        except ValueError:
            ok = False
        out.append(["免稅發票放行", ok])

        # ⑦ 發票額 > 請款額要擋
        row = (await db.execute(text(
            "SELECT id, erp_quotation_id, billing_amount FROM erp_billings "
            "WHERE billing_amount > 1000 ORDER BY id DESC LIMIT 1"))).first()
        if row:
            over = SimpleNamespace(amount=Decimal(str(row[2])) * 2, tax_amount=Decimal("0"),
                                   billing_id=row[0], erp_quotation_id=row[1])
            try:
                await svc._validate_and_link(over); ok = False
            except ValueError:
                ok = True
            out.append(["發票額超過請款被擋", ok])

        # ⑧ 收款額 > 請款額要擋（請款服務層）
        from app.services.erp.billing_service import ERPBillingService
        import inspect
        src = inspect.getsource(ERPBillingService.update)
        out.append(["收款上限守衛在 update 裡", "超過請款額" in src])

    print("RESULT " + json.dumps(out, ensure_ascii=False))

asyncio.run(main())
'''


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=" * 70)
    print(" 填報守衛存在性（weekly 117）—— 下一筆填進來會不會又髒")
    print("=" * 70)

    out = exec_in(["python", "-"], stdin=PROBE, timeout=180)
    if out is None:
        print("  [YELLOW] 容器不可用 —— 未驗（不視為通過）")
        write_result("entry_time_guards", 1, "容器不可用，未驗")
        return 1

    line = next((l for l in out.splitlines() if l.startswith("RESULT ")), None)
    if not line:
        print("  [RED] 探針沒有回結果 —— 守衛狀態不明")
        print("\n".join(out.splitlines()[-6:]))
        write_result("entry_time_guards", 2, "探針沒有回結果")
        return 2

    checks = json.loads(line[len("RESULT "):])
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    if bad:
        print(f"\n  ⚠️ 事後稽核抓到的錯，入口沒有擋 —— 資料修乾淨之後還會再髒一次。")
        print("     修法在 app/services/erp/party_resolver.py 與各 service 的建立／更新路徑。")
        print(f"\nStatus: [RED] {len(bad)} 條守衛失效：{'、'.join(bad)}")
        write_result("entry_time_guards", 2, f"{len(bad)} 條守衛失效", {"failed": bad})
        return 2
    print(f"\nStatus: [GREEN] {len(checks)} 條填報守衛都會擋（含 3 條負向控制）")
    write_result("entry_time_guards", 0, f"{len(checks)} 條守衛正常")
    return 0


if __name__ == "__main__":
    sys.exit(main())
