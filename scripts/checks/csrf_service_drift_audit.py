#!/usr/bin/env python3
"""CSRF Service Drift Audit — pile ↔ lvrland csrf_service 單一源守門（Tier2 / L80）。

背景：pile/lvrland `csrf_service.py`（189 行）為真乾淨重複（HH-1），**僅差 1 行**——
redis client import 路徑（pile: unified_redis_client 直接 / lvrland: redis_client 相容包裝，
兩者 re-export 同一 UnifiedRedisClient，介面完全相同）。

為何用 drift audit 而非 import-式共享 wheel：
  把 csrf 併入 ck_auth wheel 需 bump 版本 → fitness step 70 逐 repo 比對版本 →
  只 re-vendor pile+lvrland 會讓 Missive/DT 版本偏移標紅 → 逼迫 re-vendor+rebuild 含
  **主產品 Missive**（blast radius）。csrf 兩檔僅差 1 cosmetic 行、各 1 caller、drift 風險
  低，故採零風險 drift audit 保證單一源，避免主產品 churn（比例原則，對齊 sso_bridge
  conformance 處置）。真 import-式收斂（獨立 ck-csrf 套件）留 focused session。

檢查：pile 與 lvrland csrf_service.py 正規化後（統一 redis import 路徑差異）必須逐行相同。
  逾此 = 意外 drift → RED。

用法：python scripts/checks/csrf_service_drift_audit.py [--strict]
跨 repo：從 CK_Missive 讀 sibling repo；任一不存在則 skip（非 fail）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]
CK_ROOT = REPO_ROOT.parent
PILE = CK_ROOT / "CK_PileMgmt/backend/app/core/csrf_service.py"
LVRLAND = CK_ROOT / "CK_lvrland_Webmap/backend/app/core/csrf_service.py"

# 已知刻意差異：redis client import 路徑（兩者 resolve 同一 UnifiedRedisClient）。
# 正規化：把兩種 import 路徑統一，其餘必須逐行相同。
_REDIS_IMPORT_RE = re.compile(
    r"from\s+backend\.app\.core\.(unified_redis_client|redis_client)\s+import\s+get_redis_client"
)
_NORMALIZED_REDIS = "from backend.app.core.<REDIS> import get_redis_client"


def _normalize(src: str) -> list[str]:
    lines = []
    for ln in src.splitlines():
        ln = _REDIS_IMPORT_RE.sub(_NORMALIZED_REDIS, ln)
        lines.append(ln.rstrip())
    return lines


def main(strict: bool = False) -> int:
    print("=== CSRF Service Drift Audit (pile ↔ lvrland 單一源 / L80) ===")
    print("  已知刻意差異：redis import 路徑（Tier3 registry §1.7）；其餘須逐行相同")
    print("─" * 60)

    if not PILE.exists() or not LVRLAND.exists():
        print(f"  ⚪ SKIP（sibling 不在本 checkout）pile={PILE.exists()} lvrland={LVRLAND.exists()}")
        return 0

    pile_n = _normalize(PILE.read_text(encoding="utf-8", errors="replace"))
    lvr_n = _normalize(LVRLAND.read_text(encoding="utf-8", errors="replace"))

    if pile_n == lvr_n:
        print(f"  🟢 PASS：pile/lvrland csrf_service 正規化後逐行相同（{len(pile_n)} 行，單一源守住）")
        return 0

    # 找出差異行
    diffs = []
    for i, (a, b) in enumerate(zip(pile_n, lvr_n), 1):
        if a != b:
            diffs.append((i, a, b))
    len_diff = abs(len(pile_n) - len(lvr_n))
    print(f"  🔴 DRIFT：{len(diffs)} 行不同" + (f" + 行數差 {len_diff}" if len_diff else ""))
    for i, a, b in diffs[:10]:
        print(f"     L{i}:")
        print(f"       pile   : {a[:80]}")
        print(f"       lvrland: {b[:80]}")
    print("  → 非已知 redis import 差異 = 意外 drift，應收斂回單一源")
    print("─" * 60)
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main(strict="--strict" in sys.argv))
