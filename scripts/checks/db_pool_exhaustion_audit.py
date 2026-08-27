#!/usr/bin/env python3
"""db_pool_exhaustion_audit.py — fitness step 48

偵測 SQLAlchemy DB connection pool 耗盡風險（v6.12 P3 forward-looking）。

風險背景：
- SQLAlchemy pool exhausted 時新 connection 進入 wait queue（默認 30 秒 timeout）
- L29 family silent failure 模式：connection wait 不 alert，看似 OK 實際 latency 飆
- 業務 endpoint 慢但 docker healthcheck 仍 200 → silent dormant
- 觀察點：`/health` endpoint 已暴露 pool stats（{size, checked_in, checked_out, overflow, max_overflow}）

判定邏輯：
1. 抓 /health endpoint pool stats（local + public）
2. 計算 utilization = checked_out / (size + max_overflow)
3. RED：utilization > 90%（almost exhausted）
4. YELLOW：utilization > 50% 或 overflow > 0（已用到 overflow pool）
5. GREEN：utilization < 50% 且 overflow = 0

Usage:
    python scripts/checks/db_pool_exhaustion_audit.py [--strict]

Exit codes:
    0 = green (pool utilization healthy)
    1 = yellow (>50% util or overflow active)
    2 = red (>90% util, near exhaustion; --strict 時 yellow 也 exit 2)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

# Endpoints to audit (local + public)
HEALTH_ENDPOINTS = [
    ("local", "http://localhost:8001/health"),
    ("public", "https://missive.cksurvey.tw/health"),
]


def _server_side_budget():
    """伺服器端的 `max_connections` 用掉多少 —— 與應用自己的池是**兩件事**。

    2026-08-27 實測到兩者完全背離：
      · 應用池   15/35 → 本檢核報 **GREEN 2.9%**
      · 伺服器   49/50 → **每一個新連線都被拒絕**（psql 也連不進去）

    ⇒ 原本這支問的是「我的池滿了嗎」，而使用者遇到的是「資料庫還收不收連線」。
      池沒滿也可能整台 DB 進不去 —— 額度是**所有客戶端共用**的，
      應用池只佔其中一部分。那次連兩支檢核（sso_coverage / agent_evolution_health）
      都因此報假 RED。

    ⚠️ **不能靠 DB 連線來量這件事** —— 需要它的時候正是連不進去的時候。
      所以優先走 DB（準），連不上就退回 postgres 容器的 `/proc/net/tcp`
      數 ESTABLISHED（不需要任何連線）。

    ⚠️ 代理的已知限制（實測對照，不假裝沒有）：proc 只數 **TCP** 客戶端，
      容器內走 unix socket 的 psql 不在內（實測 proc=2 / client_backends=3，
      差的 1 就是那個 psql）。**低估的方向是安全的**：它不會把健康的誤報成滿。
    """
    import os
    import subprocess

    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    container = os.getenv("PG_CONTAINER", "ck_missive_postgres")

    def _exec(cmd):
        try:
            r = subprocess.run(["docker", "exec", container] + cmd,
                               capture_output=True, encoding="utf-8",
                               timeout=25, env=env)
            return (r.stdout or "").strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    psql = ["psql", "-U", "ck_user", "-d", "ck_documents", "-t", "-A", "-c"]
    used = _exec(psql + ["SELECT count(*) FROM pg_stat_activity "
                         "WHERE backend_type='client backend'"])
    limit = _exec(psql + ["SELECT setting FROM pg_settings WHERE name='max_connections'"])
    how = "pg_stat_activity"

    if not used.isdigit():
        # DB 收不了連線 —— 這正是本段存在的理由
        used = _exec(["sh", "-c",
                      "awk 'NR>1 && $4==\"01\"' /proc/net/tcp /proc/net/tcp6 "
                      "2>/dev/null | wc -l"])
        how = "/proc/net/tcp（DB 連不上，退回 OS 層；只數 TCP 客戶端）"
    if not limit.isdigit():
        limit = os.getenv("PG_MAX_CONNECTIONS", "50")
        how += "｜max_connections 取自預設"
    if not used.isdigit():
        return "SKIP", "取不到伺服器端連線數（容器 %s 問不到）" % container

    u, m = int(used), int(limit)
    pct = (u / m * 100) if m else 0

    def _who() -> str:
        """快滿時「是誰佔著」—— 2026-08-27 實測 49/50 而我查不出成因。

        當時能用的只有 `/proc/net/tcp` 的 peer 位址（DB 已經拒連），
        而我是臨時手刻的；下次再發生時這一段要自己說出來，
        否則報表只有「49/50」，接手的人從零開始。

        位址是十六進位小端序（`040014AC` = 172.20.0.4），順手轉成點分十進位；
        對照容器 IP 就知道是哪一個。**只在快滿時才跑**，平時不加負擔。
        """
        raw = _exec(["sh", "-c",
                     "awk 'NR>1 && $4==\"01\"' /proc/net/tcp 2>/dev/null "
                     "| awk '{print $3}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -5"])
        if not raw:
            return ""
        out = []
        for ln in raw.strip().split(chr(10)):
            parts = ln.split()
            if len(parts) != 2:
                continue
            cnt, hexip = parts
            try:
                b = bytes.fromhex(hexip)
                ip = ".".join(str(x) for x in reversed(b))
            except Exception:
                ip = hexip
            out.append(f"{ip}×{cnt}")
        if not out:
            return ""
        return ("　連線來源：" + "、".join(out)
                + "（對照容器：docker inspect <名稱> --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'）")

    line = "伺服器端 %d/%d（%.0f%%）｜來源：%s" % (u, m, pct, how)
    if pct >= 90:
        return "RED", line + "　⚠️ 額度快用完 —— 新連線會被拒絕（含 psql 與所有檢核腳本）" + _who()
    if pct >= 70:
        return "YELLOW", line + "　⚠️ 餘裕不足" + _who()
    return "GREEN", line


def _curl_json(url: str, timeout: int = 5) -> dict | None:
    """Fetch URL and parse as JSON."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 2,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def _classify(pool: dict) -> tuple[str, float, str]:
    """Return (severity, utilization_pct, reason)."""
    size = pool.get("size", 0)
    checked_out = pool.get("checked_out", 0)
    overflow = pool.get("overflow", 0)
    max_overflow = pool.get("max_overflow", 0)

    capacity = size + max_overflow
    if capacity <= 0:
        return "GREEN", 0.0, "no capacity data"

    util_pct = (checked_out / capacity) * 100.0

    if util_pct > 90:
        return "RED", util_pct, f"utilization >{90}% — near exhaustion"
    if util_pct > 50 or overflow > 0:
        reason_parts = []
        if util_pct > 50:
            reason_parts.append(f"util {util_pct:.1f}%")
        if overflow > 0:
            reason_parts.append(f"overflow active ({overflow}/{max_overflow})")
        return "YELLOW", util_pct, " + ".join(reason_parts)
    return "GREEN", util_pct, f"util {util_pct:.1f}%"


