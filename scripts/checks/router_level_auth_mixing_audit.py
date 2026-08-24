#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""router 層認證有沒有誤擋公開端點（C2）。

## 為什麼有這支

2026-08-21 收斂無認證端點時，修法一律加在 **router 層**
（`APIRouter(dependencies=[Depends(require_auth())])`）而不是逐一改端點參數 ——
理由是「逐一改會漏，而漏掉的那條不會有人發現」。

但 CK_PileMgmt 2026-08-24 指出這個作法的反面風險：**同一個 router 檔案裡
可能混雜真公開端點與該收斂端點**（他們的 `gislayers` 一半是管理 CRUD、
一半是公開地圖互動）。router 層加認證會把公開那半也一起擋掉，
而**那種失敗只有真的打開那一頁才看得見** —— tsc 看不到、
py_compile 看不到、走查以管理員身分跑也看不到。

## 判準

1. 找出所有加了 router 層認證依賴的端點檔；
2. 用 **runtime** 取得那些檔案底下的端點路徑（不是 grep 原始碼 ——
   端點可能來自 include_router 的巢狀組合）；
3. 找出前端**真正不需登入且會渲染**的路由；
4. 若有公開路由消費到受保護檔案的端點 ⇒ RED。

## ⚠️ 這支看不到什麼（寫出來，免得它被當成全面）

**非瀏覽器消費者** —— Prometheus／webhook／Hermes 不在前端路由裡。
那一面由 `integration_e2e_validation.py` 負責（Hermes 三條鏈）與
`public_endpoint_auth_audit.py` 的白名單負責。

## 兩個量測陷阱（都是 2026-08-24 實際踩到的）

* **`<Navigate>` 轉址不是頁面** —— 它不渲染、不打 API。第一版沒排除它，
  於是 `ROUTES.PROJECTS`／`TAOYUAN`／`DIGITAL_TWIN` 全被標成「不需登入」，
  **24 條裡有 12 條是假的**。
* **不能只 grep 原始碼找端點** —— 要問 runtime，因為端點路徑由
  `include_router(prefix=...)` 組出來，原始碼裡看不到完整路徑。

