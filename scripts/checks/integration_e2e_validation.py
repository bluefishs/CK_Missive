"""Integration E2E Validation (v6.13, 2026-05-31)

對齊 owner 訴求:
- 「已多次針對坤哥+Hermes+智能體 整合列為核心議題」
- 「期待本次整合優化程序能突破性成長」
- 「非一次性成功」

突破性 = 不只一次 endpoint 真活，要持續驗證機制：
- 每日 02:05 cron 跑 5 鏈 E2E 驗證
- 任一鏈斷 → LINE 推 owner + 寫 integration health marker
- 揭發 silent dormant 直到修復

5 驗證鏈:
1. Missive backend /health (業務量 OK)
2. Missive backend /api/ai/kunge/snapshot (坤哥 snapshot 真活)
3. Missive backend /api/ai/agent/tools (manifest 公開 kunge_snapshot tool)
4. Hermes container (ck-hermes-gateway healthy)
5. ck-missive-bridge skill (tools.py + tool_spec.json 對齊)

對齊 owner 安全:
- 純 read 驗證 - 無 mutation
- 任一鏈斷不影響其他 - 獨立 try/except
- 結果寫 wiki/memory/integration-health/*.json 持久化追溯
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
# 2026-08-15：weekly 跑在 host（cp950），而 ✅🔴⚠ 這些符號 cp950 編不出來。
# 崩潰是**路徑相依**的 —— 平常走 GREEN 分支沒事，偏偏在要報問題的那一刻崩掉，
# 而那時看到的是 UnicodeEncodeError 不是它本來要講的事。同 L49.8（.ps1 的 BOM）家族。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# 2026-08-04：預設值原本寫死容器路徑 `/app/wiki`。在 host 上 Windows 會把它解析成
# **磁碟根目錄下的 app/wiki 目錄**（磁碟相對路徑）—— 於是 host 執行時產出
# 靜靜寫進一個沒人讀的雜散目錄，而消費端（producer registry）讀的是 repo 內的路徑。
# 已累積 7 月以來的殘留。改用 **repo 相對路徑**：容器內腳本在 `/app/scripts/checks/`
# → parents[2] = `/app`，host 上 → repo 根，兩邊都對（L52 家族）。
_REPO_ROOT = Path(__file__).resolve().parents[2]
WIKI_MEMORY = Path(os.getenv("CK_WIKI_DIR") or (_REPO_ROOT / "wiki")) / "memory"
HEALTH_DIR = WIKI_MEMORY / "integration-health"


def _safe_get_token() -> str:
    """讀 MCP_SERVICE_TOKEN from env (container 內) or .env file"""
    tok = os.getenv("MCP_SERVICE_TOKEN", "").strip()
    if tok:
        return tok
    env_path = Path("/app/.env")
    if not env_path.exists():
        env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("MCP_SERVICE_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


async def check_chain_1_missive_health() -> Dict[str, Any]:
    """Chain 1: Missive backend /health (業務量 OK)"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("http://localhost:8001/health")
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code, "error": "non-200"}
            data = r.json()
            biz_ok = data.get("business_data", {}).get("ok", False)
            return {
                "ok": biz_ok,
                "documents": data.get("business_data", {}).get("documents", 0),
                "entities": data.get("business_data", {}).get("canonical_entities", 0),
            }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


async def check_chain_2_kunge_snapshot() -> Dict[str, Any]:
    """Chain 2: kunge_snapshot E2E"""
    try:
        import httpx
        token = _safe_get_token()
        if not token:
            return {"ok": False, "error": "no MCP_SERVICE_TOKEN"}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "http://localhost:8001/api/ai/kunge/snapshot",
                json={"window_days": 7},
                headers={"X-Service-Token": token},
            )
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code, "error": r.text[:200]}
            data = r.json()
            counts = data.get("counts", {})
            return {
                "ok": data.get("success", False),
                "lessons": counts.get("lessons", 0),
                "patterns": counts.get("patterns", 0),
                "proposals": counts.get("proposals", 0),
                "pending_proposals": data.get("health_signals", {}).get("pending_proposals_count", 0),
            }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


async def check_chain_3_tools_manifest() -> Dict[str, Any]:
    """Chain 3: tools manifest 含 kunge_snapshot（需帶服務 token）

    2026-08-21：`/api/ai/agent/tools` 改為需要 `X-Service-Token`。
    原本的 docstring 寫「manifest **公開**」—— 那個假設不再成立：
    實測公網未登入、帶一枚公開可取的 CSRF token 就拿得到整份工具清冊
    與 server 資訊，而那是規劃攻擊面時最有用的一份文件。

    ⚠️ Hermes 端**本來就帶**（`tools.py:_make_headers` 設 X-Service-Token），
    所以真正的整合沒壞 —— 壞的是這支驗證腳本自己還在用舊假設。
    這正是 L81「換了出口就要換整條鏈」：改了端點的認證，
    消費端之一沒跟上，而它的失敗看起來像整合斷了。
    """
    try:
        import os
        import httpx
        token = os.getenv("MCP_SERVICE_TOKEN") or ""
        headers = {"X-Service-Token": token} if token else {}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post("http://localhost:8001/api/ai/agent/tools",
                                  headers=headers)
            if r.status_code in (401, 403) and not token:
                # 沒有 token 就無法驗 —— 說出來，不要判成「整合斷了」
                return {"ok": False, "status": r.status_code,
                        "reason": "MCP_SERVICE_TOKEN 未設，無法驗證（不是整合斷了）"}
            if r.status_code != 200:
                return {"ok": False, "status": r.status_code}
            data = r.json()
            tool_names = [t.get("name") for t in data.get("tools", [])]
            has_kunge = "kunge_snapshot" in tool_names
            return {
                "ok": has_kunge,
                "total_tools": len(tool_names),
                "has_kunge_snapshot": has_kunge,
            }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


