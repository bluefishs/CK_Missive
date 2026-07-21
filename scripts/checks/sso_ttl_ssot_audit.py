#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSO session TTL 跨 repo SSOT 稽核（I10 / L80，2026-07-21）

「一次 SSO session 能活多久」散在三處（三 repo/層），無單一 SSOT：
  1. IdP  `ck_employee` cookie TTL   — CK_Website/functions/auth/callback.ts（signJWT + Max-Age）
  2. 消費端 SSO session TTL          — CK_Missive SSO_ACCESS_TOKEN_EXPIRE_MINUTES（config.py）
  3. 前端 idle timeout（活動制）      — frontend/src/hooks/utility/useIdleTimeout.ts

不變式 I10/I11：**IdP cookie TTL 應 >= 消費端 SSO session TTL**，否則消費端 session 過期時
IdP cookie 已先失效 → refresh 的 SSO 回退（P1 無痛續命）無憑證可用 → 使用者被迫重登。
idle timeout 為獨立關注點（活動制，只要有互動即續），不納入相等比較，僅列印對照。

用法：python scripts/checks/sso_ttl_ssot_audit.py [--strict]
  --strict：drift 時 exit 1（供 fitness / pre-commit）。

跨 repo：若 CK_Website 不在 ../CK_Website 則該項標 SKIP（不失敗，僅少一項對照）。
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # L49.8 family：Windows cp950 韌性
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]  # CK_Missive/
CK_WEBSITE = ROOT.parent / "CK_Website"


def _grep_int(path: Path, pattern: str):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== SSO session TTL 跨 repo SSOT 稽核 (I10/L80) ===")

    # 2. 消費端 Missive SSO session TTL（分鐘 → 秒）
    missive_min = _grep_int(ROOT / "backend/app/core/config.py",
                            r"SSO_ACCESS_TOKEN_EXPIRE_MINUTES\s*:\s*int\s*=\s*(\d+)")
    missive_sec = missive_min * 60 if missive_min is not None else None

    # 1. IdP ck_employee cookie TTL（秒）
    idp_sec = None
    idp_status = "SKIP（CK_Website 不在 ../CK_Website）"
    cb = CK_WEBSITE / "functions/auth/callback.ts"
    if cb.exists():
        idp_sec = _grep_int(cb, r"ck_employee=\$\{jwtHS\}[^`]*Max-Age=(\d+)")
        idp_status = f"{idp_sec}s" if idp_sec else "讀取失敗"

    def fmt(s):
        return f"{s}s ({s/3600:.1f}h)" if isinstance(s, int) else "N/A"

    print(f"  [1] IdP ck_employee cookie TTL : {idp_status if idp_sec is None else fmt(idp_sec)}")
    print(f"  [2] Missive SSO session TTL    : {fmt(missive_sec)}  (SSO_ACCESS_TOKEN_EXPIRE_MINUTES={missive_min})")
    print(f"  [3] 前端 idle timeout          : 活動制（有互動即續，非固定壽命，獨立關注點不納入比較）")

    issues = []
    if idp_sec is not None and missive_sec is not None:
        if idp_sec < missive_sec:
            issues.append(
                f"IdP cookie TTL {fmt(idp_sec)} < 消費端 SSO session {fmt(missive_sec)} "
                f"→ session 過期時 IdP cookie 已先失效，P1 無痛續命失憑證（違 I10）。"
                f"建議：CK_Website callback.ts 的 signJWT/Max-Age 對齊為 {missive_sec}s。"
            )
    if idp_sec is None:
        print("  ℹ️ 未讀到 IdP cookie TTL，跨 repo 對照略過（僅檢查消費端存在）。")
        if missive_sec is None:
            issues.append("Missive SSO_ACCESS_TOKEN_EXPIRE_MINUTES 讀取失敗。")

    if issues:
        print("\n🟡 DRIFT:")
        for i in issues:
            print(f"  - {i}")
        print("\nOVERALL = YELLOW")
        return 1 if strict else 0
    print("\nOVERALL = GREEN（三處 TTL 對齊 / 無跨 repo drift）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
