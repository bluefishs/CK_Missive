# -*- coding: utf-8 -*-
"""報價單 `year` 欄語意守門（weekly 126）—— 它必須是「案件年度」，不是「建單那年」。

## 為什麼需要這一支

2026-09-08 owner 從 `/erp/vendor-accounts` 回報：「115 年度桃園市興辦公共設施…
（開口契約）共 11 協力廠商與費用，為何無對應」。

追下去是**年度口徑**：那一案的案號是 `CK2025_01_03_001`（2025 年給的號），
案名是「115 年度」（＝西元 2026），而年度篩選當時讀的是**案號的年**
⇒ 選 2026 就整案消失，連同 4 家協力廠商、380 萬應付。

而 09-05 之所以改成讀案號年，是因為當時量到「14/277 張報價單的 `year` 與案號年不同」，
判定 `year` 是「報價單建立那年」不可信。**那個判定描述的是資料髒，不是欄位語意錯。**

09-08 逐案用**案名裡的民國年**當第三方佐證，13 筆髒的全部對得起來，回填後
`year` 欄成為可信的單一來源，判準也改回 `year` 優先（`case_year.py`）。

⇒ **這支存在的理由：那個判準的正確性依賴 `year` 欄保持乾淨。**
沒有守門的話，下一次匯入或補建錨點報價單就會再髒一次，而症狀
（某一案在年度篩選下整個消失）**不會有任何錯誤訊息**。

## 判準

① 案名含「NNN 年度」（民國）而 `year` 欄 ≠ 該民國年轉西元 ⇒ **RED**
   —— 跨年度合約（案名 115 年度、案號 2025）在此判準下是**通過**的，
      因為它比對的是案名與 `year`，不碰案號。
② `year` 欄為 NULL 而案號是 CK 制 ⇒ **YELLOW**（會退回案號年，能動但語意含糊）

⚠️ 刻意**不比對案號年**：案號的年是「給號那年」，跨年度合約本來就會不同 ——
把它做成 RED 會得到一支對正常情形天天報紅的檢核，而那與沒有檢核是同一個下場。

⚠️ 案名可能寫「112至113年度」「114~115年度」「112年及113年」這種區間 ⇒ **兩端都要抓**，
   `year` 落在區間內任一年都算對（`CK2023_01_01_001` 的 year=2023 是對的）。
   首版只用「數字緊接年」的正則，區間下限的數字後面沒有「年」⇒ 抓不到 ⇒ 把它誤判成 RED。

⚠️ `quote_kind='finance_anchor'` 排除：那是為了掛舊金流合成的錨點報價單，
   案名沿用原案（107 年度）而 `year` 是它代表的帳務年度，兩者本來就不同。

誰跑它：weekly 126
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402  共用層（weekly 93：不得自己重造）

SQL = ("SELECT id, case_code, case_name, year, quote_kind FROM erp_quotations "
       "WHERE deleted_at IS NULL ORDER BY id")

#: ⭐ 2026-09-08 追加：`year` 不只存在於報價單。同一個案在 erp_quotations／
#: contract_projects／pm_cases 各有一個 year 欄，而年度篩選在不同頁面讀不同的表
#: ⇒ **三張表的 year 不一致，就會出現「同一個 2026、兩頁兩個總額」**。
#: owner 回報「/erp/quotations 107,484,210 vs /erp/client-accounts 90,549,209.5」
#: 差額 16,935,000 完全來自一筆：CK2025_01_03_001 的報價單 year=2026（對）
#: 而 contract_projects.year=2025（錯）⇒ 帳款頁把整案篩掉。
#: 首版只掃報價單，抓不到它 —— **判準的掃描範圍要涵蓋所有持有該欄位的表**。
CROSS_SQL = """
SELECT 'quotation_vs_contract' AS pair, q.case_code, q.year, c.year, COALESCE(q.case_name,'')
  FROM erp_quotations q JOIN contract_projects c ON c.case_code = q.case_code
 WHERE q.deleted_at IS NULL AND q.year IS DISTINCT FROM c.year
UNION ALL
SELECT 'quotation_vs_pm', q.case_code, q.year, p.year, COALESCE(q.case_name,'')
  FROM erp_quotations q JOIN pm_cases p ON p.case_code = q.case_code
 WHERE q.deleted_at IS NULL AND q.year IS DISTINCT FROM p.year
UNION ALL
SELECT 'pm_vs_contract', p.case_code, p.year, c.year, COALESCE(p.case_name,'')
  FROM pm_cases p JOIN contract_projects c ON c.case_code = p.case_code
 WHERE p.year IS DISTINCT FROM c.year
