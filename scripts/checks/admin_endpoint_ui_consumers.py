#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""需要管理員的端點，被哪些「非管理頁面」消費 —— 人工觸發，不接排程。

## 為什麼有這支

2026-08-20 owner 回報「同仁又變成代碼」。根因是五個人員下拉全部打
`users/list`（`require_admin()`），一般同仁登入時 403 ⇒ 選項為空 ⇒
AntD Select 直接顯示原始數字 id。

修完之後該問的是：**還有多少地方是這樣**。這支就是那次掃描的正式版。

## 為什麼不接排程

跑完的結論是：**沒有第二個「一般使用者需要的資料掛在管理員端點」的案例**，
剩下的是一個較輕的家族 —— 4 個頁面路由只要登入、但頁內含管理動作，
一般使用者看得到按鈕、按下去 403（`/ai/erp-graph` 的 Ingest Admin 分頁、
`/ai/code-graph`、`/ai/knowledge-graph` 的管理面板、
`/erp/einvoice-sync` 的「同步」）。那些 403 部分是刻意的產品決策，
接排程只會每天報同樣 4 個已知項 ⇒ 變成沒人看的告警。

所以它是**素材**不是哨兵：`OPEN_ITEMS_20260819.md` C5（走查永遠以最高權限跑）
收束時，用這支盤點要驗哪些頁面。

## 判準與已知限制

- 端點權威來源是 **FastAPI runtime 的 dependency 樹**，不是 grep
  （在容器內載入 app，因為 `main` 模組在 `/app`）。
- 常數比對用**完整限定名** `GROUP_ENDPOINTS.NAME`。
  ⚠️ 第一版用裸名，`CREATE`/`DELETE`/`LIST` 在多個 endpoints 檔都有，
  結果把所有 CRUD 都算到 backup 頭上 —— 37 支候選裡一大半是假的。
- `api/*.ts` 是定義層不是頁面；它們會被列出來，但要再追一層才是真消費者。
  這一層**刻意不自動判定**：猜錯會產生假陽性，留給人工核實。

用法：
  python scripts/checks/admin_endpoint_ui_consumers.py          # 人可讀
  python scripts/checks/admin_endpoint_ui_consumers.py --json   # 機器可讀
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FE = PROJECT_ROOT / "frontend" / "src"
CONTAINER = "ck_missive_backend"

# 這些檔案路徑視為「管理頁面本身」，其消費不算問題。
# 規則列在輸出裡 —— 排除規則若不可見，清單就無法被信任。
ADMIN_FILE_PAT = re.compile(
    r"(^|/)(admin|Admin)"
    r"|Management(Page|Tab)?\."
    r"|^pages/(UserFormPage|UserListPage|RolePermission|SecurityCenter|Deployment|Backup|Governance|Permission)"
    r"|^components/(ai/management|dashboard/SystemHealthDashboard|kunge)/?"
    r"|^pages/(digitalTwin|knowledgeBase|codeGraph|knowledgeGraph)/"
    r"|^pages/(UnifiedAgentPage|SystemMonitoringPage|SchedulerEventsPage|DatabaseGraphPage|MemoryDashboardPage)\."
)

_RUNTIME_PROBE = r"""
import json, sys
sys.path.insert(0, "/app")
from main import app
ADMIN = ("require_admin", "require_superuser", "is_admin_user", "is_superuser_user", "get_admin")
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
    hit = sorted(n for n in deps(r) if any(a in n for a in ADMIN))
    if hit:
        rows.append({"path": p, "admin_deps": hit})
print("@@JSON@@" + json.dumps(rows, ensure_ascii=False))
"""


def norm(p: str) -> str:
    p = re.sub(r"^/api/", "", p)
    p = re.sub(r"\{[^}]+\}", "*", p)
    p = re.sub(r"\$\{[^}]+\}", "*", p)
    return p.strip("/")