退出碼：0 GREEN／2 RED（有公開路由消費受保護端點，或探測不可用）。
"""
from __future__ import annotations

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

#: ⚠️ parents[2] 不是 [1] —— 本檔在 scripts/checks/ 底下，差一層。
#: 2026-08-24 第一版寫 [1]，於是 guarded_files() 與 public_routes() 都掃到
#: 不存在的目錄、回空集合，而檢核**印 GREEN**。
#: **一支找不到東西就回綠的檢核比沒有檢核更糟**（本專案 08-18 已記過同型）。
REPO = Path(__file__).resolve().parents[2]
CONTAINER = "ck_missive_backend"
ENDPOINTS = REPO / "backend" / "app" / "api" / "endpoints"
APP_ROUTER = REPO / "frontend" / "src" / "router" / "AppRouter.tsx"

_PROBE = r'''
import inspect, json, sys
sys.path.insert(0, "/app")
from main import app
out = []
for r in app.routes:
    p, ep = getattr(r, "path", None), getattr(r, "endpoint", None)
    if not p or ep is None:
        continue
    try:
        f = inspect.getsourcefile(ep) or ""
    except Exception:
        f = ""
    out.append({"path": p, "file": f})
print("@@JSON@@" + json.dumps(out))
'''


def probe() -> list[dict] | None:
    """問 runtime 要「端點 → 定義它的檔案」。

    不 grep 原始碼：端點路徑由 include_router(prefix=...) 組出來，
    原始碼裡看不到完整路徑。
    """
    try:
        r = subprocess.run(
            ["docker", "exec", "-i", "-e", "PYTHONIOENCODING=utf-8",
             "-w", "/app", CONTAINER, "python", "-"],
            input=_PROBE.encode("utf-8"), capture_output=True, timeout=180)
    except FileNotFoundError:
        print("[RED] 找不到 docker CLI —— 無法取得 runtime 事實，不下結論", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[RED] 容器探測逾時", file=sys.stderr)
        return None
    for line in (r.stdout or b"").decode("utf-8", "replace").splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@"):])
    print(f"[RED] 探測沒有回傳結果：{(r.stderr or b'').decode('utf-8', 'replace')[-300:]}",
          file=sys.stderr)
    return None


def guarded_files() -> set[str]:
    """加了 router 層認證依賴的端點檔（相對 endpoints/ 的路徑）。"""
    out = set()
    for f in ENDPOINTS.rglob("*.py"):
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if re.search(r"APIRouter\([^)]*dependencies\s*=", t, re.S):
            out.add(str(f.relative_to(ENDPOINTS)).replace("\\", "/"))
    return out


def public_routes() -> list[str]:
    """前端**真正不需登入且會渲染**的路由。

    ⚠️ 排除 `<Navigate>` —— 轉址不渲染也不打 API。2026-08-24 第一版沒排除，
    24 條裡有 12 條是假的。
    """
    if not APP_ROUTER.exists():
        return []
    out = []
    for line in APP_ROUTER.read_text(encoding="utf-8", errors="replace").split("\n"):
        if "<Route" not in line or "<Navigate" in line:
            continue
        if "ProtectedRoute" in line or "AuthGuard" in line:
            continue
        m = re.search(r'path=[{"\']+([^"\'}\s]+)', line)
        if m:
            out.append(m.group(1))
    return out


def main() -> int:
    rows = probe()
    if rows is None:
        return 2   # 探測不到就是不知道，不得靜靜回綠

    guarded = guarded_files()
    # 找不到東西不得回綠 —— 2026-08-24 第一版 REPO 路徑差一層，
    # 三個集合全空而它印 GREEN。**一支找不到東西就回綠的檢核比沒有檢核更糟。**
    if not ENDPOINTS.exists() or not APP_ROUTER.exists():
        print(f"[RED] 掃描目標不存在，無法下結論：\n"
              f"      endpoints={ENDPOINTS}（{'在' if ENDPOINTS.exists() else '不在'}）\n"
              f"      AppRouter={APP_ROUTER}（{'在' if APP_ROUTER.exists() else '不在'}）",
              file=sys.stderr)
        return 2
    if not guarded:
        print("[RED] 一個加了 router 層認證的檔案都沒找到 —— "
              "2026-08-21 明明改了 16 個，這個 0 是掃描壞了不是現況",
              file=sys.stderr)
        return 2

    by_file: dict[str, list[str]] = {}
    for row in rows:
        fn = row["file"].replace("\\", "/")
        if "/api/endpoints/" not in fn:
            continue
        key = fn.split("/api/endpoints/", 1)[1]
        if key in guarded:
            by_file.setdefault(key, []).append(row["path"])

    pub = public_routes()
    #: 認證流程與 404 —— 這些頁面本來就該公開，且不消費業務端點
    AUTH_FLOW = re.compile(
        # ⚠️ 用 `MFA` 配 `$` 錨定會漏掉 `MFA_VERIFY`（2026-08-24 實跑抓到）——
        # 認證流程的常數名會長出後綴，所以這裡用**前綴**比對不用完整比對。
        r"^(ROUTES\.)?(HOME|ENTRY|LOGIN|REGISTER|FORGOT_PASSWORD|RESET_PASSWORD|"
        r"MFA|VERIFY_EMAIL|LINE_CALLBACK|LINE_BIND_CALLBACK|NOT_FOUND)")
    unexpected = [p for p in pub if p != "*" and not AUTH_FLOW.search(p)]

    print("=" * 66)
    print("router 層認證有沒有誤擋公開端點")
    print("=" * 66)
    print(f"  加了 router 層認證的端點檔 : {len(guarded)}")
    print(f"  其下端點                   : {sum(len(v) for v in by_file.values())}")
    print(f"  前端不需登入且會渲染的路由 : {len(pub)}（認證流程與 404）")

    if unexpected:
        print(f"\n  [RED] {len(unexpected)} 條公開路由不屬於認證流程 ——")
        print("        它們可能消費到已被 router 層擋住的端點，請逐一核實：")
        for p in unexpected:
            print(f"      {p}")
        print("\n  核實方式：打開該頁面（**未登入狀態**）看有沒有 401。")
        print("  tsc／py_compile／以管理員身分跑的走查都看不到這種失敗。")
        return 2

    print("\n  [GREEN] 公開路由全部是認證流程頁面，不消費受保護端點")
    print("\n  ⚠️ 這支看不到**非瀏覽器消費者**（Prometheus／webhook／Hermes）——")
    print("     那一面由 integration_e2e_validation 與 public_endpoint_auth_audit 負責。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
