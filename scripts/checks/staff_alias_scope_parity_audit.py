#!/usr/bin/env python3
"""承辦身分合併展開的一致性稽核 —— owner 2026-09-09 從 `/erp/vendor-accounts` 回報。

問的問題：**同一個人的兩個帳號，問「他的案有哪些」要得到同一個答案。**

事故：owner 以王駿穠登入、篩選「李昭德（3）」，畫面顯示「共 0 家、經費 0」。
實查兩個數字**各自都對，只是來自兩份定義**：

    id=11 staff_李昭德   canonical_user_id=19  已停用  ← CK2025_01_03_001（380 萬）掛在這裡
    id=19 luke19630612  canonical=None       在用    ← 下拉顯示的就是這個 id

  · 下拉（`assignable_staff`）**有**展開 alias ⇒ 算出 3 個案，括號寫 (3)
  · 列表（`case_codes_of_user`）**沒有**展開 ⇒ 只拿到 2 個，選 2026 後一個不剩

**同一個檔案裡兩支函式對「這個人是誰」用了兩份定義**，而且都不會報錯 ——
畫面只說「沒有資料」，讀起來像那位承辦今年沒案子。
這是 ADR-0025 身分合併家族的又一處：合併寫進去了，消費端沒有跟著展開。

判準（兩段）：
  ① **靜態**：`case_codes_of_user` 的 SQL 必須用上 `_ALIAS_GROUP`。
     拿掉展開就是這個事故本身 ⇒ 直接讀原始碼判，這是唯一擋得住復發的一條。
  ② **動態**：確認判準還有鑑別力 —— 至少有一個 alias 帳號真的掛著指派，
     且展開後的結果嚴格大於單獨查。沒有這種樣本時①是在零樣本上成立的。

⚠️ 沒有 alias 帳號時本檢核**不判綠燈也不判紅**，回報「無可檢對象」——
零樣本的綠燈是本 repo 記過的假綠形狀。

退出碼：0 = 一致；2 = 有不一致；1 = 無法連線／無可檢對象。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

try:
    import asyncpg
except ImportError as e:  # pragma: no cover
    print("missing dep: %s" % e, file=sys.stderr)
    sys.exit(1)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DSN = os.getenv("DATABASE_URL", "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents")
DSN = DSN.replace("postgresql+asyncpg://", "postgresql://")

#: 與 `app/repositories/erp/case_staff.py` 的 `_ALIAS_GROUP` 同一份語意。
#:
#: ⚠️ **首版在這裡寫了一句錯話並差點交出去**（2026-09-09 自我更正）：
#: 原註解寫「如果應用端把展開拿掉，這裡算出來的答案就會分家而報紅」——**不會**。
#: 本檢核的兩邊**都用下面這份自己的 SQL**，永遠一致 ⇒ 永遠綠，
#: 那正是本 repo 記過最多次的假綠形狀（判準量的是鄰近的東西，不是被驗的性質）。
#:
#: ⇒ 「應用端有沒有展開」由 §靜態那一段直接讀原始碼判（`_uses_alias_group`）。
#: 本段動態查詢的職責只剩一個：**確認這個判準還有鑑別力** ——
#: 也就是「真的有 alias 帳號掛著指派」，否則靜態綠燈是在零樣本上成立的。
ALIAS_GROUP = """
    SELECT u.id FROM users u
     WHERE u.id = COALESCE((SELECT canonical_user_id FROM users WHERE id = $1), $1)
        OR u.canonical_user_id = COALESCE((SELECT canonical_user_id FROM users WHERE id = $1), $1)
"""

CODES_OF = """
    SELECT DISTINCT pa.case_code
      FROM project_user_assignments pa
     WHERE pa.user_id IN (%s) AND pa.case_code IS NOT NULL
       AND COALESCE(pa.status, 'active') <> 'inactive'
    UNION
    SELECT DISTINCT cp.case_code
      FROM project_user_assignments pa2
      JOIN contract_projects cp ON cp.id = pa2.project_id
     WHERE pa2.user_id IN (%s) AND cp.case_code IS NOT NULL
       AND COALESCE(pa2.status, 'active') <> 'inactive'
""" % (ALIAS_GROUP, ALIAS_GROUP)

SINGLE_ID_ONLY = """
    SELECT DISTINCT pa.case_code
      FROM project_user_assignments pa
     WHERE pa.user_id = $1 AND pa.case_code IS NOT NULL
       AND COALESCE(pa.status, 'active') <> 'inactive'
    UNION
    SELECT DISTINCT cp.case_code
      FROM project_user_assignments pa2
      JOIN contract_projects cp ON cp.id = pa2.project_id
     WHERE pa2.user_id = $1 AND cp.case_code IS NOT NULL
       AND COALESCE(pa2.status, 'active') <> 'inactive'
