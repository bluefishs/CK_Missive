#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: 承攬案件 case_code 橋接覆蓋率審計

2026-07-29 觸發（owner 回報 `/contract-cases/187` 無法進行財務紀錄作業）：

`case_code` 是 承攬案件 ↔ ERP 報價 ↔ PM 案件 的跨模組橋樑，只在
「邀標 → 建案 → 成案」自動流程中寫入。直接建立或歷史匯入的承攬案件沒有此值，
其詳情頁「財務紀錄」分頁就永遠是空的——**而且沒有任何告警**，
要等使用者自己撞到才知道（典型沉默缺口，見 PRODUCER_SELF_CHECK_CONTRACT）。

本 audit 只看「還在跑的案子」（執行中／待執行）：已結案的歷史匯入案件不需要財務作業，
列出來只會製造噪音（對齊 Tier 3 registry「別對刻意狀態報警」原則）。

判定：
- 執行中／待執行案件，既無 case_code、也沒有任何以 project_code 對得上的 ERP 報價
  → YELLOW（可作業但財務分頁是空的，建議補建報價或補填案號）
- 上述數量 > --threshold → RED

用法：
    python scripts/checks/contract_case_code_coverage_audit.py
    python scripts/checks/contract_case_code_coverage_audit.py --threshold 10 --ci

Version: 1.0.0 (2026-07-29)
關聯：
- docs/architecture/AUTH_I3_PROPAGATION_PATCHES.md（同輪 session，不同主題）
- frontend/src/pages/contractCase/tabs/FinanceTab.tsx（「建立報價並綁定此案」入口）
- backend/app/services/contract/case_code.py（cross_module_lookup project_code fallback）
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Windows cp950 防護（L49.8 同族）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import asyncpg
except ImportError:
    print("需要 asyncpg", file=sys.stderr)
    sys.exit(1)

DSN = os.getenv(
    # 2026-08-28：原本純硬編 `localhost:5434`，而 daily 檢核跑在**容器內** ——
    # 容器裡沒有 5434（那是 host 的對外埠）⇒ 連線 OSError，而整體仍 EXIT=0
    #（沉默失敗，實測 [5/78] 與 [55/78] 兩步都是這樣）。
    # 改為讀 DATABASE_URL、保留原值當 host 執行時的 fallback。
    # `.replace` 不可省：容器內的值是 postgresql+asyncpg://，asyncpg.connect 不接受該 scheme。
    "AUDIT_DSN", os.getenv("DATABASE_URL", "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents").replace("postgresql+asyncpg://", "postgresql://")
)

# 仍在進行、需要財務作業的狀態（已結案／歷史匯入不列入）
ACTIVE_STATUSES = ("執行中", "待執行")

SQL = """
SELECT cp.id,
       cp.project_code,
       cp.status,
       left(cp.project_name, 40) AS name
FROM contract_projects cp
WHERE cp.status = ANY($1)
  AND (cp.case_code IS NULL OR cp.case_code = '')
  AND NOT EXISTS (
        SELECT 1 FROM erp_quotations q
        WHERE q.project_code IS NOT NULL
          AND q.project_code <> ''
          AND q.project_code = cp.project_code
      )
ORDER BY cp.id
"""


async def main(threshold: int, ci: bool) -> int:
    try:
        conn = await asyncpg.connect(DSN)
    except Exception as e:  # 環境不可達時 graceful skip（避免 fitness 整串中斷）
        print(f"⚪ SKIP 無法連線資料庫: {e}")
        return 0
    try:
        rows = await conn.fetch(SQL, list(ACTIVE_STATUSES))
        total = await conn.fetchval("SELECT count(*) FROM contract_projects")
        linked = await conn.fetchval(
            "SELECT count(*) FROM contract_projects WHERE case_code IS NOT NULL AND case_code <> ''"
        )
    finally:
        await conn.close()

    print("=== 承攬案件 case_code 橋接覆蓋率 ===")
    print(f"總案件 {total} / 已有 case_code {linked} "
          f"({(linked / total * 100) if total else 0:.1f}%)")
    print(f"進行中且無財務關聯: {len(rows)}")

    for r in rows:
        print(f"  - id={r['id']} [{r['status']}] {r['project_code'] or '(無成案編號)'} {r['name']}")

    if not rows:
        print("✅ GREEN — 所有進行中案件都可進行財務紀錄作業")
        return 0

    print()
    print("修法：於該案「財務紀錄」分頁按「建立報價並綁定此案」（自動帶入成案編號），")
    print("      或編輯案件補填「建案案號 (case_code)」。")

    if len(rows) > threshold:
        print(f"🔴 RED — 超過門檻 {threshold}")
        return 1 if ci else 0
    print(f"🟡 YELLOW — {len(rows)} 筆待補（門檻 {threshold}）")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=int, default=10, help="超過此數量判 RED")
    p.add_argument("--ci", action="store_true", help="RED 時 exit 1")
    a = p.parse_args()
    sys.exit(asyncio.run(main(a.threshold, a.ci)))
