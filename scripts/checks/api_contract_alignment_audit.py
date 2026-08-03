#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程式 × 頁面 × 服務 三者對應完整性稽核。

## 為什麼需要它（2026-08-03）

系統裡有**五份「有哪些 API」的清單，三種不同的 key**：

  服務  OpenAPI /openapi.json      724 操作   URL 路徑      FastAPI runtime 自動
  程式  code_graph api_endpoint    714        模組::函式    AST 每日全量
  頁面  frontend/src/api/endpoints 479 常數   URL 路徑      手寫 TS
  ─     tools_manifest             12 工具    工具名        手寫 dict
  ─     Prometheus path 標籤       —          URL 路徑      每日抓

其中三份用 URL 當 key、**可以互相對照，卻沒有任何一支在對照**。
於是沒有一處回答得了「這個端點還有沒有用」「前端這個常數打得到嗎」。

實際後果已經看得到：12 個前端端點常數指向不存在的後端（逐一驗證後確認是死常數、
未造成故障），而其中 2 個**還被測試斷言保護著** —— 測試是綠的，保護的是空殼。

## 這支刻意不做的事

**不建第六份清單**。橋不必自己造：FastAPI runtime 的每個 route 同時有
`path` 與 `endpoint` 函式，本身就是「服務 ↔ 程式」的權威對應，直接讀就好。

**不判定「後端有、前端無」的 257 個端點**。那需要真實流量（`capability_usage_snapshot.py`
在收，判定時點 2026-08-31）。現在只能靠 grep 推論，會產出跟既有 dead_ui 143 候選
同型、沒人敢據以刪除的清單。所以這裡只報數字、不告警。

## 三態
  0 = GREEN    無「前端打不到」的端點
  1 = YELLOW   程式圖譜與 runtime 不一致（要處理，但不是壞掉）
  2 = RED      前端常數指向不存在的後端路由／無法取得資料源

用法：
  python scripts/checks/api_contract_alignment_audit.py
  python scripts/checks/api_contract_alignment_audit.py --json   # 輸出結構化結果
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FE_ENDPOINT_DIR = REPO / "frontend" / "src" / "api" / "endpoints"
FE_SRC = REPO / "frontend" / "src"
BACKEND_CONTAINER = "ck_missive_backend"
PG_CONTAINER = "ck_missive_postgres"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _norm(path: str) -> str:
    """把路徑正規化到可比對的形態。

    前端常數不含 `/api` 前綴（apiClient 的 baseURL 已含），且用 `${id}` 樣板；
    後端用 `{id}`。兩邊都收斂成 `/api/...` + `{}`。
    """
    p = path.strip()
    p = re.sub(r"\$\{[^}]*\}", "{}", p)
    p = re.sub(r"\{[^}]*\}", "{}", p)
    if not p.startswith("/api"):
        p = "/api" + ("" if p.startswith("/") else "/") + p
    return p.rstrip("/") or "/"


# ---------------------------------------------------------------- 服務（權威）

def load_service_routes() -> list[dict]:
    """從 FastAPI runtime 取 route，**這是三者對應的權威來源**。

    在容器內執行：host 沒有完整的執行環境，而 `openapi.json` 只有 path、
    沒有 endpoint 函式，湊不出「服務 ↔ 程式」那一邊。
    """
    code = (
        "import sys,json; sys.path.insert(0,'/app');"
        "from main import app;"
        "out=[{'path':r.path,'module':getattr(r.endpoint,'__module__',''),"
        "'func':getattr(r.endpoint,'__name__',''),"
        "'methods':sorted(getattr(r,'methods',[]) or [])}"
        " for r in app.routes if getattr(r,'endpoint',None) is not None"
        " and hasattr(r,'path')];"
        "print('@@JSON@@'+json.dumps(out))"
    )
    proc = subprocess.run(
        ["docker", "exec", BACKEND_CONTAINER, "python", "-c", code],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@"):])
    raise RuntimeError(f"無法從容器取得 routes（exit={proc.returncode}）：{proc.stderr[-300:]}")


# ---------------------------------------------------------------- 程式（圖譜）

def load_code_graph_endpoints() -> set[str]:
    """code_graph 的 api_endpoint，形態是 `模組::函式`。"""
    proc = subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", "ck_user", "-d", "ck_documents",
         "-tAc", "SELECT canonical_name FROM canonical_entities WHERE entity_type='api_endpoint';"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"無法查 code_graph：{proc.stderr[-300:]}")
    return {l.strip() for l in proc.stdout.splitlines() if l.strip()}


# ---------------------------------------------------------------- 頁面（前端）

def load_frontend_constants() -> dict[str, str]:
    """前端端點常數：正規化路徑 -> 原始字面值（供人回查）。"""
    out: dict[str, str] = {}
    for f in FE_ENDPOINT_DIR.glob("*.ts"):
        for raw in re.findall(r"['\"](/[A-Za-z0-9/_{}$.\-]+)['\"]", f.read_text(encoding="utf-8")):
            out.setdefault(_norm(raw), raw)
    return out


