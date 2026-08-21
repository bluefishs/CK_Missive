#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""無認證端點稽核 —— 用 FastAPI runtime dependency 樹，不是 grep。

## 為什麼有這支

owner 2026-08-21：「不應有資訊外漏問題，請加強與規劃作業」。

公網實測（未帶任何憑證）曾取得業務資料：

    /api/documents-enhanced/statistics → 200
    {"total":2017,"current_year_count":496,
     "delivery_method_stats":{"electronic":459,"paper":144}}

根因不是某個端點忘了加，是 `TUNNEL_GUARD_ENABLED=false`
（2026-08-03 的既有決策 —— 它是 all-or-nothing，開了會擋掉整個 SPA）⇒
**所有沒有自帶認證的端點一律對公網開放**。

## 為什麼不沿用既有的 security_scan 規則

`security_issues` 裡「端點缺少認證裝飾器」那條 grep 規則產生了
**122 個被人工標為誤判的 high** —— 誤判是真問題（23 個 open）的 6 倍。
它認不出 `Depends(require_auth())` 這類寫法，於是報一堆假的，
真的反而淹沒在噪音裡。

FastAPI 的 dependency 樹是**權威來源**：端點實際會不會跑認證，
它說了算。同一份資產已用在 `admin_endpoint_ui_consumers.py`。

## 判準

* 在**應用實際執行的容器內**載入 app（host 沒有相依，
  且「檢核要在它保護的東西實際執行的環境裡驗」是本專案已立的判準）；
* 走訪每條 `/api/*` route 的 dependency 樹，找認證相依；
* 不在白名單（登入／webhook／健康檢查／API 文件）的無認證端點即為缺口；
* baseline 內的已知項不判紅（逐步清），**新增的一律 RED**。

退出碼：0 GREEN／2 RED（新增無認證端點，或探測不可用而無法下結論）。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTAINER = "ck_missive_backend"
BASELINE = Path(__file__).with_name("public_endpoint_auth_baseline.json")

#: 刻意公開 —— 每一條都要能回答「為什麼它不需要登入」。
INTENDED = [
    (r"^/api/auth/", "登入流程本身（未登入才會打）"),
    (r"^/api/health", "健康檢查（cloudflared/監控要用）"),
    (r"^/api/line/", "LINE webhook（走 X-Line-Signature 驗簽）"),
    (r"^/api/telegram/", "Telegram webhook（走 token 路徑）"),
    (r"^/api/discord/", "Discord interactions（走簽章驗證）"),
    (r"^/api/hermes/", "Hermes ACP（走 X-Service-Token）"),
    (r"^/api/public/", "刻意公開的唯讀端點"),
    (r"^/api/(docs|redoc|openapi)", "API 文件（另有來源守衛擋公網，見 main.py）"),
    (r"^/api/security/csp-report", "瀏覽器自動回報 CSP 違規，無法帶憑證"),
    (r"^/api/secure-site-management/csrf-token", "CSRF 自癒需要（L68），必須未登入可取"),
    (r"^/api/debug/", "開發除錯端點（生產實測 404/403）"),
]

_PROBE = r'''
import json, sys
sys.path.insert(0, "/app")
from main import app
AUTH = ("require_auth", "require_admin", "require_superuser", "get_current_user",
        "optional_auth", "is_admin_user", "is_superuser_user", "verify_service_token",
        "get_admin", "service_auth", "require_service")
def deps(route):
    out, d = set(), getattr(route, "dependant", None)
    if not d:
        return out
    stack = [d]
    while stack:
        cur = stack.pop()
        c = getattr(cur, "call", None)
        if c is not None:
            out.add(getattr(c, "__qualname__", getattr(c, "__name__", str(c))))
        stack.extend(getattr(cur, "dependencies", []) or [])
    return out
rows = []
for r in app.routes:
    p = getattr(r, "path", None)
    if not p or not p.startswith("/api"):
        continue
    names = deps(r)
    rows.append({"path": p, "authed": any(any(a in n for a in AUTH) for n in names)})
print("@@JSON@@" + json.dumps(rows, ensure_ascii=False))
'''


