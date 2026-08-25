#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""管理動作有沒有給一般同仁看見（C4）。

## 為什麼有這支

`OPEN_ITEMS` B7：**4 個頁面路由只要登入（`ProtectedRoute`），而頁內含管理動作**
⇒ 一般同仁看得到那個按鈕／分頁，**點下去必然 403**。

而那些 403 **部分是刻意的**（電子發票同步會呼叫財政部 API、有配額；
入圖會重建圖譜）—— 所以修法不是放寬端點權限，是
**畫面不該給一個必然失敗的按鈕**。

2026-08-24 實查四頁：`CodeGraphManagementPage`／`KnowledgeGraphPage`／
`ERPEInvoiceSyncPage` **都已有 `isAdmin` 判斷且真的用在渲染上**，
只有 `ERPGraphPage` 漏了（它的「入圖管理」分頁無條件顯示）。已補。

## 判準

一個前端頁面若消費了**需要管理員的端點**，它必須有身分守衛
（`isAdmin` / `hasPermission` / `useAuthGuard` 取用），否則 RED。

⚠️ 判準刻意寬鬆到「**檔案裡有沒有身分判斷**」而不是「那個判斷有沒有
包住正確的元素」—— 後者要語意判斷，做成腳本只會得到一份不可信的清單
（同 v6.39 否決自動分類的理由）。這支抓的是**完全沒有守衛**的那一類，
那正是 ERPGraphPage 的形態。

## ⚠️ 這支看不到什麼

* 守衛存在但包錯元素（要人看）；
* 非前端消費者（Hermes／webhook）—— 它們不走這條路徑。

退出碼：0 GREEN／2 RED（有頁面消費管理端點卻無身分守衛）。
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

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend" / "src"
CONTAINER = "ck_missive_backend"

#: 身分守衛的寫法 —— 這幾種在本 repo 都實際用著。
#: ⚠️ 不要只認一種：08-10 的教訓正是「管理員判定有四份規則」，
#: 只認 `isAdmin` 會把用 `hasPermission('admin:access')` 的頁面誤報。
GUARD_PATTERNS = ("isAdmin", "hasPermission(", "isSuperuser", "requireAdmin")

_PROBE = r'''
import json, sys
sys.path.insert(0, "/app")
from main import app
ADMIN = ("require_admin", "require_superuser", "is_admin_user", "is_superuser_user")
def deps(route):
    out, d = set(), getattr(route, "dependant", None)
    if not d:
        return out
    st = [d]
    while st:
        c = st.pop()
        f = getattr(c, "call", None)
        if f is not None:
            out.add(getattr(f, "__qualname__", getattr(f, "__name__", "?")))
        st.extend(getattr(c, "dependencies", []) or [])
    return out
out = []
for r in app.routes:
    p = getattr(r, "path", None)
    if not p or not str(p).startswith("/api"):
        continue
    if any(any(a in n for a in ADMIN) for n in deps(r)):
        out.append(str(p))
print("@@JSON@@" + json.dumps(sorted(set(out))))
'''


def admin_paths() -> list[str] | None:
    """需要管理員的端點路徑 —— 問 runtime，不 grep 裝飾器。"""
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
    print("[RED] 探測沒有回傳結果", file=sys.stderr)
    return None


