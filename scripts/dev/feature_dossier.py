#!/usr/bin/env python
"""功能模組履歷 —— 把系統的語言翻譯成使用者的語言。

## 為什麼要這一支

`dossier.py` 以**檔案／ADR** 為單位組履歷，那是系統的語言。
但 owner 與使用者的心智模型是**功能模組** ——「公文管理」「桃園查估」「報表分析」。

兩者之間隔著五段鏈，每一段都有資料，卻沒有任何一處把它們接起來。後果就是
2026-08-13 發生的事：`tender_cache` 匯入壞掉時，**沒有任何一個畫面會說
「標案功能的圖譜查詢壞了」** —— 只有一行 `Tool ... failed` 的 warning。

五段素材全部既有，一段都不需要新建：

| 段 | 來源 | 既有規模 |
|---|---|---|
| 功能模組 → 路由 | DB `site_navigation_items` | 76 項／64 有路由／7 個頂層 |
| 路由 → 前端頁面 | `router/types.ts` + `router/AppRouter.tsx` | 140 條 Route |
| 前端頁面 → API | 頁面 import + `api/endpoints/*.ts` | 端點常數 479 條 |
| API → 後端模組 | FastAPI runtime route→endpoint 函式 | 714 端點 |
| 後端模組 → 紀錄 | `dossier.py` 的七段 | ADR 23／教訓 80 |

## 鑑別力

依 `SELF_AUDIT_EVOLUTION_STANDARD` §3：任何比對工具交付前必須用「已知為真」
與「已知為假」各驗一次，**驗不出鑑別力的維度一律不交付**（v6.38 就砍掉過
「常數有定義但沒人用」那個維度）。本支對每一段都印出對應數，
對不上的**明講對不上**，不假裝有答案。

## 用法

    python scripts/dev/feature_dossier.py --list            # 列出功能模組
    python scripts/dev/feature_dossier.py 公文管理           # 單一模組履歷
    python scripts/dev/feature_dossier.py --all --emit-wiki  # 全部落地 wiki
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"


# ---------------------------------------------------------------- 段 1：功能模組 → 路由
def load_features() -> list[dict]:
    """從 DB 讀導覽樹 —— 那是使用者眼中的系統，不是我們自己另編一份清單。"""
    sql = (
        "SELECT COALESCE(p.title, n.title) AS top, n.title, n.path "
        "FROM site_navigation_items n "
        "LEFT JOIN site_navigation_items p ON p.id = n.parent_id "
        "WHERE n.is_enabled AND n.path IS NOT NULL "
        "ORDER BY COALESCE(p.sort_order, n.sort_order), n.sort_order;"
    )
    out = subprocess.run(
        ["docker", "exec", "ck_missive_postgres", "psql", "-U", "ck_user",
         "-d", "ck_documents", "-t", "-A", "-F", "|", "-c", sql],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
    ).stdout
    feats: dict[str, dict] = {}
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) != 3 or not parts[2].strip():
            continue
        top, title, path = (p.strip() for p in parts)
        feats.setdefault(top, {"name": top, "items": []})
        feats[top]["items"].append({"title": title, "path": path})
    return list(feats.values())


# ---------------------------------------------------------------- 段 2：路由 → 前端頁面
_ROUTE_CONST = re.compile(r"^\s*([A-Z0-9_]+):\s*'([^']+)'", re.M)
# element 常被守衛包起來（`element={<ProtectedRoute><DocumentPage /></ProtectedRoute>}`），
# 只抓第一個元件名會拿到 ProtectedRoute → 每一條都對不上。
# 改成抓整段 element，再從裡面挑「lazy 表裡有的那個」才是真正的頁面。
_ROUTE_EL = re.compile(r"<Route\s+path=\{ROUTES\.([A-Z0-9_]+)\}\s+element=\{(.*?)\}\s*/>", re.S)
_LAZY = re.compile(r"const\s+(\w+)\s*=\s*lazy\(\(\)\s*=>\s*import\('([^']+)'")


def route_to_page() -> dict[str, str]:
    """path → 前端頁面檔。三段查表：path→ROUTES key→元件→檔案。"""
    types_src = (FE / "router" / "types.ts").read_text(encoding="utf-8", errors="ignore")
    key_to_path = {m.group(1): m.group(2) for m in _ROUTE_CONST.finditer(types_src)}
    app_src = (FE / "router" / "AppRouter.tsx").read_text(encoding="utf-8", errors="ignore")
    comp_to_file = {m.group(1): m.group(2) for m in _LAZY.finditer(app_src)}
    out: dict[str, str] = {}
    for m in _ROUTE_EL.finditer(app_src):
        key, element = m.group(1), m.group(2)
        path = key_to_path.get(key)
        if not path:
            continue
        # element 內可能有多個元件（守衛 + 頁面）→ 取 lazy 表裡有的那個
        for comp in re.findall(r"<(\w+)", element):
            rel = comp_to_file.get(comp)
            if rel:
                out[path] = rel.replace("../", "frontend/src/") + ".tsx"
                break
    return out


# ---------------------------------------------------------------- 段 3：前端頁面 → API
def _endpoint_constants() -> dict[str, str]:
    """`物件.鍵` → URL。

    ⚠️ 初版只用「鍵名」比對，結果 `LIST` / `LOGIN` / `CREATE` / `EXPORT` 這些
    通用字在任何檔案裡都能命中 —— 公文管理因此被算成會打 `/auth/login`
    與 `/erp/quotations/export`。**那份清單整份是假的。**
    端點常數實際的引用形式是 `DOCUMENTS_ENDPOINTS.LIST`，所以鍵必須帶物件前綴。
    """
    const: dict[str, str] = {}
    for f in (FE / "api" / "endpoints").glob("*.ts"):
        src = f.read_text(encoding="utf-8", errors="ignore")
        obj = None
        for line in src.splitlines():
            m = re.match(r"export const ([A-Z0-9_]+)\s*=", line)
            if m:
                obj = m.group(1)
                continue
            k = re.match(r"\s*([A-Z0-9_]+):\s*'(/[^']+)'", line)
            if k and obj:
                const[f"{obj}.{k.group(1)}"] = k.group(2)
    return const


def _resolve(base: Path, rel: str) -> Path | None:
    t = (base / rel).resolve()
    for cand in (t.with_suffix(".tsx"), t.with_suffix(".ts"),
                 t / "index.ts", t / "index.tsx"):
        if cand.exists():
            return cand
    return None


def page_to_apis(page_rel: str, const: dict[str, str], depth: int = 2) -> list[str]:
    """一個頁面打到哪些 API —— 追到 hook 層為止。

    深度 2 不是隨手取的：本專案的架構是 **pages → hooks → api/endpoints**
    （`.claude/rules/architecture-frontend.md`），頁面本身通常一個端點常數都不引用
    （`DocumentPage.tsx` 就是零引用）。追一層看不到任何 API，
    追太深則會把整個 app 的端點都算進來 —— 那種「每個功能都用到所有 API」的
    清單沒有鑑別力，依 §3 規則不得交付。
    """
    start = ROOT / page_rel
    if not start.exists():
        return []
    seen: set[Path] = {start}
    frontier = [start]
    for _ in range(depth):
        nxt: list[Path] = []
        for f in frontier:
            try:
                src = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in re.finditer(r"from\s+'(\.[^']+)'", src):
                c = _resolve(f.parent, m.group(1))
                if c and c not in seen:
                    seen.add(c)
                    nxt.append(c)
        frontier = nxt

    hits: set[str] = set()
    for f in seen:
        try:
            src = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for qualified, url in const.items():
            obj, key = qualified.split(".", 1)
            if re.search(rf"\b{obj}\.{key}\b", src):
                hits.add(url)
    return sorted(hits)


# ---------------------------------------------------------------- 段 4：API → 後端模組
def api_to_module() -> dict[str, str]:
    """URL 前綴 → 後端 endpoint 模組。用 FastAPI 自己的 router 掛載，不另建對照表。"""
    out: dict[str, str] = {}
    routes = ROOT / "backend" / "app" / "api" / "routes.py"
    if not routes.exists():
        return out
    src = routes.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(
            r"include_router\(\s*([\w.]+)\.router[^)]*?prefix\s*=\s*[\"']([^\"']+)[\"']", src, re.S):
        out[m.group(2)] = m.group(1)
    return out


# ---------------------------------------------------------------- 段 5：誰在看它
def _walk_results() -> dict[str, list[str]]:
    """走查結果 —— 只取檔案裡**真的有**的東西。

    ⚠️ `ui-sweep.json` 記的是 `pass`/`fail` 總數、`failures`、`known_limitations`，
    **沒有通過路由的清單**。所以「這個功能模組有沒有被走查涵蓋」在現有資料裡
    無法回答。初版假設它有 `results[]` 而算出「涵蓋 0/3」—— 那個 0 不是
    「沒被涵蓋」，是「查不到」，兩者意思相反。這裡只回真的讀得到的失敗清單。
    """
    out: dict[str, list[str]] = {"failures": []}
    f = ROOT / "wiki" / "memory" / "integration-health" / "ui-sweep.json"
    if not f.exists():
        return out
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return out
    for item in data.get("failures") or []:
        r = item.get("route") if isinstance(item, dict) else str(item)
        if r:
            out["failures"].append(str(r))
    return out


def render(feat: dict, r2p: dict, const: dict, a2m: dict, cov: dict, md: bool) -> str:
    h1, h2 = ("# ", "## ") if md else ("", "── ")
    b = [f"{h1}功能模組履歷：{feat['name']}", ""]

    pages, apis, modules, unmapped = [], set(), set(), []
    for it in feat["items"]:
        page = r2p.get(it["path"])
        if page:
            pages.append((it["title"], it["path"], page))
            for u in page_to_apis(page, const):
                apis.add(u)
        else:
            unmapped.append((it["title"], it["path"]))
    for u in apis:
        for prefix, mod in a2m.items():
            if u.startswith(prefix):
                modules.add(mod)
                break

    b.append(f"{h2}使用者看到的（{len(feat['items'])} 個項目）")
    for t, p, f in pages:
        b.append(f"{'- ' if md else '  '}{t}　`{p}`　→ {f}")
    if unmapped:
        # 對不上就明講，不假裝有答案 —— 動態路由（:id）與外部連結本來就對不到
        b.append("")
        b.append(f"{'- ' if md else '  '}⚠️ {len(unmapped)} 個項目對應不到前端頁面檔"
                 f"（動態路由或非 SPA 路由）：" + "、".join(f"{t}({p})" for t, p in unmapped[:6]))
    b.append("")

    b.append(f"{h2}它打哪些 API —— 目前無法可信回答")
    b.append(f"{'- ' if md else '  '}靜態追 import 得不出可信答案：頁面經 `from '../hooks'` 這類")
    b.append(f"{'  ' if md else '   '}barrel re-export 取用，追下去會把全 app 的端點都吸進來。")
    b.append(f"{'  ' if md else '   '}實測鑑別力：深度 3 時公文頁得到 42 個端點而**含 document 字樣者 0%**，")
    b.append(f"{'  ' if md else '   '}深度 5 爆到 168 個。依 SELF_AUDIT_EVOLUTION_STANDARD §3，")
    b.append(f"{'  ' if md else '   '}驗不出鑑別力的維度不得交付 —— 所以這裡不給清單，而不是給一份錯的。")
    b.append(f"{'- ' if md else '  '}**正確的解法是 runtime 而非靜態推論**：讓瀏覽器走查在開啟頁面時")
    b.append(f"{'  ' if md else '   '}記錄實際發出的請求（引擎已有 read_network_requests 能力），")
    b.append(f"{'  ' if md else '   '}那是事實不是推論。與第 6 階價值層改用 Prometheus 真實流量同一個道理。")
    b.append("")

    b.append(f"{h2}誰在看它 —— 走查結果檔目前答不出來")
    b.append(f"{'- ' if md else '  '}`ui-sweep.json` 只記 `pass`/`fail` 總數與失敗清單，")
    b.append(f"{'  ' if md else '   '}**不記通過了哪些路由** → 無法回答「這個功能模組有沒有被走查涵蓋」。")
    b.append(f"{'- ' if md else '  '}這本身是個缺口：走查每天在跑、涵蓋率卻無人可查。")
    b.append(f"{'  ' if md else '   '}修法是讓引擎輸出通過路由清單（一行的事），不是在這裡猜。")
    if cov.get("failures"):
        mine = [r for r in cov["failures"] if any(r.startswith(p) for _t, p, _f in pages)]
        if mine:
            b.append(f"{'- ' if md else '  '}⚠️ 走查回報的失敗中屬於本模組：" + "、".join(mine[:6]))
    b.append("")
    return "\n".join(b)


def main() -> int:
    ap = argparse.ArgumentParser(description="功能模組履歷")
    ap.add_argument("feature", nargs="?", help="功能模組名稱（如 公文管理）")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--emit-wiki", action="store_true")
    args = ap.parse_args()

    feats = load_features()
    if not feats:
        print("✗ 讀不到 site_navigation_items —— 無法判定（不視為通過）")
        return 2
    if args.list:
        for f in feats:
            print(f"  {f['name']:<12} {len(f['items'])} 個項目")
        return 0

    r2p, const, a2m, cov = route_to_page(), _endpoint_constants(), api_to_module(), _walk_results()
    targets = feats if args.all else [f for f in feats if f["name"] == args.feature]
    if not targets:
        print(f"找不到功能模組「{args.feature}」，可用：" + "、".join(f["name"] for f in feats))
        return 1

    for f in targets:
        body = render(f, r2p, const, a2m, cov, md=args.emit_wiki)
        if args.emit_wiki:
            out = ROOT / "wiki" / "topics" / f"功能模組 {f['name']}.md"
            fm = ("---\n"
                  f"title: 功能模組 {f['name']}\n"
                  "type: topic\n"
                  "sources: [site_navigation_items, router/AppRouter.tsx, api/endpoints, api/routes.py, ui-sweep.json]\n"
                  "tags: [功能模組, 履歷, 整合, auto-compiled]\n"
                  "confidence: high\n"
                  "---\n\n"
                  "> 由 `scripts/dev/feature_dossier.py` 組出，**不要手改**。\n"
                  "> 這是使用者語言的履歷：一個功能模組用到哪些頁面、API、後端模組，以及**誰在看它**。\n\n")
            out.write_text(fm + body, encoding="utf-8")
            print(f"  ✓ {out.name}")
        else:
            print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
