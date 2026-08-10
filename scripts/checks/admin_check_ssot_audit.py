# -*- coding: utf-8 -*-
"""管理員判定 SSOT 稽核 —— 不得有第二份規則（2026-08-10）。

## 起因

員工 `洪慶忠` 的資料是 `role='admin'` 但 `is_admin=false`（13 個 active 帳號中
唯一一個不一致）。系統裡的管理員判定當時散在四處，而且規則不同：

  · `dependencies.require_admin`            → flag OR role  ✓
  · `auth/login_history.py`                 → flag OR role  ✓
  · `api/endpoints/backup.py::_is_admin`    → **只看 flag**（10 個端點）
  · `auth_service.check_admin_permission`   → 只看 flag（當時零生產呼叫者）

後果是**看得到而用不了**：前端 `usePermissions.isAdmin` 併看 role，
所以選單會顯示「備份管理」；點進去每一個動作都回 403。
這種症狀最難自行診斷 —— 使用者會以為是自己操作錯，或以為系統壞了。

## 這支問的問題

    有沒有人又寫了一份自己的管理員判定？

判準：程式碼中出現 `is_admin` / `is_superuser` 的**布林判定**，
若同一個判定式沒有一併看 `role`，就是第二份規則。
唯一允許的實作是 `app/core/dependencies.py::is_admin_user`。

## 刻意不管的

  · 賦值（`is_admin=...`）、schema 欄位宣告、dict 取值（`"is_admin"`）
  · 測試檔（測試本來就要能構造各種組合）
  · `is_admin_user` 自身的定義

用法：
    python scripts/checks/admin_check_ssot_audit.py
    python scripts/checks/admin_check_ssot_audit.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "backend" / "app"

CANONICAL = "dependencies.py"          # 唯一允許定義判定的檔案
CANONICAL_FUNC = "is_admin_user"

# **必須是屬性存取**（`user.is_admin`），不是裸識別字。
#
# 首版沒這條，30 個命中裡大半是假陽性：rls_filter 的參數宣告與 docstring、
# `RLSFilter.apply_document_rls(query, Document, user_id, is_admin)` 這種傳參、
# query_builder 收到已解析布林後的 `if is_admin:`。
# 那些地方的判定其實早就對了（`get_user_rls_flags` 2026-05-06 就加了 role fallback），
# 報出來只會讓清單不可採信 —— 而不可採信的清單沒有人會逐條看。
#
# 裸識別字代表「值是別人給的」，該追的是給值的那一端；
# 屬性存取才代表「這裡自己在從 user 物件推導身分」。
ATTR_ADMIN = re.compile(r"\b\w+\.is_admin\b(?!\s*=[^=])")
ATTR_SUPER = re.compile(r"\b\w+\.is_superuser\b(?!\s*=[^=])")
HAS_ROLE = re.compile(r"\brole\b")
SKIP_LINE = re.compile(
    r'^\s*[#*]|"""|\'\'\''
    r'|"is_(?:admin|superuser)"|\'is_(?:admin|superuser)\''
    r'|is_(?:admin|superuser)\s*=(?!=)'      # 賦值／關鍵字參數，不是判定
    r'|is_(?:admin|superuser):\s*bool'       # 欄位型別宣告
)


def scan() -> list[tuple[str, int, str, str]]:
    """回傳 (檔案, 行號, 內容, 類型)；類型為 'admin' 或 'superuser'。"""
    hits: list[tuple[str, int, str, str]] = []
    for p in sorted(APP.rglob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        if "/tests/" in rel or rel.endswith("_test.py"):
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if SKIP_LINE.search(s):
                continue
            kind = "admin" if ATTR_ADMIN.search(s) else ("superuser" if ATTR_SUPER.search(s) else "")
            if not kind:
                continue
            if p.name == CANONICAL and CANONICAL_FUNC in "\n".join(lines[max(0, i - 14):i + 2]):
                continue  # 唯一實作自身
            # 判定式**同一行或緊鄰數行**有看 role 就算合規
            if HAS_ROLE.search("\n".join(lines[max(0, i - 4):i + 3])):
                continue
            hits.append((rel, i, s[:100], kind))
    return hits


def judge(hits: list) -> int:
    return 2 if hits else 0


def self_test() -> int:
    bad = []
    cases = [
        ("有第二份規則", [("a.py", 1, "x")], 2),
        ("只有唯一實作", [], 0),
    ]
    for name, h, expect in cases:
        got = judge(h)
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {name:20s} 預期 exit={expect} 實際={got}")
        if not ok:
            bad.append(name)

    # 正則鑑別力：布林判定要抓到，賦值與字串鍵不能誤抓
    checks = [
        ("return user.is_admin or user.is_superuser", True, "屬性布林判定"),
        ("if not current_user.is_admin:", True, "端點內自行判定"),
        ("if not _is_admin(current_user):", False, "呼叫 helper"),
        ("is_admin=user_row.is_admin,", False, "賦值"),
        ('"is_admin": True,', False, "字典鍵"),
        ("is_admin: bool = False", False, "欄位宣告"),
        ("if is_admin or is_superuser:", False, "裸識別字（值由呼叫端解析）"),
        ("query, Document, user_id, is_admin", False, "傳參"),
        ("            is_superuser: 是否為超級使用者", False, "docstring 參數說明"),
    ]
    for src, want, why in checks:
        got = (bool(ATTR_ADMIN.search(src)) or bool(ATTR_SUPER.search(src))) and not bool(SKIP_LINE.search(src))
        ok = got == want
        print(f"  {'✓' if ok else '✗'} {why:20s} {'命中' if got else '不命中'}")
        if not ok:
            bad.append(why)

    if bad:
        print(f"\n✗ 判準無鑑別力：{bad}")
        return 2
    print("\n✓ 判準有鑑別力（正向 2、負向 5）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--strict", action="store_true", help="相容旗標")
    ap.add_argument("--ci", action="store_true", help="相容旗標")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("=== 管理員判定 SSOT 稽核 ===")
    if not APP.is_dir():
        print(f"✗ 找不到 {APP} —— 無法判定，不視為通過")
        return 2

    hits = scan()
    print(f"  唯一允許的實作：app/core/dependencies.py::{CANONICAL_FUNC}（flag OR role）")
    if hits:
        admin_hits = [h for h in hits if h[3] == "admin"]
        super_hits = [h for h in hits if h[3] == "superuser"]
        print(f"\n🔴 發現 {len(hits)} 處自行推導身分（admin {len(admin_hits)}／superuser {len(super_hits)}）：")
        for rel, ln, s, kind in hits[:14]:
            print(f"    · [{kind:9s}] {rel}:{ln}  {s}")
        if len(hits) > 14:
            print(f"    …另 {len(hits) - 14} 處")
        print(f"  → 改為 `from app.core.dependencies import {CANONICAL_FUNC}`"
              f"（superuser 用 is_superuser_user）後委派。")
        print("     只看 flag 會擋掉 role='admin' 但 is_admin=false 的帳號 ——")
        print("     而前端選單併看 role，於是使用者看得到卻用不了。")
    else:
        print("  ✓ 沒有第二份規則")

    code = judge(hits)
    print()
    print(f"Status: [{'RED' if code >= 2 else 'GREEN'}]")
    return code


if __name__ == "__main__":
    sys.exit(main())
