#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ADR-0033 配套 — IdP Connectivity Check

ADR-0033 後 Google + LINE 是唯一登入路徑。其中任一 IdP 服務中斷 = 全服務無法登入。
本檢查每月跑 + 部署前必跑，確保兩條 IdP 路徑都健康。

檢查項：
- Google OAuth Discovery: https://accounts.google.com/.well-known/openid-configuration
- LINE OAuth Discovery: https://access.line.me/.well-known/openid-configuration

關聯：
- docs/adr/0033-disable-password-authentication.md
- docs/runbooks/sso_emergency_rollback.md

Exit codes:
  0 — 兩 IdP 皆 OK 或非 strict
  1 — strict mode (--ci) 且至少一個 IdP 不可達
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Tuple

import urllib.request
import urllib.error
import ssl

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


GOOGLE_DISCOVERY = "https://accounts.google.com/.well-known/openid-configuration"
LINE_DISCOVERY = "https://access.line.me/.well-known/openid-configuration"


def _check(url: str, name: str, timeout: float = 5.0) -> Tuple[bool, float, str]:
    """回傳 (ok, elapsed_ms, info)。"""
    start = time.monotonic()
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "ck-missive-fitness/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            elapsed = (time.monotonic() - start) * 1000
            if resp.status == 200:
                # 簡單驗證 issuer 欄位存在（不解 JSON 避免依賴）
                body = resp.read(2048).decode("utf-8", errors="ignore")
                ok = '"issuer"' in body
                return ok, elapsed, f"HTTP 200, {len(body)} bytes (sample)"
            return False, elapsed, f"HTTP {resp.status}"
    except urllib.error.URLError as e:
        elapsed = (time.monotonic() - start) * 1000
        return False, elapsed, f"URLError: {e.reason}"
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return False, elapsed, f"{type(e).__name__}: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(description="IdP Connectivity Check")
    parser.add_argument("--ci", action="store_true", help="any failure exit 1")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    print("=== IdP Connectivity（ADR-0033 配套）===")
    print()

    fail = 0
    for url, name in [(GOOGLE_DISCOVERY, "Google"), (LINE_DISCOVERY, "LINE")]:
        ok, ms, info = _check(url, name, args.timeout)
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name:<8} {ms:6.0f}ms  {info}")
        if not ok:
            fail += 1

    print()
    if fail == 0:
        print("[PASS] 兩個 IdP 皆可達；ADR-0033 認證鏈健康")
    else:
        print(
            f"[FAIL] {fail}/2 IdP 不可達 — 用戶可能無法登入。"
            " 緊急：見 docs/runbooks/sso_emergency_rollback.md"
        )

    return 1 if (args.ci and fail > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