def main() -> int:
    # Force UTF-8 stdout for Windows cp950 console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any warning")
    args = parser.parse_args()

    print("=" * 60)
    print("DB pool exhaustion audit (v6.12 P3)")
    print("v1.0 / detect connection pool exhaustion risk")
    print("=" * 60)

    overall_severity = "GREEN"
    any_reachable = False

    for name, url in HEALTH_ENDPOINTS:
        print(f"\n  {name}: {url}")
        data = _curl_json(url)
        if not data:
            print(f"    ⚪ unreachable (likely network issue)")
            continue

        any_reachable = True
        pool = data.get("pool") or {}
        if not pool:
            print(f"    ⚪ no pool stats in /health (older backend?)")
            continue

        severity, util_pct, reason = _classify(pool)
        indicator = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[severity]

        size = pool.get("size", 0)
        checked_out = pool.get("checked_out", 0)
        overflow = pool.get("overflow", 0)
        max_overflow = pool.get("max_overflow", 0)
        capacity = size + max_overflow

        print(f"    {indicator} {severity}: {reason}")
        print(f"       size={size} | checked_out={checked_out} | overflow={overflow}/{max_overflow}")
        print(f"       capacity={capacity} | utilization={util_pct:.1f}%")

        # Escalate overall
        if severity == "RED":
            overall_severity = "RED"
        elif severity == "YELLOW" and overall_severity == "GREEN":
            overall_severity = "YELLOW"

    if not any_reachable:
        print(f"\n  ⚪ no endpoint reachable — skipping audit")
        return 0

    # === 第二個維度：伺服器端額度（與應用池是兩件事，2026-08-27 加）===
    sev2, msg2 = _server_side_budget()
    icon = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢", "SKIP": "⚪"}[sev2]
    print("")
    print(f"  {icon} {msg2}")
    if sev2 == "RED":
        overall_severity = "RED"
    elif sev2 == "YELLOW" and overall_severity == "GREEN":
        overall_severity = "YELLOW"
    elif sev2 == "SKIP" and overall_severity == "GREEN":
        # 「沒量到」不得與「量了沒事」在歷史裡長得一樣 —— 本 repo 的三態約定
        # （0 GREEN / 1 YELLOW / 2+ RED）裡，未驗完屬 YELLOW 不屬 GREEN。
        overall_severity = "YELLOW"

    print(f"\n  Final severity: {overall_severity}")

    if overall_severity == "RED":
        print("\n💡 修法建議：")
        print("  1. 立即 docker logs ck_missive_backend 看哪個 endpoint 長時間 hold connection")
        print("  2. 調 pool size: SQLALCHEMY_ENGINE_OPTIONS.pool_size + max_overflow")
        print("  3. 加 pool_pre_ping=True 防 stale connection")
        print("  4. 加 pool_recycle=3600（每小時刷新）")
        print("  5. review code 找未 close 的 session（特別 background scheduler）")
    elif overall_severity == "YELLOW":
        print("\n💡 informational：")
        print("  目前 overflow 已啟用或 utilization > 50% — 觀察是否常態化")
        print("  若 7 天內持續 yellow → 考慮提升 pool_size")

    if overall_severity == "RED":
        return 2
    if overall_severity == "YELLOW" and args.strict:
        return 2
    if overall_severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
