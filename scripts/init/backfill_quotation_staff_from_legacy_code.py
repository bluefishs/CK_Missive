#!/usr/bin/env python3
"""從舊報價編號的代碼補回承辦同仁（owner 2026-08-29 指認 A/B/C/D）

## 為什麼先前沒補

2026-08-20 那次是從**彙整表的工作表名稱**取承辦（原始／老闆／慶忠／元宏／其他）。
115 檔只有一個「工作表1」⇒ 當時的結論是「115 檔沒有承辦人資訊，那是資料本身
沒有」。**那個結論錯了** —— 資訊在 `legacy_quotation_no` 的代碼裡：

    B115-A001-0A   →  A
    B115-B003-0    →  B
    B114-C012-1    →  C

第一段的 `B115` 是年度前綴（那個 B 不是人），**人的代碼是第二段開頭那個字母**。

owner 2026-08-29：「114、115代碼解析 已多次提出 A坤樹 B慶忠 C元宏 D廷睿」。

## 解碼規則先在已知答案上驗過（不是直接拿去補未知）

    代碼   現有承辦        筆數
    A      張坤樹           5      ← 乾淨
    B      洪慶忠          36
    B      曾廷睿           2      ← ⚠️ 衝突，不覆蓋
    C      邱元宏          55      ← 乾淨
    D      曾廷睿           5      ← 乾淨
    Y      洪慶忠           1      ← 不在四碼內，跳過

⇒ A／C／D 三碼零反例；B 有 2 筆反例。**已有指派的一律不動** ——
那 2 筆可能是後來人工改過的，人改過的比代碼推出來的更可信。

## 這支做什麼、不做什麼

**做**：只對「全庫查不到任何承辦」的案號，依代碼寫入 `project_user_assignments`
（`case_code` + `user_id`，role 沿用既有的「專案PM」）。

**不做**：不覆蓋既有指派；不猜測代碼表以外的字母（Y 之類一律列出不寫）；
不對沒有 `legacy_quotation_no` 的報價單做任何事。

預設 dry-run，要真的寫入需 `--apply`。
"""
import argparse
import asyncio
import os
import re
import sys
from collections import defaultdict

# 容器內 app 套件在 /app；本機執行時才需要往上找 backend/
for _p in ("/app", os.path.join(os.path.dirname(__file__), "..", "..", "backend")):
    if os.path.isdir(os.path.join(_p, "app")):
        sys.path.insert(0, _p)
        break

from sqlalchemy import text  # noqa: E402

from app.db.database import AsyncSessionLocal  # noqa: E402

#: owner 2026-08-29 指認。**只放人講過的**，不自行推測
#: （同 `quotation_legacy_import._SHEET_ALIASES` 的原則）。
CODE_TO_NAME = {
    "A": "張坤樹",
    "B": "洪慶忠",
    "C": "邱元宏",
    "D": "曾廷睿",
    # owner 2026-08-29 補充：「Y也指定慶忠」。
    # 現有唯一一筆 Y 的承辦**本來就是洪慶忠** —— 指認與既有資料一致，不是新規則。
    "Y": "洪慶忠",
}

#: 舊編號格式 `B115-A001-0A`：年度前綴 + 「-」 + **人的代碼** + 流水
_CODE_RE = re.compile(r"^[A-Z][0-9]{3}-([A-Z])")

ROLE = "專案PM"  # 與 08-20 那次一致：來源只說了「這是誰的案子」，不多猜職責層級


async def main(apply: bool) -> int:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text("""
            SELECT q.case_code, q.legacy_quotation_no
              FROM erp_quotations q
             WHERE q.legacy_quotation_no IS NOT NULL
               AND q.case_code IS NOT NULL AND q.case_code <> ''
               AND NOT EXISTS (
                   SELECT 1 FROM project_user_assignments pa
                     LEFT JOIN contract_projects cp ON cp.case_code = q.case_code
                    WHERE pa.project_id = cp.id OR pa.case_code = q.case_code)
        """))).all()

        users = {n: i for i, n in (await db.execute(text(
            "SELECT id, COALESCE(full_name, username) FROM users"
        ))).all()}

        # 同一個案號可能有多張報價單 —— 指派是掛在案號上，去重
        by_case: dict[str, set[str]] = defaultdict(set)
        unknown: dict[str, int] = defaultdict(int)
        no_code = 0
        for case_code, legacy in rows:
            m = _CODE_RE.match(legacy or "")
            if not m:
                no_code += 1
                continue
            code = m.group(1)
            if code not in CODE_TO_NAME:
                unknown[code] += 1
                continue
            by_case[case_code].add(code)

        plan: list[tuple[str, str, int]] = []
        conflict: list[tuple[str, set[str]]] = []
        missing_user: set[str] = set()
        for case_code, codes in sorted(by_case.items()):
            if len(codes) > 1:
                # 同一案號的多張報價單指向不同的人 —— 不猜，交給人看
                conflict.append((case_code, codes))
                continue
            name = CODE_TO_NAME[next(iter(codes))]
            uid = users.get(name)
            if uid is None:
                missing_user.add(name)
                continue
            plan.append((case_code, name, uid))

        per_person: dict[str, int] = defaultdict(int)
        for _, name, _ in plan:
            per_person[name] += 1

        print(f"缺承辦且有舊編號的報價單：{len(rows)} 張")
        print(f"  解得出代碼的案號：{len(by_case)}")
        print(f"  舊編號不合格式（無代碼）：{no_code} 張")
        if unknown:
            print(f"  ⚠️ 代碼不在對照表內（不寫入）：{dict(unknown)}")
        if conflict:
            print(f"  ⚠️ 同案號多個代碼（不寫入）：{len(conflict)} 件 {conflict[:5]}")
        if missing_user:
            print(f"  ⚠️ 對照表有名字但系統查無此人（不寫入）：{sorted(missing_user)}")
        print(f"\n可寫入：{len(plan)} 件案號  {dict(per_person)}")

        if not apply:
            print("\n[dry-run] 未寫入。確認無誤後加 --apply")
            return 0

        for case_code, _name, uid in plan:
            await db.execute(text("""
                INSERT INTO project_user_assignments
                       (case_code, user_id, role, is_primary, status)
                VALUES (:cc, :uid, :role, true, 'active')
            """), {"cc": case_code, "uid": uid, "role": ROLE})
        await db.commit()
        print(f"\n已寫入 {len(plan)} 筆指派。")
        return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的寫入（預設 dry-run）")
    raise SystemExit(asyncio.run(main(ap.parse_args().apply)))