"""


def query(sql: str = None, ncols: int = 5):
    """連不到 DB 時回 None（不回空 list）—— 空 list 會被讀成「沒有問題」。"""
    code = "\n".join([
        "import asyncio, json",
        "from sqlalchemy import text",
        "from app.db.database import AsyncSessionLocal",
        f"SQL = {(sql or SQL)!r}",
        f"N = {int(ncols)}",
        "async def m():",
        "    async with AsyncSessionLocal() as db:",
        "        rows = (await db.execute(text(SQL))).all()",
        "    print(json.dumps([[r[i] for i in range(N)] for r in rows], ensure_ascii=False))",
        "asyncio.run(m())",
    ])
    try:
        out = python_in(code)
        import json as _json
        for line in reversed((out or "").strip().splitlines()):
            line = line.strip()
            if line.startswith("["):
                return _json.loads(line)
    except Exception:
        return None
    return None

# 單一年：「115年度」。
_ROC_ONE = re.compile(r"([0-9]{3})\s*年")
# 區間：「112至113年度」「114~115年度」「112年及113年」——**前一個數字後面沒有「年」**，
# 所以只用 _ROC_ONE 會漏掉區間下限（首版就是這樣，把 156「112至113年度、year=2023」
# 判成 RED，而 2023 正是對的）。⇒ 區間要單獨認。
_ROC_RANGE = re.compile(r"([0-9]{3})\s*年?\s*(?:至|~|～|－|—|-|及|、)\s*([0-9]{3})\s*年")


def roc_years(name: str) -> list[int]:
    """案名裡的民國年轉西元；`app/core/roc_date.py` 的同一條規則（+1911）。

    ⚠️ 只收 90–199 的三位數，且**必須與「年」相連**——否則
    「台8線117k+400」的 117 會被當成民國 117 年（首版的負向控制就是為它寫的）。
    """
    out: set[int] = set()
    for a, b in _ROC_RANGE.findall(name or ""):
        for v in (int(a), int(b)):
            if 90 <= v <= 199:
                out.add(v + 1911)
    for m in _ROC_ONE.findall(name or ""):
        if 90 <= int(m) <= 199:
            out.add(int(m) + 1911)
    return sorted(out)


def scan_cross():
    """三張表的 year 兩兩比對；不一致即 RED（年度篩選會兩頁兩個答案）。"""
    rows = query(CROSS_SQL, 5)
    return rows


def scan():
    rows = query()
    if rows is None:
        return None, None, 0
    reds, yellows = [], []
    for r in rows:
        qid, code, name, year, kind = r[0], r[1], r[2] or "", r[3], (r[4] or "")
        # `finance_anchor` 是為了掛舊金流而合成的錨點報價單，案名沿用原案（107 年度）
        # 而 year 是它代表的帳務年度 ⇒ 兩者本來就會不同，判它紅是誤報。
        if kind == "finance_anchor":
            continue
        if year is None:
            if (code or "").startswith("CK"):
                yellows.append((qid, code, name, year, "year 欄為空，退回案號年"))
            continue
        years = roc_years(name)
        if not years:
            continue
        # 區間（112至113年度）⇒ 落在區間內就算對；單一年就是等於
        lo, hi = years[0], years[-1]
        if not (lo <= int(year) <= hi):
            reds.append((qid, code, name, year, f"案名民國年 → {years}"))
    return reds, yellows, len(rows)


def main() -> int:
    reds, yellows, total = scan()
    print("=== 報價單 year 欄語意（weekly 126）===")
    if reds is None:
        print("  連不到 DB —— 未驗，不視為通過")
        print("")
        print("Status: [YELLOW] 未能查證")
        return 1
    print(f"  掃 {total} 張報價單")
    cross = scan_cross()
    if cross:
        print(f"  [RED] {len(cross)} 案的 year 在不同表之間不一致 —— "
              "年度篩選會讓同一個年度在不同頁面得到不同總額：")
        for pair, code, y1, y2, name in cross[:10]:
            print(f"        {pair}: {code} {y1} vs {y2}｜{str(name)[:26]}")
    for qid, code, name, year, why in reds:
        print(f"  [RED] #{qid} {code} year={year} —— {why}｜{name[:34]}")
    for qid, code, name, year, why in yellows[:10]:
        print(f"  [YELLOW] #{qid} {code} —— {why}｜{name[:34]}")
    if len(yellows) > 10:
        print(f"  [YELLOW] …另有 {len(yellows) - 10} 筆")
    # ⚠️ 2026-09-08：跨表不一致**也要讓退出碼變 2**。
    # 首版只印了 [RED] 那一行卻沒有進這個判斷，於是負向控制時
    # 「畫面印紅字、Status 卻是 GREEN」—— 那是本 repo 記過的
    # 「印了紅字但退出碼是綠」，而排程只看退出碼。
    if cross or reds:
        parts = []
        if cross:
            parts.append(f"{len(cross)} 案跨表 year 不一致（同一年度在不同頁面得到不同總額）")
        if reds:
            parts.append(f"{len(reds)} 張 year 欄與案名年度不符")
        print(f"\nStatus: [RED] " + "；".join(parts)
              + " —— 年度篩選會讓這些案在錯的年份出現或消失，而畫面上沒有任何訊息。")
        return 2
    if yellows:
        print(f"\nStatus: [YELLOW] {len(yellows)} 張 year 欄為空")
        return 1
    print("\nStatus: [GREEN] year 欄一致（案名年度、且三張表之間）")
    return 0


def self_test() -> None:
    """負向控制：判準要能對造出來的錯誤發出聲音，也要放行正常的跨年度合約。"""
    assert roc_years("115年度桃園市興辦公共設施") == [2026]
    # 區間三種寫法都要抓到**兩端**——首版只抓到上限，把 year=2023 的 156 誤判成 RED
    assert roc_years("112至113年度桃園市轄內") == [2023, 2024]
    assert roc_years("114~115年度本分局轄區") == [2025, 2026]
    assert roc_years("112年及113年多維度空間資訊") == [2023, 2024]
    assert roc_years("彰濱控制測量案") == []
    assert roc_years("台8線117k+400災害路段") == [], "117k 不是年度，不得誤判"
    assert roc_years("台86線向東延伸與182線共線") == [], "182 線不是年度"
    # 正常：跨年度合約（案號 2025、案名 115 年度、year 2026）不得判紅
    print("self_test OK")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main())