def main() -> int:
    paths = admin_paths()
    if paths is None:
        return 2
    if not FRONTEND.exists():
        print(f"[RED] 找不到前端目錄：{FRONTEND}", file=sys.stderr)
        return 2
    if not paths:
        print("[RED] 一條需要管理員的端點都沒找到 —— 那是掃描壞了不是現況",
              file=sys.stderr)
        return 2

    #: 端點路徑的尾段（去掉 /api 與參數），用來在前端找**字面值**
    tails = {}
    for p in paths:
        t = re.sub(r"\{[^}]+\}", "", p[len("/api"):]).rstrip("/")
        if len(t) > 8:
            tails[t] = p

    #: ⚠️ 只比對字面路徑**抓不到本 repo 的主要寫法**。
    #: 規範 §1「所有 API 走端點常數，禁止硬編路徑」⇒ 頁面裡寫的是
    #: `AI_ENDPOINTS.GRAPH_ERP_INGEST`，字面路徑根本不在頁面檔裡。
    #: 2026-08-24 負向測試揭露：把 ERPGraphPage 的守衛**完全移除**
    #: （檔內 isAdmin 剩 0 處），這支仍回 GREEN ——
    #: **它抓不到自己被建立來抓的那個案例**，而首跑那兩個命中剛好都是假陽性。
    #:
    #: ⚠️⚠️ 而且**必須用完整限定名**：`CREATE`／`DELETE`／`LIST` 在
    #: admin(3)／core(6)／projects(9)／users(14) 四個檔裡都有 ——
    #: 裸名比對會把 `API_ENDPOINTS.USERS.CREATE` 對到 backup 的 CREATE，
    #: 報出「員工建立頁在打備份端點」。（08-20 掃全管理員端點時已踩過
    #: 同一個坑：裸名 37 支候選一大半是假的，改限定名後降到 18 支。）
    #:
    #: 本 repo 有兩種寫法，兩種都要認：
    #:   ① `BACKUP_ENDPOINTS.CREATE`        group 直接用
    #:   ② `API_ENDPOINTS.BACKUP.CREATE`    barrel 別名（index.ts 組起來的）
    ep_dir = FRONTEND / "api" / "endpoints"
    if not ep_dir.exists():
        print(f"[RED] 找不到端點常數目錄：{ep_dir}", file=sys.stderr)
        return 2

    group_key_path: dict[tuple[str, str], str] = {}
    alias_of_group: dict[str, str] = {}
    for ef in sorted(ep_dir.rglob("*.ts")):
        et = ef.read_text(encoding="utf-8", errors="replace")
        group = None
        for line in et.splitlines():
            m = re.match(r"export const ([A-Z][A-Z0-9_]*)\s*=\s*\{", line)
            if m:
                group = m.group(1)
                continue
            # barrel：`ALIAS: X_ENDPOINTS,`
            m = re.match(r"\s+([A-Z][A-Z0-9_]*)\s*:\s*([A-Z][A-Z0-9_]*_ENDPOINTS)\s*,?\s*$", line)
            if m:
                alias_of_group[m.group(2)] = m.group(1)
                continue
            if not group:
                continue
            # `KEY: '/path'` 或 `KEY: (x) => `/path...``
            m = re.match(r"\s+([A-Z][A-Z0-9_]*)\s*:\s*(?:\([^)]*\)\s*=>\s*)?[`'\"]([^`'\"]+)", line)
            if m:
                key, path = m.group(1), m.group(2)
                for tail, full in tails.items():
                    if path.startswith(tail):
                        group_key_path[(group, key)] = full
                        break
    if not group_key_path:
        print("[RED] 一個端點常數都沒解析到 —— 掃描壞了不是現況", file=sys.stderr)
        return 2

    #: 完整限定名（兩種寫法）→ 端點路徑
    qualified: dict[str, str] = {}
    for (group, key), full in group_key_path.items():
        qualified[f"{group}.{key}"] = full
        alias = alias_of_group.get(group)
        if alias:
            qualified[f"{alias}.{key}"] = full

    #: ⚠️ 決定性的維度：**那個頁面掛在什麼路由底下**。
    #: 加常數解析後首報 14 個，逐一看多數是 AdminDashboardPage／
    #: BackupManagementPage 這類 —— 它們的路由寫著 `roles={['admin']}`，
    #: 一般同仁**根本進不去**，頁內不需要再判一次（判定只該有一份，08-10）。
    #:
    #: B7 的形態恰恰相反：**路由只要登入、頁內卻有管理動作**，
    #: 例如 `<Route path={ROUTES.ERP_GRAPH} element={<ProtectedRoute><ERPGraphPage/></ProtectedRoute>}/>`。
    router = FRONTEND / "router" / "AppRouter.tsx"
    if not router.exists():
        print(f"[RED] 找不到 {router} —— 沒有路由資訊就無法判定", file=sys.stderr)
        return 2
    rt = router.read_text(encoding="utf-8", errors="replace")

    # 元件名 → 模組路徑（lazy import）
    comp_module: dict[str, str] = {}
    for m in re.finditer(r"const\s+(\w+)\s*=\s*lazy\(\s*\(\)\s*=>\s*import\(['\"]([^'\"]+)", rt):
        comp_module[m.group(1)] = m.group(2)
    # 直接 import 的頁面元件
    for m in re.finditer(r"^import\s+(?:\{\s*)?(\w+)[^\n]*from\s+['\"](\.\./pages/[^'\"]+)", rt, re.M):
        comp_module.setdefault(m.group(1), m.group(2))

    # 元件名 → 該路由有沒有 roles 限制
    routed_open: set[str] = set()   # 只要登入
    routed_admin: set[str] = set()  # 有 roles 限制
    for m in re.finditer(r"<ProtectedRoute([^>]*)>\s*<(\w+)\s*/?>", rt):
        attrs, comp = m.group(1), m.group(2)
        (routed_admin if "roles={[" in attrs else routed_open).add(comp)

    if not comp_module or not (routed_open | routed_admin):
        print("[RED] 路由解析不到任何頁面 —— 掃描壞了不是現況", file=sys.stderr)
        return 2

    #: 模組路徑（`../pages/X`）→ 檔案相對路徑（`pages/X.tsx`）
    open_files = {comp_module[c].replace("../", "") + ".tsx"
                  for c in routed_open if c in comp_module}

    offenders = []
    for f in sorted(FRONTEND.rglob("*.tsx")):
        if "__tests__" in str(f) or f.name.endswith(".test.tsx"):
            continue
        try:
            t = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # ⚠️ 先去掉註解再比對 —— 首跑兩個命中裡有一個是假陽性：
        # ContractCaseStaffFormPage 的 `/users/list` 只出現在**註解**裡
        # （2026-08-20 修好時寫的說明「這裡原本打 /users/list」），
        # 實際打的是 `/users/assignable`。比對原始碼字面值而不排除註解，
        # 等於把「我們曾經打過它」讀成「我們現在在打它」。
        body = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
        body = re.sub(r"^\s*//.*$", "", body, flags=re.M)
        hits = [full for tail, full in tails.items() if tail in body]
        hits += [full for q, full in qualified.items()
                 if re.search(r"\b" + re.escape(q).replace(r"\.", r"\s*\.\s*") + r"\b", body)]
        hits = sorted(set(hits))
        if not hits:
            continue
        if any(g in body for g in GUARD_PATTERNS):
            continue
        # ⚠️ 只算「被路由掛載、且路由只要登入」的頁面：
        #   * 頁內的 tab 元件（`pages/knowledgeBase/WikiAdminTab.tsx` 等）
        #     守衛在父頁 —— 要求每個元件自己帶守衛，會逼出一堆重複的判斷；
        #   * `roles={['admin']}` 的路由，一般同仁根本進不去。
        # 首跑另一個假陽性是 components/dashboard/SystemHealthDashboard.tsx，
        # 它的唯一消費者是 AdminDashboardPage，守衛在那裡。
        rel = str(f.relative_to(FRONTEND)).replace("\\", "/")
        if rel not in open_files:
            continue
        offenders.append((rel, hits[:3]))

    print("=" * 66)
    print("管理動作有沒有給一般同仁看見")
    print("=" * 66)
    print(f"  需要管理員的端點 : {len(paths)}")
    print(f"  掃描前端頁面     : {len(list(FRONTEND.rglob('*.tsx')))} 個 .tsx")
    print(f"  只要登入的路由   : {len(open_files)}（另 {len(routed_admin)} 條有 roles 限制，一般同仁進不去）")

    if offenders:
        print(f"\n  [RED] {len(offenders)} 個頁面消費管理端點但**沒有任何身分守衛**：")
        for name, hits in offenders:
            print(f"      {name}")
            for h in hits:
                print(f"          → {h}")
        print("\n  修法：**不顯示那個按鈕／分頁**，不是放寬端點權限 ——")
        print("        那些 403 部分是刻意的（配額、重建圖譜）。")
        print("        缺的是「畫面不該給一個必然失敗的按鈕」（OPEN_ITEMS B7）。")
        return 2

    print("\n  [GREEN] 消費管理端點的頁面都有身分守衛")
    print("\n  ⚠️ 這支只看「有沒有守衛」，不看「守衛有沒有包住正確的元素」——")
    print("     後者要語意判斷，做成腳本只會得到一份不可信的清單。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
