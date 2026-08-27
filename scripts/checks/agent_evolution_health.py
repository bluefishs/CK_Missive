#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent Evolution Health Diagnostic — 診斷坤哥進化引擎為何沒跑

排查 agent_evolution_history 14d 0 新增的根因：
  1. Redis 連線狀態（scheduler 靠 redis counter）
  2. Query counter 當前值（觸發條件 #1: 每 50）
  3. Last evolution timestamp（觸發條件 #2: 距上次 24h）
  4. Domain scores（觸發條件 #3: 5 連續低分）
  5. 過去 evolution history 樣本（看是否「跑了但沒事改」）

Lesson: L21（待加入 LESSONS_REGISTRY.md）

Usage:
    python scripts/checks/agent_evolution_health.py
    python scripts/checks/agent_evolution_health.py --redis-url redis://localhost:6380

Exit codes:
    0 — healthy（evolution 有持續觸發）
    1 — warning（trigger 久未觸發但 redis OK）
    2 — error（redis 不可達或 counter reset）

Version: 1.0.0 (2026-04-28)
Refs: L20 (LESSONS_REGISTRY)
"""


from __future__ import annotations

# cp950 韌性（L49.8 家族）：本檔的 ❌ / ✅ 只出現在**錯誤處理路徑**，
# 於是平時不會踩到，一旦 Redis/DB 真的出問題就在印錯誤時再爆一次
# UnicodeEncodeError —— 真正的錯誤訊息反而被蓋掉。
# 2026-08-03 實測：weekly step 4 因 DB 連線暫斷而走進 except，
# 接著就死在 `'cp950' codec can't encode '❌'`。
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

try:
    import asyncpg
    import redis.asyncio as redis_async
except ImportError as e:
    print(f"missing dep: {e}", file=sys.stderr)
    sys.exit(1)

# v6.13 (2026-05-31) 對齊 cross-file-ssot — strip sqlalchemy +asyncpg suffix
# bug: container DATABASE_URL=postgresql+asyncpg://... asyncpg.connect 不接受
DSN = os.getenv("DATABASE_URL", "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents")
DSN = DSN.replace("postgresql+asyncpg://", "postgresql://")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")

QUERY_COUNTER_KEY = "agent:evolution:query_count"  # 2026-04-29 修：原 'query_counter' 拼錯（scheduler 實際用 'query_count'）→ health script 永遠報 counter=0
LAST_EVOLUTION_KEY = "agent:evolution:last_run"
EVAL_HISTORY_KEY = "agent:evolution:eval_history"
EVOLVE_EVERY_N = 50
EVOLVE_INTERVAL_HOURS = 24


async def diagnose(redis_url: str) -> int:
    print("=== Agent Evolution Health Diagnostic ===\n")

    # === 1. DB: 過去 evolution history ===
    print("[1/5] DB: agent_evolution_history")
    try:
        conn = await asyncpg.connect(DSN)
        last = await conn.fetchrow(
            "SELECT created_at, trigger_reason, signals_critical, patterns_promoted, "
            "patterns_demoted, total_patterns_after FROM agent_evolution_history "
            "ORDER BY created_at DESC LIMIT 1"
        )
        total = await conn.fetchval("SELECT COUNT(*) FROM agent_evolution_history")
        last_14d = await conn.fetchval(
            "SELECT COUNT(*) FROM agent_evolution_history WHERE created_at > NOW() - INTERVAL '14 days'"
        )
        if last:
            age = datetime.now(timezone.utc) - last["created_at"].replace(tzinfo=timezone.utc)
            print(f"  total={total}  last_14d={last_14d}")
            print(f"  最後一次: {last['created_at']} ({age.days}d ago)")
            print(f"  trigger={last['trigger_reason']}  signals_critical={last['signals_critical']}  "
                  f"promoted={last['patterns_promoted']}  demoted={last['patterns_demoted']}")
        else:
            print("  ⚠️ 從未有 evolution 紀錄")
        await conn.close()
    except Exception as e:
        print(f"  ❌ DB 查詢失敗: {e}")
        return 2

    # === 2. Redis 連線 ===
    print("\n[2/5] Redis 連線")
    try:
        r = redis_async.from_url(redis_url, decode_responses=True)
        pong = await r.ping()
        print(f"  ✓ Redis ping: {pong}")
    except Exception as e:
        # 2026-08-27：**「我連不到」不等於「它掛了」** —— 這支跑在 host（weekly 在 host），
        # 而 Redis 只發佈在 `127.0.0.1:6380`。實測那個埠轉發是 **L76 殭屍**：
        # TCP 連得上（socket 接受）但立刻被關閉，raw PING 收到空回應。
        # 同時容器內 `redis-cli ping` 回 **PONG**、backend 容器內 `r.ping()` 回 **True**。
        # ⇒ evolution scheduler 跑在容器裡，它**完全不受影響**。
        #
        # 原本這裡直接 return 2 並斷言「永不觸發」——那是**假紅燈加上錯誤結論**，
        # 而 weekly 每週都會產生一次。同族：`check_runs_in_which_environment`
        # 「檢核要在排程實際執行的環境裡驗」。
        #
        # 改為：連不到就從容器再問一次，兩者分開講。
        import subprocess
        container_ok = False
        try:
            out = subprocess.run(
                ["docker", "exec", "ck_missive_redis", "redis-cli", "ping"],
                capture_output=True, encoding="utf-8", timeout=20,
                env=dict(os.environ, MSYS_NO_PATHCONV="1"))
            container_ok = "PONG" in (out.stdout or "")
        except Exception:
            container_ok = False

        if container_ok:
            print(f"  ⚠️  從本機（host）連不到 Redis：{e}")
            print("      但**容器內 redis-cli ping = PONG** —— Redis 是活的。")
            print("      這是 host 端的埠轉發問題（L76 殭屍轉發：TCP 連得上、立刻被關閉），")
            print("      而 evolution scheduler 跑在容器裡，**不受影響**。")
            print("      → 判 YELLOW：要修的是埠轉發（stop+rm+up -d，不是 restart），")
            print("        不是 evolution 機制。本檢核後續步驟需要 Redis，故就此停住。")
            return 1
        print(f"  ❌ Redis 不可達: {e}")
        print("     （容器內也問不到 PONG ⇒ 這次是真的）")
        print("  → evolution scheduler 完全靠 redis counter，不可達 = 永不觸發")
        return 2

    # === 3. Counter 狀態 ===
    print("\n[3/5] Query counter 狀態")
    try:
        counter = await r.get(QUERY_COUNTER_KEY)
        counter_val = int(counter) if counter else 0
        next_trigger = EVOLVE_EVERY_N - (counter_val % EVOLVE_EVERY_N)
        print(f"  current counter: {counter_val}")
        print(f"  下次觸發距 {next_trigger} 個 query")
        if counter_val == 0:
            print("  ⚠️ Counter = 0 — 可能 PM2 重啟後 redis 未 persist counter")
    except Exception as e:
        print(f"  ❌ Counter 查詢失敗: {e}")

    # === 4. Last evolution timestamp ===
    print("\n[4/5] Last evolution timestamp（redis）")
    try:
        last_run = await r.get(LAST_EVOLUTION_KEY)
        if last_run:
            last_dt = datetime.fromtimestamp(float(last_run), timezone.utc)
            elapsed = datetime.now(timezone.utc) - last_dt
            print(f"  last_run: {last_dt.isoformat()}")
            print(f"  elapsed: {elapsed.total_seconds() / 3600:.1f} 小時")
            if elapsed > timedelta(hours=EVOLVE_INTERVAL_HOURS):
                print(f"  ⚠️ 已超 {EVOLVE_INTERVAL_HOURS}h — 應觸發但未觸發")
                print("  → 表示 scheduler.should_evolve() 在生產未被呼叫")
                print("  → 檢查 agent_orchestrator 是否在每次 query 結束後呼叫 should_evolve()")
        else:
            print("  ⚠️ Redis 無 last_run 紀錄 — scheduler 從未跑過或重啟後遺失")
    except Exception as e:
        print(f"  ❌ last_run 查詢失敗: {e}")

    # === 5. Domain scores ===
    print("\n[5/5] Domain scores（最近 5 筆 per domain）")
    domain_low_count = 0
    for domain in ("doc", "dispatch", "erp", "graph", "pm", "analysis"):
        try:
            scores_raw = await r.lrange(f"agent:domain_scores:{domain}", 0, 4)
            if scores_raw:
                scores = [float(s) for s in scores_raw]
                avg = sum(scores) / len(scores)
                low = sum(1 for s in scores if s < 0.5)
                flag = " 🔴 5 連續低分" if low == 5 and len(scores) == 5 else ""
                if low == 5 and len(scores) == 5:
                    domain_low_count += 1
                print(f"  {domain:10} count={len(scores)} avg={avg:.2f} low_count={low}{flag}")
            else:
                print(f"  {domain:10} (no data)")
        except Exception:
            print(f"  {domain:10} (query failed)")

    await r.aclose()

    # === 結論 ===
    print("\n=== 診斷結論 ===")
    if total > 0 and last_14d == 0:
        print("⚠️  evolution 曾跑過但 14 天 0 新增")
        print("    可能原因：")
        print("    1. PM2 重啟後 redis counter reset → 累積中（看 [3/5]）")
        print("    2. agent_orchestrator 沒呼叫 should_evolve()（看 [4/5]）")
        print("    3. 過去紀錄 signals_critical=0 → 'evolution 跑了但沒事改' 是常態")
        print("\n    建議：")
        print("    - 看 PM2 log 搜「should_evolve」確認被呼叫")
        print("    - 看 redis counter 是否正在累積（diff 1 分鐘前後）")
        print("    - 若 counter 卡 0，檢查 ck-backend 是否實際接到 redis")
        return 1

    print("✓ evolution 健康（最近 14 天有觸發）")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--redis-url", default=REDIS_URL, help="Redis URL")
    args = parser.parse_args()
    sys.exit(asyncio.run(diagnose(args.redis_url)))
