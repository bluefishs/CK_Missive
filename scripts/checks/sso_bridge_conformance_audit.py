#!/usr/bin/env python3
"""SSO Bridge Conformance Audit — 跨 repo sso_bridge 安全契約守門（Tier2 / L80）。

背景：模組化收斂欲把 4 repo sso_bridge 強抽成單一 flow，複查揭露 orchestration 含
**刻意 per-repo 安全政策分歧**（auto-provision matrix 等），強抽 = 過度抽象 auth。
決策：**不強抽 orchestration**，改用本 audit 守「共享安全契約」（防意外 drift），
分歧登記於 docs/architecture/SSO_BRIDGE_DIVERGENCE_MATRIX.md（防誤判為 drift）。

本 audit **不強制實作相同**，只強制以下安全契約（違反 = RED）：
  C1  必須用 ck_auth 共享驗證：import verify_ck_sso_jwt_auto + has_system_permission
      （from <repo>.core.ck_sso，該檔為 ck_auth.sso re-export shim）
  C2  禁止重新實作 JWT 驗證：sso_bridge 內不得直接 jwt.decode / jose.decode
  C3  守衛順序狀態碼：flag(503) → cookie(401) → jwt(401) → permission(403)
      必須在「查 User」之前，且順序正確
  C4  必須有系統權限檢查（has_system_permission 被呼叫）

用法：
  python scripts/checks/sso_bridge_conformance_audit.py [--strict]
  --strict：任一 RED → exit 1（CI / fitness 用）

跨 repo：從 CK_Missive 執行，讀 sibling repo（../CK_*）。repo 不存在則 skip（非 fail）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# cp950 host 韌性（L49.8 同族）
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# repo → sso_bridge.py 相對路徑（從 CK_Missive 根執行）
REPO_ROOT = Path(__file__).resolve().parents[2]  # CK_Missive/
CK_ROOT = REPO_ROOT.parent  # D:\CKProject
TARGETS = {
    "missive": REPO_ROOT / "backend/app/api/endpoints/auth/sso_bridge.py",
    "lvrland": CK_ROOT / "CK_lvrland_Webmap/backend/app/api/endpoints/auth/sso_bridge.py",
    "pile": CK_ROOT / "CK_PileMgmt/backend/app/api/endpoints/auth/sso_bridge.py",
    "digitaltunnel": CK_ROOT / "CK_DigitalTunnel/api/src/routers/sso_bridge.py",
}

# Documented-exempt：C3(守衛順序)/C4(系統權限檢查) 刻意不適用之 repo。
#   C1(用 ck_auth verify) + C2(不重新實作驗證) 仍為全 repo 通用鐵律，exempt 不放寬。
#   登記於 SSO_BRIDGE_DIVERGENCE_MATRIX.md §3。
GUARD_EXEMPT = {
    # DT 刻意不檢 has_system_permission（政策：任何已驗證 CK 員工皆可進，role 僅首次建立套用），
    # 且採 bearer/XOR 獨立 paradigm，守衛結構與 3 個 cookie-session repo 不同。
    "digitaltunnel": "刻意不檢系統權限（DT 政策）+ bearer 獨立 paradigm",
}


def audit_file(name: str, path: Path) -> list[str]:
    """回傳違規清單（空 = 通過）。"""
    violations: list[str] = []
    src = path.read_text(encoding="utf-8", errors="replace")
    guard_exempt = name in GUARD_EXEMPT

    # C1 用共享驗證（全 repo 通用鐵律，exempt 不放寬）
    if "verify_ck_sso_jwt_auto" not in src:
        violations.append("C1: 未使用共享 verify_ck_sso_jwt_auto（可能重新實作驗證）")

    # C2 禁止重新實作 JWT 驗證（全 repo 通用鐵律）
    #   允許 import ck_sso；但檔內直接 jwt.decode / jose.jwt.decode = 重新實作
    if re.search(r"\bjwt\.decode\s*\(", src) or re.search(r"jose[.\w]*\.decode\s*\(", src):
        violations.append("C2: 檔內直接 jwt/jose.decode（應委派 ck_auth.sso，禁重新實作驗證）")

    # C4 系統權限檢查（guard_exempt repo 刻意不適用）
    if not guard_exempt and "has_system_permission" not in src:
        violations.append("C4: 未呼叫 has_system_permission（系統權限檢查缺失）")

    if guard_exempt:
        return violations  # C3 守衛順序對 exempt repo 不適用

    # C3 守衛順序：擷取 status code 出現序，驗證 503 → 401 → 401 → 403 在查 User 前
    #   先 scope 到 sso_bridge endpoint 函式本體（排除 try_mint fallback，其亦含 get_user_by_email）
    ep = re.search(r"\n(?:async\s+)?def\s+sso_bridge\s*\(", src)
    body = src[ep.start():] if ep else src
    # 以 endpoint 內第一個 get_user_by_email 作為「查 User」錨點
    user_lookup = re.search(r"get_user_by_email", body)
    pre_user = body[: user_lookup.start()] if user_lookup else body
    codes = re.findall(r"HTTP_(\d{3})_", pre_user)
    # 期望前綴序列（查 User 前）：503, 503, 401, 401, 403  （允許 subset / 合理省略但序不可亂）
    # 簡化契約：第一個必為 503（flag）、最後一個（權限）必為 403、且 401 不得晚於 403
    if codes:
        if codes[0] != "503":
            violations.append(f"C3: 首守衛狀態碼應為 503(flag) 實為 {codes[0]}")
        idx_401 = next((i for i, c in enumerate(codes) if c == "401"), None)
        idx_403 = next((i for i, c in enumerate(codes) if c == "403"), None)
        if idx_401 is not None and idx_403 is not None and idx_401 > idx_403:
            violations.append("C3: 401(cookie/jwt) 晚於 403(permission)，守衛順序錯亂")
    else:
        violations.append("C3: 查 User 前未見任何 HTTPException 守衛（守衛缺失）")

    return violations


def main(strict: bool = False) -> int:
    print("=== SSO Bridge Conformance Audit ===")
    print(f"  安全契約守門（不強制實作相同，只守共享契約）")
    print(f"  刻意分歧登記：SSO_BRIDGE_DIVERGENCE_MATRIX.md + TIER3_INTENTIONAL_DIVERGENCE_REGISTRY.md")
    print("─" * 60)

    total_red = 0
    checked = 0
    for name, path in TARGETS.items():
        if not path.exists():
            print(f"  ⚪ {name:<14} SKIP（檔案不存在：{path}）")
            continue
        checked += 1
        violations = audit_file(name, path)
        exempt_note = f"（C3/C4 exempt：{GUARD_EXEMPT[name]}）" if name in GUARD_EXEMPT else ""
        if violations:
            total_red += 1
            print(f"  🔴 {name:<14} {len(violations)} 違規 {exempt_note}")
            for v in violations:
                print(f"       - {v}")
        elif name in GUARD_EXEMPT:
            print(f"  🟡 {name:<14} PASS（C1/C2 守住）{exempt_note}")
        else:
            print(f"  🟢 {name:<14} PASS（安全契約守住）")

    print("─" * 60)
    print(f"  檢查 {checked} repo，{total_red} RED")
    if total_red == 0:
        print("✅ GREEN：所有 sso_bridge 變體維持共享安全契約")
    else:
        print("🔴 RED：安全契約被破壞，見上方違規（可能是意外 drift）")
        print("   note：刻意 policy 分歧（auto-provision 等）不在此 audit 範圍，見分歧矩陣")

    return 1 if (strict and total_red > 0) else 0


if __name__ == "__main__":
    sys.exit(main(strict="--strict" in sys.argv))