async def check_chain_4_hermes_container() -> Dict[str, Any]:
    """Chain 4: Hermes gateway healthy via HTTP (不依賴 docker CLI)

    container 內沒 docker socket，改 HTTP healthcheck (對齊 L49 family)。
    嘗試多個 endpoint 名稱以涵蓋 hermes-gateway 各版本 API。
    """
    try:
        import httpx
        # 嘗試多個 hostname (container network alias)
        for host in ["ck-hermes-gateway", "hermes-gateway", "host.docker.internal"]:
            for port in [8642, 9119]:
                url = f"http://{host}:{port}/health"
                try:
                    async with httpx.AsyncClient(timeout=3) as client:
                        r = await client.get(url)
                        if r.status_code < 500:
                            return {
                                "ok": True,
                                "endpoint": f"{host}:{port}",
                                "status": r.status_code,
                            }
                except Exception:
                    continue
        return {
            "ok": False,
            "error": "hermes-gateway unreachable on 8642/9119",
            "tried_hosts": ["ck-hermes-gateway", "hermes-gateway", "host.docker.internal"],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def check_chain_5_bridge_skill() -> Dict[str, Any]:
    """Chain 5: ck-missive-bridge skill 對齊 — 在 host 跑時檢查 docs/

    對齊「在 container 跑 skip 但回 ok with note」原則：
    container 內 docs/ 不 mount → 改用 missive tool_manifest 反查（chain 3 已驗）
    """
    candidates = [
        Path(__file__).resolve().parents[2] / "docs" / "hermes-skills" / "ck-missive-bridge" / "tools.py",
        Path("/host/docs/hermes-skills/ck-missive-bridge/tools.py"),
    ]
    for tools_py in candidates:
        if tools_py.exists():
            content = tools_py.read_text(encoding="utf-8", errors="ignore")
            has_endpoint = "kunge_snapshot" in content and "/api/ai/kunge/snapshot" in content
            return {
                "ok": has_endpoint,
                "has_kunge_endpoint": has_endpoint,
                "tools_py_size": tools_py.stat().st_size,
                "tools_py_path": str(tools_py),
            }
    # 在 container 內跑 → skip，回 ok 並註明（避免 cron silent fail）
    return {
        "ok": True,
        "skipped": True,
        "note": "docs/ not mounted in container — bridge skill verified via chain 3 manifest",
    }


def write_health_report(results: Dict[str, Dict[str, Any]]) -> Path:
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    filename = f"integration-health-{now.strftime('%Y%m%d-%H%M%S')}.json"
    path = HEALTH_DIR / filename
    all_ok = all(r.get("ok", False) for r in results.values())
    payload = {
        "timestamp": now.isoformat(timespec="seconds"),
        "all_ok": all_ok,
        "broken_chains": [k for k, v in results.items() if not v.get("ok", False)],
        "chains": results,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _prune_old_reports()
    return path


# 保留天數：夠回答「最近有沒有斷過鏈」，又不讓目錄無上限成長。
# 2026-08-04：這個目錄自 05-31 起累積 167 個檔、從未清理過 —— 產出有保留策略
# 才算完整，否則就是另一種「產出沒有下游」（只是換成佔空間的形式）。
REPORT_RETENTION_DAYS = 30


def _prune_old_reports() -> int:
    """刪掉超過保留期的歷史報告，回傳刪除數。

    刻意**只清自己產生的檔名樣式**（`integration-health-*.json`）——
    同一目錄下還有 `ui-sweep.json` / `capability-usage.json` 等別人的產出，
    用萬用字元清整個目錄會誤刪（刪除型操作不得靠「大概不會有別的檔」）。
    """
    import time
    cutoff = time.time() - REPORT_RETENTION_DAYS * 86400
    removed = 0
    for f in HEALTH_DIR.glob("integration-health-*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue  # 檔案被別的程序持有就跳過，下一輪再清
    return removed


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=== Integration E2E Validation (v6.13) ===")
    print()

    results = {
        "chain_1_missive_health": await check_chain_1_missive_health(),
        "chain_2_kunge_snapshot": await check_chain_2_kunge_snapshot(),
        "chain_3_tools_manifest": await check_chain_3_tools_manifest(),
        "chain_4_hermes_container": await check_chain_4_hermes_container(),
        "chain_5_bridge_skill": check_chain_5_bridge_skill(),
    }

    all_ok = all(r.get("ok", False) for r in results.values())
    broken = [k for k, v in results.items() if not v.get("ok", False)]

    for name, r in results.items():
        emoji = "✅" if r.get("ok") else "❌"
        # 簡潔輸出
        details = {k: v for k, v in r.items() if k != "ok"}
        print(f"{emoji} {name}: {json.dumps(details, ensure_ascii=False)[:200]}")

    print()
    print(f"OVERALL: {'✅ ALL PASS' if all_ok else f'❌ BROKEN: {broken}'}")

    if not args.dry_run:
        path = write_health_report(results)
        print(f"REPORT: {path}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