def fetch_admin_endpoints() -> list[dict]:
    """在應用實際執行的容器內取 route 樹。

    不在 host 跑：host 沒有應用的相依，而且「檢核要在它保護的東西實際
    執行的環境裡驗」是本專案已立的判準（L90/2026-08-11）。
    """
    probe = PROJECT_ROOT / "backend" / "logs" / "_admin_ep_probe.py"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(_RUNTIME_PROBE, encoding="utf-8")
    try:
        r = subprocess.run(
            ["docker", "exec", "-w", "/app", CONTAINER, "python", "/app/logs/_admin_ep_probe.py"],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
    except FileNotFoundError:
        print("[SKIP] 找不到 docker CLI —— 這支需要在能連到 backend 容器的環境執行", file=sys.stderr)
        return []
    except subprocess.TimeoutExpired:
        print("[SKIP] 容器探測逾時", file=sys.stderr)
        return []
    finally:
        probe.unlink(missing_ok=True)
    for line in (r.stdout or "").splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@"):])
    print(f"[SKIP] 容器探測沒有回傳結果：{(r.stderr or '')[-300:]}", file=sys.stderr)
    return []


def scan() -> dict:
    eps = fetch_admin_endpoints()
    if not eps:
        return {"available": False}
    admin_paths = {norm(e["path"]) for e in eps}

    qualified: dict[str, str] = {}
    for f in sorted((FE / "api" / "endpoints").rglob("*.ts")):
        group = None
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            g = re.search(r"export\s+const\s+([A-Z][A-Z0-9_]*)\s*(?::[^=]+)?=\s*\{", line)
            if g:
                group = g.group(1)
                continue
            m = re.search(r"(\b[A-Z][A-Z0-9_]*)\s*:\s*(?:\([^)]*\)\s*=>\s*)?[`']([^`']+)[`']", line)
            if m and group and m.group(2).startswith("/"):
                qualified.setdefault(f"{group}.{m.group(1)}", norm(m.group(2)))

    admin_consts = {q: p for q, p in qualified.items() if p in admin_paths}

    usage: dict[str, set[str]] = defaultdict(set)
    for f in list(FE.rglob("*.ts")) + list(FE.rglob("*.tsx")):
        rel = str(f.relative_to(FE)).replace("\\", "/")
        if rel.startswith(("api/endpoints/", "types/generated/")) or "__tests__" in rel or rel.endswith(".test.ts"):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for q in admin_consts:
            group, name = q.split(".", 1)
            if re.search(re.escape(group) + r"\s*\.\s*" + re.escape(name) + r"\b", text):
                usage[q].add(rel)

    candidates = []
    for q, files in sorted(usage.items()):
        non_admin = sorted(f for f in files if not ADMIN_FILE_PAT.search(f))
        if non_admin:
            candidates.append({"const": q, "path": "/" + admin_consts[q],
                               "non_admin_consumers": non_admin, "total_consumers": len(files)})
    return {"available": True, "admin_endpoints": len(eps), "with_frontend_const": len(admin_consts),
            "consumed": len([q for q, v in usage.items() if v]), "candidates": candidates}


def main() -> int:
    ap = argparse.ArgumentParser(description="管理員端點的非管理頁面消費者（人工觸發）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    res = scan()
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if not res.get("available"):
        print("無法取得端點清單（見上方 SKIP 原因）。這支是人工素材，不判紅。")
        return 0

    print("=" * 66)
    print("需要管理員的端點 × 非管理頁面消費者")
    print("=" * 66)
    print(f"  需要管理員的端點：{res['admin_endpoints']}")
    print(f"  有前端常數對應　：{res['with_frontend_const']}")
    print(f"  真的被消費　　　：{res['consumed']}")
    print(f"  非管理頁面在用　：{len(res['candidates'])}（**候選，非結論**）\n")
    print("排除為「管理頁面自己在用」的規則：路徑含 admin/Admin、*Management(Page|Tab)、")
    print("  UserForm/UserList/RolePermission/SecurityCenter/Deployment/Backup/Governance/Permission、")
    print("  components/{ai/management,dashboard/SystemHealthDashboard,kunge}、")
    print("  pages/{digitalTwin,knowledgeBase,codeGraph,knowledgeGraph}/、")
    print("  UnifiedAgentPage/SystemMonitoring/SchedulerEvents/DatabaseGraph/MemoryDashboard\n")
    print("⚠️ `api/*.ts` 是定義層不是頁面 —— 出現在這裡代表要再追一層消費者。\n")
    for c in res["candidates"]:
        print(f"● {c['const']}  ->  {c['path']}   （共 {c['total_consumers']} 個消費者）")
        for f in c["non_admin_consumers"]:
            print(f"    {f}")
    print()
    print("2026-08-20 首跑人工核實結論：無「一般使用者需要的資料掛在管理員端點」之第二例；")
    print("剩餘為『頁面只要登入但頁內含管理動作』，403 部分屬刻意 —— 見 OPEN_ITEMS C5。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