"""


def _uses_alias_group() -> tuple[bool, str]:
    """靜態：`case_codes_of_user` 有沒有真的用 alias 展開。

    這是本檢核**唯一擋得住復發**的一條 —— 動態查詢驗不到應用程式碼。
    """
    p = os.path.join(ROOT, "backend", "app", "repositories", "erp", "case_staff.py")
    if not os.path.isfile(p):
        return False, "找不到 %s" % p
    src = open(p, encoding="utf-8").read()
    if "_ALIAS_GROUP" not in src:
        return False, "case_staff.py 裡沒有 _ALIAS_GROUP —— 展開被移除了"
    i = src.find("async def case_codes_of_user")
    if i < 0:
        return False, "找不到 case_codes_of_user"
    body = src[i : i + 2000]
    # ⚠️ 2026-09-09 自我更正（同日第二次）：首版判「body 裡有沒有出現 _ALIAS_GROUP」，
    # 而**這支函式的 docstring 自己就寫著「見 `_ALIAS_GROUP` 的說明」** ⇒ 拿掉真正的
    # 展開之後判準照樣綠。實測正向控制：注入回歸 → rc 仍是 0。
    # 判準的掃描範圍不得包含描述它的文字（本 repo 已記過多次，這是又一次）。
    # ⇒ 改判**實際被代入 SQL 的形狀**：`IN ({_ALIAS_GROUP})`，註解不會這樣寫。
    needle = "IN ({_ALIAS_GROUP})"
    n = body.count(needle)
    if n < 2:
        return False, (
            "case_codes_of_user 的 SQL 只有 %d 處用 IN ({_ALIAS_GROUP})（應為 2："
            "綁 case_code 與綁 project_id 兩條）—— 它只認傳進來的那一個 id" % n
        )
    return True, "case_codes_of_user 兩條綁法都展開了 alias 群"


async def run() -> int:
    try:
        conn = await asyncpg.connect(DSN)
    except Exception as e:
        print("無法連線資料庫：%s" % e)
        return 1

    try:
        groups = await conn.fetch(
            "SELECT DISTINCT COALESCE(canonical_user_id, id) AS canon FROM users "
            "WHERE canonical_user_id IS NOT NULL"
        )
        print("=" * 68)
        print("承辦身分合併展開的一致性稽核（weekly）")
        print("=" * 68)
        ok_static, msg = _uses_alias_group()
        print("① 靜態：%s %s" % ("✅" if ok_static else "⛔", msg))
        if not groups:
            print("無可檢對象：這個資料庫沒有任何 alias 帳號（canonical_user_id 全為 NULL）。")
            print("⚠️ 這不是綠燈 —— 零樣本無法證明展開是對的。")
            return 1

        bad = []
        discriminating = False
        for g in groups:
            canon = g["canon"]
            ids = [r["id"] for r in await conn.fetch(ALIAS_GROUP, canon)]
            expected = {r["case_code"] for r in await conn.fetch(CODES_OF, canon)}
            names = await conn.fetch(
                "SELECT id, username, is_active FROM users WHERE id = ANY($1::int[])", ids
            )
            print()
            print("身分群 canonical=%s（%d 個帳號）" % (canon, len(ids)))
            for n in names:
                solo = {r["case_code"] for r in await conn.fetch(SINGLE_ID_ONLY, n["id"])}
                got = {r["case_code"] for r in await conn.fetch(CODES_OF, n["id"])}
                mark = "OK" if got == expected else "不一致"
                print("   id=%-4s %-18s active=%-5s 單獨=%d 展開後=%d  %s"
                      % (n["id"], n["username"], n["is_active"], len(solo), len(got), mark))
                if got != expected:
                    bad.append((n["id"], sorted(expected - got), sorted(got - expected)))
                # ② 展開後必須涵蓋單獨查得到的
                if not solo <= got:
                    bad.append((n["id"], sorted(solo - got), []))
                if len(got) > len(solo):
                    # 這個帳號單獨查會漏案 ⇒ 展開確實在做事 ⇒ 判準有鑑別力
                    discriminating = True

        print()
        print("② 動態鑑別力：%s" % (
            "✅ 有 alias 帳號單獨查會漏案，展開確實在做事"
            if discriminating else
            "⚠️ 沒有任何帳號因展開而多拿到案 —— ① 的綠燈目前是在零樣本上成立"))
        if not ok_static:
            print()
            print("⛔ 應用端沒有展開 alias 群 —— 這正是 09-09「顯示 (3) 卻 0 家」的成因。")
            return 2
        if bad:
            print("⛔ 身分群內問到不同答案：%d 處" % len(bad))
            for uid, missing, extra in bad:
                print("   id=%s 少了 %s 多了 %s" % (uid, missing, extra))
            print()
            print("⇒ 修法：`app/repositories/erp/case_staff.py` 的 `_ALIAS_GROUP` ——")
            print("   問「這個人的案有哪些」必須先把 alias 群展開，不能只認傳進來的那個 id。")
            rc = 2
        else:
            print("✅ 每個身分群內，alias 與 canonical 問到的案是同一組")
            rc = 0

        report = {"groups": len(groups), "mismatches": len(bad)}
        outdir = os.path.join(ROOT, "wiki", "memory", "integration-health")
        if os.path.isdir(outdir):
            with open(os.path.join(outdir, "staff_alias_scope_parity.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        return rc
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