def probe() -> list[dict] | None:
    f = PROJECT_ROOT / "backend" / "logs" / "_auth_probe.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(_PROBE, encoding="utf-8")
    try:
        r = subprocess.run(
            ["docker", "exec", "-w", "/app", CONTAINER, "python", "/app/logs/_auth_probe.py"],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
    except FileNotFoundError:
        print("[RED] 找不到 docker CLI —— 無法取得 runtime 事實，不下結論", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[RED] 容器探測逾時", file=sys.stderr)
        return None
    finally:
        f.unlink(missing_ok=True)
    for line in (r.stdout or "").splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@"):])
    print(f"[RED] 探測沒有回傳結果：{(r.stderr or '')[-300:]}", file=sys.stderr)
    return None


def why_intended(path: str) -> str | None:
    for pat, reason in INTENDED:
        if re.search(pat, path):
            return reason
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="無認證端點稽核（runtime dependency 樹）")
    ap.add_argument("--ci", action="store_true", help="新增缺口即 exit 2")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--update-baseline", action="store_true",
                    help="把目前的缺口寫成 baseline（只在**確認每一條都已處理或已決定接受**時用）")
    args = ap.parse_args()

    rows = probe()
    if rows is None:
        # 探測不到就是不知道 —— 不得靜靜回綠（本專案已立此判準）
        return 2

    no_auth = [r["path"] for r in rows if not r["authed"]]
    gaps = [p for p in no_auth if not why_intended(p)]

    base = []
    if BASELINE.exists():
        try:
            base = json.loads(BASELINE.read_text(encoding="utf-8")).get("known_gaps", [])
        except Exception:
            base = []
    new_gaps = sorted(set(gaps) - set(base))
    fixed = sorted(set(base) - set(gaps))

    if args.update_baseline:
        BASELINE.write_text(json.dumps(
            {"_why": "已知的無認證端點，逐步清；新增的一律 RED。",
             "known_gaps": sorted(gaps)}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"baseline 已更新：{len(gaps)} 條")
        return 0

    if args.json:
        print(json.dumps({"total": len(rows), "no_auth": len(no_auth),
                          "gaps": sorted(gaps), "new_gaps": new_gaps,
                          "fixed_since_baseline": fixed}, ensure_ascii=False, indent=2))
        return 2 if (args.ci and new_gaps) else 0

    print("=" * 64)
    print("無認證端點稽核（FastAPI runtime dependency 樹）")
    print("=" * 64)
    print(f"  API 端點總數      : {len(rows)}")
    print(f"  無認證            : {len(no_auth)}")
    print(f"  其中刻意公開      : {len(no_auth) - len(gaps)}")
    print(f"  缺口（需要認證）  : {len(gaps)}   baseline {len(base)}")
    if fixed:
        print(f"\n  ✓ 已修好 {len(fixed)} 條 —— 請跑 --update-baseline 鎖住改善：")
        for p in fixed[:10]:
            print(f"      {p}")
    if new_gaps:
        print(f"\n  [RED] 新增 {len(new_gaps)} 條無認證端點：")
        for p in new_gaps:
            print(f"      {p}")
        print("\n  修法：在該 router 加 `APIRouter(dependencies=[Depends(require_auth())])`")
        print("        —— 逐一改端點參數會漏，而漏掉的那條不會有人發現。")
        print("  若是刻意公開，請加進本檔的 INTENDED 並**寫明理由**。")
        return 2 if args.ci else 1
    print("\n  [GREEN] 沒有新增的無認證端點")
    if gaps:
        print(f"  （baseline 內仍有 {len(gaps)} 條待清，見 {BASELINE.name}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