# 這裡原本還有第三個維度「常數有定義但沒人用」，**已於同日移除**。
# 兩種比對法都做不到可信：用常數名 `OBJ.KEY` 會漏掉解構匯入；用路徑字面值
# 會把 `ROLE_PERMISSIONS_LIST` 這種明明有人用的判成死的。放寬條件後做鑑別力測試
# —— 注入一個確定沒人用的 key，仍然判 0，**等於無鑑別力**。
# 依 08-02 立的判準（無鑑別力就不交付），寧可不報這個維度，也不要交一份不能採信的清單。


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    print("=" * 70)
    print(" 程式 × 頁面 × 服務 — 三者對應完整性")
    print("=" * 70)

    try:
        routes = load_service_routes()
        cg = load_code_graph_endpoints()
    except Exception as e:
        # 取不到資料源要 RED，不能因為「查不到」就印綠燈
        print(f"  ✗ RED：資料源不可用 — {e}")
        return 2

    consts = load_frontend_constants()

    # 服務側：只看業務路由（排除 FastAPI 內建的 docs/openapi、以及靜態掛載）
    biz = [r for r in routes if r["path"].startswith("/api")
           and not r["module"].startswith("fastapi.")]
    svc_paths = {_norm(r["path"]) for r in biz}
    svc_funcs = {f"{r['module']}::{r['func']}" for r in biz}

    print(f"\n  服務 (FastAPI runtime)  : {len(biz)} 條業務路由")
    print(f"  程式 (code_graph)       : {len(cg)} 個 api_endpoint")
    print(f"  頁面 (前端端點常數)     : {len(consts)} 條")

    # ── 服務 ↔ 頁面 ────────────────────────────────────────────────
    fe_only = sorted(set(consts) - svc_paths)          # 前端打不到 → RED
    svc_only = sorted(svc_paths - set(consts))         # 無前端引用 → 只報數字
    print(f"\n  [服務↔頁面] 對得上 {len(set(consts) & svc_paths)}"
          f"｜前端打不到 {len(fe_only)}｜無前端引用 {len(svc_only)}")

    # ── 服務 ↔ 程式 ────────────────────────────────────────────────
    # code_graph 的 AST 掃描範圍是 `app/`，不含 `main.py`。目前落在 main.py 的
    # 只有兩個 CORS debug 端點，且都有 DEVELOPMENT_MODE 守衛、生產實測 404/403。
    # 把它們算成「圖譜漏收」會讓這支永遠 YELLOW＝訓練人忽略黃燈。
    # **已知限制**：若日後有人把業務端點寫進 main.py，這裡不會發現 —— 那應該由
    # 「業務端點不得寫在 main.py」的規約來擋，而不是靠這支對照。
    cg_missing = sorted(f for f in (svc_funcs - cg) if not f.startswith("main::"))
    cg_stale = sorted(cg - svc_funcs)                  # 圖譜殘留
    print(f"  [服務↔程式] 對得上 {len(svc_funcs & cg)}"
          f"｜圖譜漏收 {len(cg_missing)}｜圖譜殘留 {len(cg_stale)}")


    result = {
        "service_routes": len(biz), "code_graph_endpoints": len(cg),
        "frontend_constants": len(consts),
        "frontend_unreachable": fe_only, "service_without_frontend": len(svc_only),
        "code_graph_missing": cg_missing[:50], "code_graph_stale": cg_stale[:50],
    }
    if args.json:
        print("\n@@JSON@@" + json.dumps(result, ensure_ascii=False))

    rc = 0
    if fe_only:
        print(f"\n  ✗ RED：{len(fe_only)} 條前端常數指向不存在的後端路由（呼叫必然失敗）")
        for p in fe_only[:15]:
            print(f"     {consts[p]}   → 正規化 {p}")
        rc = 2
    else:
        print("\n  ✓ 前端常數全部打得到後端")

    if rc != 2 and (cg_missing or cg_stale):
        print(f"\n  ⚠ YELLOW：程式圖譜與 runtime 不一致"
              f"（漏收 {len(cg_missing)}／殘留 {len(cg_stale)}）")
        for f in (cg_missing + cg_stale)[:10]:
            print(f"     {f}")
        rc = 1

    # 這一項刻意不影響判定：沒有真實流量之前，「無前端引用」不等於「沒人用」
    # （可能是 AI agent／Hermes／內部呼叫）。判定時點 2026-08-31。
    print(f"\n  ℹ {len(svc_only)} 條端點無前端引用 — **不據此判定死活**，"
          f"需 capability_usage_snapshot 的真實流量（判定時點 2026-08-31）")

    print("\n" + ("GREEN" if rc == 0 else "YELLOW" if rc == 1 else "RED"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
