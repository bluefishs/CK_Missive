# -*- coding: utf-8 -*-
"""金流異常判準的方向一致性（weekly 127）

## 為什麼需要這一支

2026-09-08 owner：「5 筆的『已收 17,850』已付清、發票多開 —— 是否異常案件標註
機制並增列篩選查詢」。做出來的機制（`app/services/erp/finance_anomaly.py`）
與既有的 weekly 104（`erp_amount_semantics_audit.py`）問的是同一族問題。

**它們不是同一份判準，這是刻意的**：weekly 104 逐筆比對（這張發票 vs 它綁的
那次請款），異常機制逐案彙總（這一案的發票合計 vs 請款合計）。兩種粒度會給出
不同的答案 —— 一案分兩次開票互相補足時逐筆會紅而逐案不紅；發票沒綁 `billing_id`
時逐筆看不到而逐案看得到。硬做成同一份，會有一邊被迫改成錯的粒度。

⇒ 要防的不是「數字不相等」，是**「一邊改了另一邊不動」**。
   判準：同一族的兩個判準，一邊抓到 ≥1 而另一邊是 **0**，就是訊號 ——
   要嘛真的只剩一種粒度看得到（那要寫下來），要嘛有人動了其中一份。

⚠️ 反過來（兩邊都 0）是正常的：那代表這一族目前沒有問題。
⚠️ 兩邊都 >0 也是正常的：數量本來就不會相等（粒度不同）。

## 誰跑它

weekly 127
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402  共用層（weekly 93）

#: (族名, 服務層的 code, weekly 104 的 SQL 條件)
#: SQL 用 weekly 104 的**逐筆**粒度，服務層用它自己的逐案粒度 —— 兩邊都不改。
FAMILIES = [
    ("發票超過請款", "invoice_over_billing",
     "SELECT COUNT(*) FROM erp_invoices i JOIN erp_billings b ON b.id = i.billing_id "
     "WHERE i.voided_at IS NULL AND i.amount > b.billing_amount * 1.01"),
    ("已收超過請款", "paid_over_billing",
     "SELECT COUNT(*) FROM erp_billings "
     "WHERE COALESCE(payment_amount, 0) > billing_amount"),
]


def probe():
    """在容器內同時跑兩邊 —— 服務層要 import，所以只能在後端容器裡跑。"""
    lines = [
        "import asyncio, json",
        "from sqlalchemy import text",
        "from app.db.database import AsyncSessionLocal",
        "from app.services.erp import finance_anomaly",
        f"FAMS = {FAMILIES!r}",
        "async def m():",
        "    out = []",
        "    async with AsyncSessionLocal() as db:",
        "        found = await finance_anomaly.scan(db)",
        "        for name, code, sql in FAMS:",
        "            svc = sum(1 for v in found.values() if any(a['code'] == code for a in v))",
        "            chk = (await db.execute(text(sql))).scalar() or 0",
        "            out.append([name, code, svc, int(chk)])",
        "    print(json.dumps(out, ensure_ascii=False))",
        "asyncio.run(m())",
    ]
    try:
        out = python_in("\n".join(lines))
        import json
        for line in reversed((out or "").strip().splitlines()):
            line = line.strip()
            if line.startswith("["):
                return json.loads(line)
    except Exception:
        return None
    return None


def main() -> int:
    rows = probe()
    print("=== 金流異常判準方向一致性（weekly 127）===")
    if rows is None:
        # 連不到就回 YELLOW 不回 GREEN —— 「沒有查證」不是「通過」。
        print("  連不到後端容器／DB —— 未驗，不視為通過")
        print("\nStatus: [YELLOW] 未能查證")
        return 1

    reds = []
    for name, code, svc, chk in rows:
        mark = "ok"
        if (svc > 0) != (chk > 0):
            mark = "**只有一邊看得到**"
            reds.append((name, code, svc, chk))
        print(f"  {name}｜異常機制（逐案）{svc}｜weekly 104（逐筆）{chk}｜{mark}")

    if reds:
        print("\n  ⚠️ 粒度不同本來就不會等量，但**一邊 0 一邊非 0** 代表：")
        print("     要嘛這一族只剩一種粒度看得到（請寫進 FIELD_SEMANTICS.md），")
        print("     要嘛有人改了其中一份判準而另一份沒跟上。")
        print("\nStatus: [RED] " + "、".join(
            f"{n}（逐案 {s} vs 逐筆 {c}）" for n, _, s, c in reds))
        return 2
    print("\nStatus: [GREEN] 兩種粒度的判準方向一致")
    return 0


def self_test() -> None:
    """負向控制：判準本身要能對「一邊 0 一邊非 0」出聲。

    不打 DB —— 直接餵造出來的計數，確認分類邏輯本身是對的。
    （這一步的意義：weekly 127 若永遠不可能紅，它與沒有檢核是同一個下場。）
    """
    def verdict(svc, chk):
        return (svc > 0) != (chk > 0)
    assert verdict(5, 0) is True, "逐案抓到而逐筆 0 —— 必須出聲"
    assert verdict(0, 3) is True, "逐筆抓到而逐案 0 —— 必須出聲"
    assert verdict(0, 0) is False, "兩邊都沒有問題 —— 不得誤報"
    assert verdict(5, 3) is False, "粒度不同、數量不等是正常的 —— 不得誤報"
    print("self_test OK")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main())
